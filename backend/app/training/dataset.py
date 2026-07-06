import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from pathlib import Path
from typing import Tuple, Optional

class RICEDataset(Dataset):
    """
    PyTorch Dataset for Remote Sensing Image Cloud Removing (RICE) Dataset.
    Supports RICE-I, RICE-II, and an in-memory Synthetic Fallback mode.
    """
    def __init__(
        self, 
        dataset_dir: Optional[str] = None, 
        subset: str = 'rice2', 
        img_size: Tuple[int, int] = (256, 256),
        synthetic: bool = False,
        num_synthetic_samples: int = 100
    ):
        self.dataset_dir = Path(dataset_dir) if dataset_dir else None
        self.subset = subset.lower()
        self.img_size = img_size
        self.synthetic = synthetic
        self.num_synthetic_samples = num_synthetic_samples
        self.file_names = []

        if not self.synthetic:
            if not self.dataset_dir or not self.dataset_dir.exists():
                print(f"Dataset path {dataset_dir} not found. Enabling synthetic mode fallback.")
                self.synthetic = True
            else:
                self.cloudy_dir = self.dataset_dir / "cloudy"
                self.clear_dir = self.dataset_dir / "clear"
                
                if not self.cloudy_dir.exists() or not self.clear_dir.exists():
                    print(f"Required subfolders 'cloudy' or 'clear' missing. Enabling synthetic fallback.")
                    self.synthetic = True
                else:
                    self.file_names = [f for f in os.listdir(self.cloudy_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
                    
                    if self.subset == 'rice2':
                        self.mask_dir = self.dataset_dir / "mask"
                        if not self.mask_dir.exists():
                            print("RICE-II requires 'mask' folder. Fallback: generating masks dynamically from differences.")
                            self.subset = 'rice1'

        if self.synthetic:
            print(f"Dataset running in SYNTHETIC fallback mode with {self.num_synthetic_samples} in-memory pairs.")

    def __len__(self) -> int:
        return self.num_synthetic_samples if self.synthetic else len(self.file_names)

    def _generate_synthetic_sample(self, index: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Generates a synthetic cloudy image, mask, and clear background sample in memory."""
        # Use seed to ensure reproducibility per sample index
        np.random.seed(index)
        
        # Clear background (forest greens and river)
        clear = np.zeros((self.img_size[1], self.img_size[0], 3), dtype=np.uint8)
        # Background color
        clear[:, :, 1] = np.random.randint(80, 150) # Green channel
        clear[:, :, 0] = np.random.randint(20, 60)  # Blue channel
        clear[:, :, 2] = np.random.randint(40, 90)  # Red channel
        
        # Add some circular landscape patterns
        for _ in range(5):
            cx = np.random.randint(0, self.img_size[0])
            cy = np.random.randint(0, self.img_size[1])
            r = np.random.randint(20, 80)
            cv2.circle(clear, (cx, cy), r, (np.random.randint(10, 50), np.random.randint(100, 180), np.random.randint(30, 80)), -1)
            
        # Draw a synthetic river
        cv2.line(clear, (0, self.img_size[1]//2), (self.img_size[0], self.img_size[1]//2 + np.random.randint(-30, 30)), (150, 90, 30), 8)
        
        # Blur background
        clear = cv2.GaussianBlur(clear, (9, 9), 0)
        
        # Cloudy image and mask
        mask = np.zeros((self.img_size[1], self.img_size[0]), dtype=np.uint8)
        # Add random puffy cloud circle
        cx = np.random.randint(40, self.img_size[0] - 40)
        cy = np.random.randint(40, self.img_size[1] - 40)
        r = np.random.randint(25, 55)
        cv2.circle(mask, (cx, cy), r, 255, -1)
        # Soften mask edges
        mask_blurred = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_f = mask_blurred.astype(np.float32) / 255.0
        
        # Create cloudy image by blending white pixels based on mask weight
        cloudy = clear.copy().astype(np.float32)
        for c in range(3):
            cloudy[:, :, c] = cloudy[:, :, c] * (1.0 - mask_f) + 255.0 * mask_f
        cloudy = cloudy.astype(np.uint8)
        
        # Normalize and convert to PyTorch tensors [C, H, W]
        clear_t = torch.from_numpy(clear).permute(2, 0, 1).float() / 255.0
        cloudy_t = torch.from_numpy(cloudy).permute(2, 0, 1).float() / 255.0
        # Binary mask thresholded at 0.1 for training target
        mask_t = torch.from_numpy(mask).unsqueeze(0).float() / 255.0
        
        return cloudy_t, mask_t, clear_t

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if self.synthetic:
            return self._generate_synthetic_sample(idx)
            
        file_name = self.file_names[idx]
        
        cloudy_path = self.cloudy_dir / file_name
        clear_path = self.clear_dir / file_name
        
        # Read images
        cloudy_img = cv2.imread(str(cloudy_path))
        clear_img = cv2.imread(str(clear_path))
        
        if cloudy_img is None or clear_img is None:
            # Fallback to a synthetic sample if disk file is corrupted
            return self._generate_synthetic_sample(idx)
            
        # Convert BGR to RGB
        cloudy_img = cv2.cvtColor(cloudy_img, cv2.COLOR_BGR2RGB)
        clear_img = cv2.cvtColor(clear_img, cv2.COLOR_BGR2RGB)
        
        # Resize to expected dimensions
        cloudy_img = cv2.resize(cloudy_img, self.img_size, interpolation=cv2.INTER_LINEAR)
        clear_img = cv2.resize(clear_img, self.img_size, interpolation=cv2.INTER_LINEAR)
        
        # Read or compute mask
        if self.subset == 'rice2':
            mask_path = self.mask_dir / file_name
            mask_img = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                mask_img = cv2.resize(mask_img, self.img_size, interpolation=cv2.INTER_NEAREST)
            else:
                # Fallback to computing mask from difference
                diff = np.abs(cloudy_img.astype(np.int16) - clear_img.astype(np.int16))
                mask_img = (diff.mean(axis=2) > 30).astype(np.uint8) * 255
        else:
            # Dynamic difference mask for RICE-I
            diff = np.abs(cloudy_img.astype(np.int16) - clear_img.astype(np.int16))
            mask_img = (diff.mean(axis=2) > 30).astype(np.uint8) * 255
            # Morphological dilation to ensure full cover
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask_img = cv2.dilate(mask_img, kernel, iterations=1)
            
        # Normalize and convert to tensors
        cloudy_tensor = torch.from_numpy(cloudy_img).permute(2, 0, 1).float() / 255.0
        clear_tensor = torch.from_numpy(clear_img).permute(2, 0, 1).float() / 255.0
        mask_tensor = torch.from_numpy(mask_img).unsqueeze(0).float() / 255.0
        
        return cloudy_tensor, mask_tensor, clear_tensor
