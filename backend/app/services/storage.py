import os
import uuid
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger

class StorageService:
    def __init__(self):
        # Create necessary directories
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        settings.WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def get_upload_path(self, image_id: str, suffix: str = "") -> Path:
        """Returns the path where the uploaded original file is stored."""
        return settings.UPLOAD_DIR / f"{image_id}{suffix}"

    def find_original_file(self, image_id: str) -> Optional[Path]:
        """Finds the uploaded original file path by checking for existing extensions."""
        # Check files matching the UUID
        for f in settings.UPLOAD_DIR.glob(f"{image_id}.*"):
            if not f.name.endswith("_meta.json") and not f.name.endswith(".json"):
                return f
        return None

    def get_processed_path(self, image_id: str, file_type: str, suffix: str = ".png") -> Path:
        """Returns the path for processed files: 'mask' or 'reconstructed'."""
        return settings.PROCESSED_DIR / f"{image_id}_{file_type}{suffix}"

    def save_upload(self, image_id: str, filename: str, content: bytes) -> Path:
        """Saves uploaded raw bytes to the uploads directory."""
        ext = os.path.splitext(filename)[1].lower()
        if not ext:
            ext = ".png" # default fallback
        
        dest_path = self.get_upload_path(image_id, ext)
        with open(dest_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved uploaded image {filename} to {dest_path}")
        return dest_path

    def save_metadata(self, image_id: str, metadata: Dict[str, Any]) -> None:
        """Saves geospatial and image metadata to a json file next to the image."""
        meta_path = settings.UPLOAD_DIR / f"{image_id}_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Saved metadata for image {image_id} to {meta_path}")

    def get_metadata(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves saved metadata for an image ID."""
        meta_path = settings.UPLOAD_DIR / f"{image_id}_meta.json"
        if not meta_path.exists():
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_image_files(self, image_id: str) -> bool:
        """Deletes all original, processed, and metadata files associated with an ID."""
        deleted = False
        # Remove original file (we search because extension is unknown)
        for f in settings.UPLOAD_DIR.glob(f"{image_id}*"):
            try:
                os.remove(f)
                deleted = True
            except OSError as e:
                logger.error(f"Failed to delete original file {f}: {e}")
                
        # Remove processed files
        for f in settings.PROCESSED_DIR.glob(f"{image_id}*"):
            try:
                os.remove(f)
                deleted = True
            except OSError as e:
                logger.error(f"Failed to delete processed file {f}: {e}")
                
        return deleted

storage_service = StorageService()
