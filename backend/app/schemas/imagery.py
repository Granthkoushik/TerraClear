from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class GeospatialMetadata(BaseModel):
    crs: Optional[str] = Field(None, description="Coordinate Reference System")
    bounds: Optional[Dict[str, float]] = Field(None, description="Bounding box limits (left, bottom, right, top)")
    transform: Optional[Dict[str, float]] = Field(None, description="Affine transform coefficients")
    projection: Optional[str] = Field(None, description="WKT projection description")
    resolution: Optional[Dict[str, float]] = Field(None, description="Pixel resolution in map units")
    center: Optional[Dict[str, float]] = Field(None, description="Approximate geographic center")

class UploadResponse(BaseModel):
    image_id: str = Field(..., description="Unique UUID generated for the uploaded image")
    filename: str = Field(..., description="Original name of the uploaded file")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    bands: int = Field(..., description="Number of spectral/color bands")
    size_bytes: int = Field(..., description="Size of the file on disk in bytes")
    has_geospatial: bool = Field(..., description="True if the image contains geo-referencing tags")
    metadata: Optional[GeospatialMetadata] = Field(None, description="Extracted LISS-IV geospatial tags")

class ProcessRequest(BaseModel):
    image_id: str = Field(..., description="Unique UUID of the uploaded image to process")
    detection_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Sensitivity threshold for cloud detection")
    force_classical: bool = Field(False, description="Force classical digital image processing instead of PyTorch DL models")

class ProcessResponse(BaseModel):
    image_id: str = Field(..., description="Unique UUID of the processed image")
    cloud_coverage_percentage: float = Field(..., description="Calculated percentage of cloud coverage in the image")
    confidence_score: float = Field(..., description="Reconstruction confidence score based on the model or DIP outputs")
    processing_time_seconds: float = Field(..., description="Total time taken to run detection and reconstruction")
    original_url: str = Field(..., description="Endpoint path to download the original image")
    mask_url: str = Field(..., description="Endpoint path to download the generated cloud mask")
    reconstructed_url: str = Field(..., description="Endpoint path to download the reconstructed surface image")
