import cv2
import numpy as np
from pathlib import Path

def generate_satellite_scene():
    """Generates a synthetic satellite scene (512x512) representing LISS-IV data."""
    width, height = 512, 512
    # 1. Base terrain (vegetation/forest - rich green)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Generate green land textures using overlaying circles/gradients
    for i in range(150):
        cx = np.random.randint(0, width)
        cy = np.random.randint(0, height)
        r = np.random.randint(40, 150)
        # Varying shades of forest green and agricultural fields
        g_val = np.random.randint(90, 160)
        r_val = np.random.randint(40, 90)
        b_val = np.random.randint(20, 60)
        cv2.circle(img, (cx, cy), r, (b_val, g_val, r_val), -1)
        
    # Smooth the texture slightly
    img = cv2.GaussianBlur(img, (15, 15), 0)
    
    # Add agriculture grid lines (faint lines mimicking land parcels)
    for x in range(0, width, 64):
        cv2.line(img, (x, 0), (x + np.random.randint(-5, 5), height), (20, 80, 30), 1)
    for y in range(0, height, 64):
        cv2.line(img, (0, y), (width, y + np.random.randint(-5, 5)), (20, 80, 30), 1)

    # 2. Add a winding river (Dark blue/cyan waterbody)
    river_points = []
    for y in range(0, height + 20, 20):
        # A sinusoidal winding path
        x = int(256 + 100 * np.sin(y / 80.0) + 20 * np.cos(y / 30.0))
        river_points.append((x, y))
        
    for i in range(len(river_points) - 1):
        cv2.line(img, river_points[i], river_points[i+1], (130, 80, 20), 16) # Outer river bed
        cv2.line(img, river_points[i], river_points[i+1], (180, 120, 30), 10) # Inner water channel
        
    # Apply blur again to blend water margins
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Save a copy of the clear sky terrain for comparison (not containing clouds)
    clear_sky = img.copy()

    # 3. Add clouds and their corresponding shadows
    # Shadows first (offset from cloud center)
    shadow_offset_x = 15
    shadow_offset_y = 12
    
    cloud_centers = [
        (120, 150, 45), # x, y, radius
        (150, 180, 35),
        (380, 320, 55),
        (400, 300, 40)
    ]
    
    # Render shadows: translucent black/dark grey
    shadow_mask = np.zeros((height, width), dtype=np.uint8)
    for cx, cy, r in cloud_centers:
        cv2.circle(shadow_mask, (cx + shadow_offset_x, cy + shadow_offset_y), r, 255, -1)
    shadow_mask = cv2.GaussianBlur(shadow_mask, (31, 31), 0)
    
    # Overlay shadows on image by darkening matching pixels
    img_f = img.astype(np.float32)
    shadow_factor = 1.0 - (shadow_mask.astype(np.float32) / 255.0) * 0.45
    for c in range(3):
        img_f[:, :, c] *= shadow_factor
    img = img_f.astype(np.uint8)

    # Render clouds: puffy bright white circles with soft edges
    cloud_mask = np.zeros((height, width), dtype=np.uint8)
    for cx, cy, r in cloud_centers:
        cv2.circle(cloud_mask, (cx, cy), r, 255, -1)
    
    cloud_mask_blurred = cv2.GaussianBlur(cloud_mask, (41, 41), 0)
    cloud_mask_f = cloud_mask_blurred.astype(np.float32) / 255.0
    
    # Blend white clouds into the image
    for c in range(3):
        img[:, :, c] = (img[:, :, c] * (1.0 - cloud_mask_f) + 255 * cloud_mask_f).astype(np.uint8)

    # Save file
    data_dir = Path("c:/TerraClear/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    sample_path = data_dir / "sample_liss4.png"
    cv2.imwrite(str(sample_path), img)
    print(f"Generated sample LISS-IV satellite image with clouds at: {sample_path.resolve()}")
    
    # Also save clear sky ground truth for inspection or validation
    gt_path = data_dir / "sample_liss4_ground_truth.png"
    cv2.imwrite(str(gt_path), clear_sky)

if __name__ == "__main__":
    generate_satellite_scene()
