import os
import sys
import unittest
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set up path so we can import 'app'
backend_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(backend_dir))
sys.path.append(str(backend_dir / "app"))

from app.core.config import settings
from app.services.storage import storage_service
from app.services.geospatial import geospatial_service
from app.services.detection import cloud_detection_service
from app.services.reconstruction import surface_reconstruction_service
from fastapi.testclient import TestClient
from app.main import app

class TestTerraClearPlatform(unittest.TestCase):
    def setUp(self):
        # Create a test directory inside c:\TerraClear\data\test_temp
        self.test_dir = Path("c:/TerraClear/data/test_temp")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy image
        self.dummy_image_path = self.test_dir / "test_image.png"
        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        # Add a "cloud" (bright white patch)
        img[30:70, 30:70, :] = 255
        cv2.imwrite(str(self.dummy_image_path), img)
        
        # Create a dummy mask
        self.dummy_mask_path = self.test_dir / "test_mask.png"
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:70, 30:70] = 255
        cv2.imwrite(str(self.dummy_mask_path), mask)

    def tearDown(self):
        # Clean up files in temp directory
        if self.dummy_image_path.exists():
            os.remove(self.dummy_image_path)
        if self.dummy_mask_path.exists():
            os.remove(self.dummy_mask_path)
        if self.test_dir.exists():
            try:
                os.rmdir(self.test_dir)
            except OSError:
                pass

    def test_storage_service(self):
        """Test UUID generation, upload paths, and metadata saving/loading."""
        img_id = storage_service.generate_id()
        self.assertTrue(len(img_id) > 10)
        
        # Test paths
        upload_path = storage_service.get_upload_path(img_id, ".tif")
        self.assertEqual(upload_path.name, f"{img_id}.tif")
        
        processed_path = storage_service.get_processed_path(img_id, "mask", ".png")
        self.assertEqual(processed_path.name, f"{img_id}_mask.png")
        
        # Save metadata
        meta_data = {"test_key": "test_value"}
        storage_service.save_metadata(img_id, meta_data)
        
        loaded_meta = storage_service.get_metadata(img_id)
        self.assertIsNotNone(loaded_meta)
        self.assertEqual(loaded_meta["test_key"], "test_value")
        
        # Cleanup test metadata file
        meta_file = settings.UPLOAD_DIR / f"{img_id}_meta.json"
        if meta_file.exists():
            os.remove(meta_file)

    def test_geospatial_service_fallback(self):
        """Test metadata extraction fallback on standard PNG image."""
        metadata, has_geo = geospatial_service.extract_metadata(self.dummy_image_path)
        self.assertFalse(has_geo)
        self.assertEqual(metadata["width"], 100)
        self.assertEqual(metadata["height"], 100)
        self.assertEqual(metadata["bands"], 3)

    def test_cloud_detection(self):
        """Test classical HSV cloud detection on dummy image."""
        output_mask_path = self.test_dir / "output_mask.png"
        
        coverage, confidence = cloud_detection_service.detect_clouds(
            self.dummy_image_path,
            output_mask_path,
            threshold=0.5,
            force_classical=True
        )
        
        self.assertTrue(output_mask_path.exists())
        self.assertTrue(coverage > 0)
        self.assertTrue(0 <= confidence <= 1.0)
        
        os.remove(output_mask_path)

    def test_surface_reconstruction(self):
        """Test classical Navier-Stokes/Telea inpainting surface reconstruction."""
        output_rebuild_path = self.test_dir / "output_rebuild.png"
        
        confidence = surface_reconstruction_service.reconstruct_surface(
            self.dummy_image_path,
            self.dummy_mask_path,
            output_rebuild_path,
            cloud_coverage_percentage=16.0,
            force_classical=True
        )
        
        self.assertTrue(output_rebuild_path.exists())
        self.assertTrue(0 <= confidence <= 1.0)
        
        os.remove(output_rebuild_path)

    def test_api_health_check(self):
        """Test health-check API endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_api_upload_failure_on_invalid_format(self):
        """Test uploading files with invalid extensions returns a 400 error."""
        client = TestClient(app)
        response = client.post(
            "/api/imagery/upload",
            files={"file": ("invalid.txt", b"dummy text content", "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file format", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
