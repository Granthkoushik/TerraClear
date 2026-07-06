import rasterio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image
from app.core.logging import logger

class GeospatialService:
    @staticmethod
    def extract_metadata(file_path: Path) -> Tuple[Dict[str, Any], bool]:
        """
        Extracts geospatial tags and basic dimensions from the uploaded image.
        Returns a dictionary of metadata and a boolean indicating whether it has georeferencing.
        """
        metadata = {
            "crs": None,
            "bounds": None,
            "transform": None,
            "projection": None,
            "resolution": None,
            "center": None,
            "width": 0,
            "height": 0,
            "bands": 0,
            "size_bytes": file_path.stat().st_size
        }
        
        # Try reading with rasterio first
        try:
            with rasterio.open(file_path) as src:
                metadata["width"] = src.width
                metadata["height"] = src.height
                metadata["bands"] = src.count
                
                # Check for georeferencing
                if src.crs is not None:
                    metadata["crs"] = src.crs.to_string()
                    metadata["projection"] = src.crs.to_wkt()
                    
                    bounds = src.bounds
                    metadata["bounds"] = {
                        "left": float(bounds.left),
                        "bottom": float(bounds.bottom),
                        "right": float(bounds.right),
                        "top": float(bounds.top)
                    }
                    
                    transform = src.transform
                    metadata["transform"] = {
                        "a": float(transform.a),
                        "b": float(transform.b),
                        "c": float(transform.c),
                        "d": float(transform.d),
                        "e": float(transform.e),
                        "f": float(transform.f)
                    }
                    
                    res = src.res
                    metadata["resolution"] = {
                        "x": float(res[0]),
                        "y": float(res[1])
                    }
                    
                    # Calculate center
                    center_x = (bounds.left + bounds.right) / 2.0
                    center_y = (bounds.bottom + bounds.top) / 2.0
                    metadata["center"] = {
                        "x": float(center_x),
                        "y": float(center_y)
                    }
                    
                    logger.info(f"Successfully extracted GeoTIFF tags for {file_path.name}. CRS: {metadata['crs']}")
                    return metadata, True
                else:
                    logger.info(f"TIFF file {file_path.name} does not contain geospatial tags.")
                    
        except Exception as e:
            logger.warning(f"Rasterio could not open {file_path.name} or extract geospatial tags: {e}. Trying PIL fallback.")

        # Fallback to standard Image reading via Pillow
        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["bands"] = len(img.getbands())
                logger.info(f"Extracted basic dimensions using PIL fallback for {file_path.name}")
        except Exception as pil_err:
            logger.error(f"Failed to read image {file_path.name} with PIL: {pil_err}")
            
        return metadata, False

geospatial_service = GeospatialService()
