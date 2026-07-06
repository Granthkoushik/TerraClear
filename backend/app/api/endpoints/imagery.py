import time
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.logging import logger
from app.schemas.imagery import UploadResponse, ProcessRequest, ProcessResponse, GeospatialMetadata
from app.services.storage import storage_service
from app.services.geospatial import geospatial_service
from app.services.detection import cloud_detection_service
from app.services.reconstruction import surface_reconstruction_service

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload a satellite imagery file (GeoTIFF, TIFF, PNG, JPG).
    Validates, stores the image, and extracts metadata.
    """
    logger.info(f"Received upload request for file: {file.filename}")
    
    # Verify file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Only GeoTIFF, TIFF, PNG, and JPG are supported."
        )
        
    try:
        # Save file to disk
        image_id = storage_service.generate_id()
        content = await file.read()
        saved_path = storage_service.save_upload(image_id, file.filename, content)
        
        # Extract metadata
        metadata_dict, has_geo = geospatial_service.extract_metadata(saved_path)
        
        # Save metadata to disk
        storage_service.save_metadata(image_id, {
            "image_id": image_id,
            "filename": file.filename,
            "has_geospatial": has_geo,
            "metadata": metadata_dict
        })
        
        # Build response model
        geo_meta = None
        if has_geo:
            geo_meta = GeospatialMetadata(**metadata_dict)
            
        return UploadResponse(
            image_id=image_id,
            filename=file.filename,
            width=metadata_dict["width"],
            height=metadata_dict["height"],
            bands=metadata_dict["bands"],
            size_bytes=metadata_dict["size_bytes"],
            has_geospatial=has_geo,
            metadata=geo_meta
        )
        
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process and store upload: {str(e)}")


@router.post("/process", response_model=ProcessResponse)
async def process_image(request: ProcessRequest):
    """
    Executes cloud detection and surface reconstruction on the uploaded image.
    """
    logger.info(f"Starting processing for image ID: {request.image_id}")
    
    # 1. Locate original file
    original_path = storage_service.find_original_file(request.image_id)
    if not original_path or not original_path.exists():
        raise HTTPException(status_code=404, detail=f"Image with ID {request.image_id} not found.")
        
    try:
        start_time = time.time()
        
        # 2. Define output paths
        mask_path = storage_service.get_processed_path(request.image_id, "mask")
        reconstructed_path = storage_service.get_processed_path(request.image_id, "reconstructed")
        
        # 3. Detect clouds
        cloud_coverage, detection_confidence = cloud_detection_service.detect_clouds(
            original_path, 
            mask_path, 
            threshold=request.detection_threshold, 
            force_classical=request.force_classical
        )
        
        # 4. Remove clouds & reconstruct surface
        reconstruction_confidence = surface_reconstruction_service.reconstruct_surface(
            original_path, 
            mask_path, 
            reconstructed_path, 
            cloud_coverage, 
            force_classical=request.force_classical
        )
        
        processing_time = time.time() - start_time
        
        # Combined confidence score
        final_confidence = (detection_confidence + reconstruction_confidence) / 2.0
        
        # Construct endpoints
        original_url = f"{settings.API_V1_STR}/imagery/download/{request.image_id}/original"
        mask_url = f"{settings.API_V1_STR}/imagery/download/{request.image_id}/mask"
        reconstructed_url = f"{settings.API_V1_STR}/imagery/download/{request.image_id}/reconstructed"
        
        # Update metadata json with processing results
        metadata = storage_service.get_metadata(request.image_id)
        if metadata:
            metadata["processing"] = {
                "cloud_coverage_percentage": cloud_coverage,
                "confidence_score": final_confidence,
                "processing_time_seconds": processing_time
            }
            storage_service.save_metadata(request.image_id, metadata)
            
        return ProcessResponse(
            image_id=request.image_id,
            cloud_coverage_percentage=round(cloud_coverage, 2),
            confidence_score=round(final_confidence, 2),
            processing_time_seconds=round(processing_time, 3),
            original_url=original_url,
            mask_url=mask_url,
            reconstructed_url=reconstructed_url
        )
        
    except Exception as e:
        logger.error(f"Failed to process image {request.image_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Image processing pipeline failed: {str(e)}")


@router.get("/download/{image_id}/{file_type}")
async def download_file(image_id: str, file_type: str):
    """
    Downloads original, mask, or reconstructed images.
    """
    if file_type not in ["original", "mask", "reconstructed"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Options are original, mask, reconstructed.")
        
    if file_type == "original":
        file_path = storage_service.find_original_file(image_id)
    elif file_type == "mask":
        file_path = storage_service.get_processed_path(image_id, "mask")
    else:
        file_path = storage_service.get_processed_path(image_id, "reconstructed")
        
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Requested {file_type} file for ID {image_id} not found.")
        
    media_type = "image/png"
    if file_path.suffix.lower() in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif file_path.suffix.lower() in [".tif", ".tiff"]:
        media_type = "image/tiff"
        
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)
