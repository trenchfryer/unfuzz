from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import aiofiles
import os
import uuid
from datetime import datetime
from app.models.image import (
    ImageUploadResponse,
    ImageMetadata,
    AnalysisStatus
)
from app.utils.image_processing import ImageProcessor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(f"{settings.UPLOAD_FOLDER}/thumbnails", exist_ok=True)


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload a single image file.

    Returns image metadata and queues for AI analysis.
    """
    try:
        # Validate file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
            )

        # Generate unique ID and filename
        image_id = str(uuid.uuid4())
        safe_filename = f"{image_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_FOLDER, safe_filename)

        # Save file
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()

            # Check file size
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes"
                )

            await out_file.write(content)

        logger.info(f"Uploaded file: {safe_filename}")

        # Validate image
        if not ImageProcessor.validate_image(file_path):
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Invalid or corrupted image file"
            )

        # Extract EXIF data
        exif_data = ImageProcessor.extract_exif_data(file_path)

        # Create thumbnail
        thumbnail_filename = f"thumb_{image_id}.jpg"
        thumbnail_path = os.path.join(
            settings.UPLOAD_FOLDER,
            "thumbnails",
            thumbnail_filename
        )

        # Handle RAW files
        process_path = file_path
        if ImageProcessor.is_raw_format(file.filename):
            # Convert RAW to JPEG for processing
            jpeg_path = os.path.join(
                settings.UPLOAD_FOLDER,
                f"{image_id}_converted.jpg"
            )
            try:
                process_path = ImageProcessor.convert_raw_to_jpeg(file_path, jpeg_path)
            except Exception as e:
                logger.warning(f"Could not convert RAW file, using original: {e}")

        ImageProcessor.create_thumbnail(process_path, thumbnail_path)

        # Create metadata object
        metadata = ImageMetadata(
            filename=file.filename,
            file_size=ImageProcessor.get_file_size(file_path),
            width=exif_data.get('width', 0),
            height=exif_data.get('height', 0),
            format=exif_data.get('format', 'unknown'),
            camera_make=exif_data.get('camera_make'),
            camera_model=exif_data.get('camera_model'),
            lens_model=exif_data.get('lens_model'),
            focal_length=exif_data.get('focal_length'),
            aperture=exif_data.get('aperture'),
            shutter_speed=exif_data.get('shutter_speed'),
            iso=exif_data.get('iso'),
            capture_time=exif_data.get('capture_time'),
            exif_data=exif_data
        )

        # In production, this would save to Supabase and return database record
        # For now, return mock response
        response = ImageUploadResponse(
            id=image_id,
            filename=file.filename,
            url=f"/uploads/{safe_filename}",
            thumbnail_url=f"/uploads/thumbnails/{thumbnail_filename}",
            metadata=metadata,
            status=AnalysisStatus.PENDING
        )

        logger.info(f"Image uploaded successfully: {image_id}")
        logger.info(f"  📸 Full file path: {file_path}")
        logger.info(f"  🖼️  Thumbnail path: {thumbnail_path}")
        logger.info(f"  🌐 URL returned: {response.url}")
        logger.info(f"  🌐 Thumbnail URL returned: {response.thumbnail_url}")

        # Test serialize the response to catch any JSON errors early
        try:
            response_dict = response.model_dump()
            logger.info(f"  ✅ Response validated successfully")
        except Exception as e:
            logger.error(f"  ❌ Response validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Response validation error: {str(e)}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-batch", response_model=List[ImageUploadResponse])
async def upload_batch(files: List[UploadFile] = File(...)):
    """
    Upload multiple image files in batch.

    Returns list of upload responses.
    """
    responses = []

    for file in files:
        try:
            response = await upload_image(file)
            responses.append(response)
        except HTTPException as e:
            logger.error(f"Failed to upload {file.filename}: {e.detail}")
            # Continue with other files
            continue
        except Exception as e:
            logger.error(f"Unexpected error uploading {file.filename}: {e}")
            continue

    if not responses:
        raise HTTPException(
            status_code=400,
            detail="No files were successfully uploaded"
        )

    return responses


@router.get("/{image_id}")
async def get_image(image_id: str):
    """
    Get image details by ID.

    In production, this would fetch from Supabase database.
    """
    # TODO: Implement database lookup
    return {
        "id": image_id,
        "message": "Image retrieval not yet implemented"
    }


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """
    Delete an image by ID.

    Removes from storage and database.
    """
    # TODO: Implement deletion
    return {
        "id": image_id,
        "message": "Image deleted successfully"
    }
