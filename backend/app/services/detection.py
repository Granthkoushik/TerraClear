import os
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import Tuple
from PIL import Image
from app.core.config import settings
from app.core.logging import logger
from app.models.networks import CloudDetectorNet

class CloudDetectionService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load_model()

    def _load_model(self):
        """Attempts to load the PyTorch U-Net cloud detector model weights."""
        if settings.CLOUD_DETECTION_MODEL_PATH.exists():
            try:
                self.model = CloudDetectorNet(n_channels=3, n_classes=1)
                self.model.load_state_dict(torch.load(settings.CLOUD_DETECTION_MODEL_PATH, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()
                logger.info(f"Loaded CloudDetector U-Net weights from {settings.CLOUD_DETECTION_MODEL_PATH} on {self.device}")
            except Exception as e:
                logger.error(f"Failed to load CloudDetector U-Net weights: {e}. Fallback enabled.")
                self.model = None
        else:
            logger.info(f"U-Net weights not found at {settings.CLOUD_DETECTION_MODEL_PATH}. Classical DIP detector will be used.")

    def detect_clouds(
        self, 
        image_path: Path, 
        output_path: Path, 
        threshold: float = 0.5, 
        force_classical: bool = False
    ) -> Tuple[float, float]:
        """
        Runs cloud detection on the image. Saves the binary mask to output_path.
        Returns:
            Tuple[cloud_coverage_percentage, detection_confidence]
        """
        # Load image with OpenCV (reads in BGR)
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            raise ValueError(f"Could not load image at {image_path}")
            
        h, w, c = img_bgr.shape
        total_pixels = h * w
        
        # Decide whether to use Deep Learning or Classical
        use_dl = (self.model is not None) and (not force_classical)
        
        if use_dl:
            try:
                # DL Inference
                # Convert BGR to RGB, normalize, and convert to tensor [1, 3, H, W]
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                img_normalized = img_rgb.astype(np.float32) / 255.0
                
                # Resize to multiple of 32 for U-Net compatibility if needed
                # (We will do a crop or resize, for simplicity, resize to nearest multiple of 32, then resize back)
                h_new = int(np.round(h / 32) * 32)
                w_new = int(np.round(w / 32) * 32)
                h_new = max(32, h_new)
                w_new = max(32, w_new)
                
                img_resized = cv2.resize(img_normalized, (w_new, h_new), interpolation=cv2.INTER_LINEAR)
                tensor_in = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    mask_tensor = self.model(tensor_in)
                    
                # Resize mask back to original size
                mask_np = mask_tensor.squeeze(0).squeeze(0).cpu().numpy()
                mask_np_resized = cv2.resize(mask_np, (w, h), interpolation=cv2.INTER_LINEAR)
                
                # Apply threshold
                binary_mask = (mask_np_resized > threshold).astype(np.uint8) * 255
                
                # Calculate metrics
                cloud_pixels = np.sum(binary_mask > 0)
                cloud_coverage = float(cloud_pixels / total_pixels) * 100.0
                
                # Confidence score based on prediction certainty (distance from 0.5 threshold)
                confidence = float(np.mean(1.0 - 2.0 * np.abs(mask_np_resized - 0.5)))
                
                # Post-process binary mask to clean edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
                binary_mask = cv2.dilate(binary_mask, kernel, iterations=1)
                
                cv2.imwrite(str(output_path), binary_mask)
                logger.info(f"DL Cloud Detection: coverage={cloud_coverage:.2f}%, confidence={confidence:.2f}")
                return cloud_coverage, confidence
                
            except Exception as e:
                logger.error(f"DL inference failed: {e}. Falling back to classical method.")
                
        # Classical Fallback
        # Convert to HSV (Hue, Saturation, Value)
        # In HSV, clouds are highly bright (high Value) and neutral color (low Saturation).
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h_val, s_val, v_val = cv2.split(img_hsv)
        
        # Normalize Saturation and Value to [0, 1]
        s_norm = s_val.astype(np.float32) / 255.0
        v_norm = v_val.astype(np.float32) / 255.0
        
        # Cloud Index = Value * (1.0 - Saturation)
        cloud_index = v_norm * (1.0 - s_norm)
        
        # Adaptive Threshold (uses threshold parameter)
        # Standard threshold for cloud detection in index space is around 0.6 to 0.7.
        # Adjusted by user threshold (lower threshold = more clouds detected)
        adjusted_thresh = 0.85 - (threshold * 0.4) # maps threshold [0,1] to [0.85, 0.45]
        
        binary_mask = (cloud_index > adjusted_thresh).astype(np.uint8) * 255
        
        # Morphological operations to clean up small artifacts and fill holes
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel_open)
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # Dilation to cover outer cloud boundaries and halos
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary_mask = cv2.dilate(binary_mask, kernel_dilate, iterations=1)
        
        # Metrics
        cloud_pixels = np.sum(binary_mask > 0)
        cloud_coverage = float(cloud_pixels / total_pixels) * 100.0
        
        # Confidence score based on contrast difference
        confidence = 0.82 + (0.10 * (1.0 - np.mean(s_norm[binary_mask > 0]))) if cloud_pixels > 0 else 0.95
        confidence = float(np.clip(confidence, 0.0, 1.0))
        
        cv2.imwrite(str(output_path), binary_mask)
        logger.info(f"Classical Cloud Detection: coverage={cloud_coverage:.2f}%, confidence={confidence:.2f}")
        
        return cloud_coverage, confidence

cloud_detection_service = CloudDetectionService()
