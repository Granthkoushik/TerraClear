import argparse
import sys
import time
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add backend and app folders to path to ensure correct relative imports
backend_dir = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(backend_dir))
sys.path.append(str(backend_dir / "app"))

from app.core.config import settings
from app.core.logging import logger
from app.models.networks import SurfaceReconstructionNet
from app.training.dataset import RICEDataset

def train_model(args):
    """Executes the PyTorch training loop for SurfaceReconstructionNet."""
    logger.info("Initializing TerraClear Surface Reconstruction training pipeline.")
    
    # 1. Device configuration
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Target execution hardware: {device}")
    
    # Ensure weights directory exists
    settings.WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Instantiate Dataset and DataLoader
    dataset = RICEDataset(
        dataset_dir=args.dataset_dir,
        subset=args.subset,
        img_size=(256, 256),
        synthetic=args.synthetic,
        num_synthetic_samples=args.num_samples
    )
    
    loader = DataLoader(
        dataset, 
        batch_size=args.batch_size, 
        shuffle=True, 
        num_workers=0, # set to 0 for Windows compatibility
        drop_last=True
    )
    
    # 3. Instantiate model, loss, and optimizer
    model = SurfaceReconstructionNet().to(device)
    
    # If starting from existing weights
    if args.resume and settings.RECONSTRUCTION_MODEL_PATH.exists():
        try:
            model.load_state_dict(torch.load(settings.RECONSTRUCTION_MODEL_PATH, map_location=device))
            logger.info("Resumed from existing model weights.")
        except Exception as e:
            logger.warning(f"Could not load existing weights to resume: {e}. Training from scratch.")
            
    model.train()
    
    l1_loss_fn = nn.L1Loss()
    mse_loss_fn = nn.MSELoss()
    
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    
    logger.info(f"Loaded dataset containing {len(dataset)} samples. Starting training...")
    
    start_time = time.time()
    best_loss = float('inf')
    
    # 4. Training Loop
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()
        running_loss = 0.0
        running_l1 = 0.0
        running_mse = 0.0
        
        for batch_idx, (cloudy, mask, clear) in enumerate(loader):
            # Move tensors to device
            cloudy = cloudy.to(device)
            mask = mask.to(device)
            clear = clear.to(device)
            
            # Forward pass
            optimizer.zero_grad()
            reconstructed = model(cloudy, mask)
            
            # Loss calculations
            l1_loss = l1_loss_fn(reconstructed, clear)
            mse_loss = mse_loss_fn(reconstructed, clear)
            
            # Combined Loss: L1 checks pixel margins, MSE pushes spatial smooth structural margins
            total_loss = l1_loss + 0.5 * mse_loss
            
            # Backward pass & Optimize
            total_loss.backward()
            optimizer.step()
            
            # Statistics
            running_loss += total_loss.item()
            running_l1 += l1_loss.item()
            running_mse += mse_loss.item()
            
            if (batch_idx + 1) % max(1, len(loader) // 5) == 0 or batch_idx == len(loader) - 1:
                logger.info(
                    f"Epoch [{epoch}/{args.epochs}] | Batch [{batch_idx+1}/{len(loader)}] | "
                    f"Total Loss: {total_loss.item():.5f} (L1: {l1_loss.item():.5f}, MSE: {mse_loss.item():.5f})"
                )
                
        epoch_loss = running_loss / len(loader)
        epoch_l1 = running_l1 / len(loader)
        epoch_mse = running_mse / len(loader)
        duration = time.time() - epoch_start
        
        logger.info(
            f"==> Epoch [{epoch}/{args.epochs}] Complete in {duration:.2f}s | "
            f"Avg Loss: {epoch_loss:.5f} (L1: {epoch_l1:.5f}, MSE: {epoch_mse:.5f})"
        )
        
        # Save checkpoints if loss improves
        if epoch_loss < best_loss:
            best_loss = epoch_loss
            try:
                torch.save(model.state_dict(), settings.RECONSTRUCTION_MODEL_PATH)
                logger.info(f"Saved new best model checkpoint to {settings.RECONSTRUCTION_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to save model weights: {e}")
                
    total_duration = time.time() - start_time
    logger.info(f"Training completed in {total_duration:.2f}s. Best loss achieved: {best_loss:.5f}")
    print(f"Model saved successfully to: {settings.RECONSTRUCTION_MODEL_PATH.resolve()}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TerraClear Surface Reconstruction Model Training")
    parser.add_argument("--dataset_dir", type=str, default=None, help="Path to RICE dataset subfolder")
    parser.add_argument("--subset", type=str, default="rice2", choices=["rice1", "rice2"], help="Dataset partition (rice1/rice2)")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=0.0005, help="Learning rate")
    parser.add_argument("--synthetic", action="store_true", help="Force synthetic data generator fallback")
    parser.add_argument("--num_samples", type=int, default=16, help="Number of synthetic samples (only used if in synthetic mode)")
    parser.add_argument("--resume", action="store_true", help="Resume training from existing weights")
    
    args = parser.parse_args()
    
    train_model(args)
