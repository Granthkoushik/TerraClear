import os
import cv2
import numpy as np
import torch
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
from app.models.networks import SurfaceReconstructionNet

class SurfaceReconstructionService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load_model()

    def _load_model(self):
        """Attempts to load the PyTorch Surface Reconstruction model weights."""
        if settings.RECONSTRUCTION_MODEL_PATH.exists():
            try:
                self.model = SurfaceReconstructionNet()
                self.model.load_state_dict(torch.load(settings.RECONSTRUCTION_MODEL_PATH, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()
                logger.info(f"Loaded SurfaceReconstructionNet weights from {settings.RECONSTRUCTION_MODEL_PATH} on {self.device}")
            except Exception as e:
                logger.error(f"Failed to load SurfaceReconstructionNet weights: {e}. Fallback enabled.")
                self.model = None
        else:
            logger.info(f"Reconstruction weights not found at {settings.RECONSTRUCTION_MODEL_PATH}. Classical DIP inpainter will be used.")

    def reconstruct_surface(
        self, 
        image_path: Path, 
        mask_path: Path, 
        output_path: Path,
        cloud_coverage_percentage: float,
        force_classical: bool = False
    ) -> float:
        """
        Reconstructs the cloud-covered surface using DL or classical inpainting.
        Saves the reconstructed image to output_path.
        Returns:
            reconstruction_confidence (float)
        """
        img_bgr = cv2.imread(str(image_path))
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        
        if img_bgr is None or mask is None:
            raise ValueError("Could not load input image or cloud mask")
            
        h, w, c = img_bgr.shape
        
        # Decide whether to use Deep Learning or Classical
        use_dl = (self.model is not None) and (not force_classical)
        
        if use_dl:
            try:
                # Prepare image for PyTorch
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                img_normalized = img_rgb.astype(np.float32) / 255.0
                mask_normalized = mask.astype(np.float32) / 255.0
                
                # U-Net / AE requires input size to be multiple of 16 or 32
                h_new = int(np.round(h / 32) * 32)
                w_new = int(np.round(w / 32) * 32)
                h_new = max(32, h_new)
                w_new = max(32, w_new)
                
                img_resized = cv2.resize(img_normalized, (w_new, h_new), interpolation=cv2.INTER_LINEAR)
                mask_resized = cv2.resize(mask_normalized, (w_new, h_new), interpolation=cv2.INTER_NEAREST)
                
                # Add dimensions to create batch size of 1
                img_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0).to(self.device)
                mask_tensor = torch.from_numpy(mask_resized).unsqueeze(0).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    rebuilt_tensor = self.model(img_tensor, mask_tensor)
                    
                # Decode and resize back to original size
                rebuilt_np = rebuilt_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
                rebuilt_resized = cv2.resize(rebuilt_np, (w, h), interpolation=cv2.INTER_LINEAR)
                
                # Convert back to BGR 0-255 scale
                rebuilt_bgr = cv2.cvtColor((rebuilt_resized * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
                
                cv2.imwrite(str(output_path), rebuilt_bgr)
                
                # Confidence score is negatively correlated with cloud coverage.
                # Reconstructing 90% cloud cover is much less confident than 5% cloud cover.
                base_confidence = max(0.2, 1.0 - (cloud_coverage_percentage / 100.0) * 0.8)
                # Apply model-based certainty adjustment (how sharp the outputs are)
                logger.info(f"DL Surface Reconstruction complete. Base confidence: {base_confidence:.2f}")
                return float(base_confidence)
                
            except Exception as e:
                logger.error(f"DL Reconstruction failed: {e}. Falling back to classical method.")
                
        # Classical Fallback (Navier-Stokes based Inpainting)
        # Use cv2.inpaint with a combination of Telea and Navier-Stokes or Telea alone.
        # Telea is preferred for detailed structures; NS is preferred for smooth transitions.
        # We'll use cv2.INPAINT_TELEA with an inpaint radius of 7.
        inpaint_radius = 7
        
        # Inpaint BGR channels
        reconstructed = cv2.inpaint(img_bgr, mask, inpaint_radius, cv2.INPAINT_TELEA)
        
        # Calculate scientific confidence score
        # Confidence decays exponentially with the percentage of missing pixels, 
        # as large cloud covers suffer from spatial information scarcity.
        # Formula: confidence = exp(-0.03 * coverage)
        confidence = float(np.exp(-0.03 * cloud_coverage_percentage))
        confidence = max(0.3, min(1.0, confidence))
        
        cv2.imwrite(str(output_path), reconstructed)
        logger.info(f"Classical Surface Reconstruction complete. Confidence: {confidence:.2f}")
        
        return confidence

surface_reconstruction_service = SurfaceReconstructionService()
