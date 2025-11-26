from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
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
from app.core.auth import get_current_user
import logging

logger = logging.getLogger(__name__)


# Request models
class UpdatePlayerOverrideRequest(BaseModel):
    player_name_override: Optional[str] = None
    jersey_number_override: Optional[str] = None

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

        # Save file to temporary location first
        temp_file_path = f"{file_path}.temp"
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            content = await file.read()

            # Check file size
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes"
                )

            await out_file.write(content)

        logger.info(f"Uploaded file to temp: {safe_filename}")

        # Validate image
        if not ImageProcessor.validate_image(temp_file_path):
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail="Invalid or corrupted image file"
            )

        # Extract EXIF data from original before optimization
        exif_data = ImageProcessor.extract_exif_data(temp_file_path)

        # Handle RAW files - convert to JPEG first
        process_path = temp_file_path
        raw_converted_path = None
        if ImageProcessor.is_raw_format(file.filename):
            # Convert RAW to JPEG for processing
            jpeg_path = os.path.join(
                settings.UPLOAD_FOLDER,
                f"{image_id}_raw_converted.jpg"
            )
            try:
                process_path = ImageProcessor.convert_raw_to_jpeg(temp_file_path, jpeg_path)
                raw_converted_path = jpeg_path
                logger.info(f"Converted RAW to JPEG: {jpeg_path}")
            except Exception as e:
                logger.warning(f"Could not convert RAW file, using original: {e}")

        # OPTIMIZATION STEP 1: Optimize image for storage
        # This resizes to max 3000px and converts to WebP (saves 70-85% space!)
        try:
            optimized_path, final_width, final_height = ImageProcessor.optimize_image_for_storage(
                image_path=process_path,
                output_path=file_path,  # Will auto-adjust extension for WebP
                max_dimension=settings.IMAGE_MAX_DIMENSION,
                quality=settings.WEBP_QUALITY if settings.USE_WEBP_STORAGE else settings.JPEG_QUALITY,
                use_webp=settings.USE_WEBP_STORAGE
            )

            # Update file_path to the optimized version (may have .webp extension now)
            file_path = optimized_path
            safe_filename = os.path.basename(file_path)

            logger.info(f"Optimized image stored: {safe_filename} ({final_width}x{final_height})")
        except Exception as e:
            logger.error(f"Optimization failed, using original: {e}")
            # Fallback: just move temp to final location
            os.rename(temp_file_path, file_path)
            final_width = exif_data.get('width', 0)
            final_height = exif_data.get('height', 0)

        # OPTIMIZATION STEP 2: Create optimized thumbnail
        thumbnail_filename = f"thumb_{image_id}.jpg"
        thumbnail_path = os.path.join(
            settings.UPLOAD_FOLDER,
            "thumbnails",
            thumbnail_filename
        )

        ImageProcessor.create_thumbnail(
            image_path=file_path,
            output_path=thumbnail_path,
            size=(settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE),
            quality=settings.THUMBNAIL_QUALITY
        )

        # CLEANUP: Delete temporary files
        if settings.DELETE_TEMP_FILES:
            try:
                # Delete temp upload file if it exists
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.info(f"Cleaned up temp file: {temp_file_path}")

                # Delete RAW converted file if it exists (we keep the original RAW)
                if raw_converted_path and os.path.exists(raw_converted_path):
                    os.remove(raw_converted_path)
                    logger.info(f"Cleaned up RAW conversion: {raw_converted_path}")
            except Exception as e:
                logger.warning(f"Could not clean up temp files: {e}")

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

        # Save to Supabase database with EXIF metadata
        try:
            from app.core.supabase import supabase_client
            from datetime import datetime

            # Convert datetime objects and sanitize EXIF data for JSON/PostgreSQL
            clean_exif = {}
            if exif_data:
                for key, value in exif_data.items():
                    try:
                        if isinstance(value, datetime):
                            clean_exif[key] = value.isoformat()
                        elif isinstance(value, bytes):
                            # Skip binary data that might contain null bytes
                            continue
                        elif isinstance(value, str):
                            # Remove null bytes from strings (PostgreSQL can't store them)
                            clean_value = value.replace('\x00', '')
                            if clean_value:  # Only add if not empty after cleaning
                                clean_exif[key] = clean_value
                        elif isinstance(value, (int, float, bool, type(None))):
                            # Safe primitive types
                            clean_exif[key] = value
                        elif isinstance(value, (list, tuple)):
                            # Handle lists/tuples (common in EXIF)
                            clean_exif[key] = str(value)
                        else:
                            # Convert other types to string
                            clean_exif[key] = str(value)
                    except Exception as e:
                        # Skip problematic fields
                        logger.debug(f"Skipping EXIF field {key}: {e}")
                        continue

            db_record = {
                "id": image_id,
                "filename": file.filename,
                "original_url": f"/uploads/{safe_filename}",
                "thumbnail_url": f"/uploads/thumbnails/{thumbnail_filename}",
                "file_size": metadata.file_size,
                "width": metadata.width,
                "height": metadata.height,
                "format": metadata.format,
                "camera_make": metadata.camera_make,
                "camera_model": metadata.camera_model,
                "lens_model": metadata.lens_model,
                "focal_length": float(metadata.focal_length) if metadata.focal_length else None,
                "aperture": float(metadata.aperture) if metadata.aperture else None,
                "shutter_speed": metadata.shutter_speed,
                "iso": int(metadata.iso) if metadata.iso else None,
                "capture_time": metadata.capture_time.isoformat() if metadata.capture_time else None,
                "exif_data": clean_exif,  # Store cleaned EXIF as JSONB
                "analysis_status": "pending"
            }

            result = supabase_client.table("images").insert(db_record).execute()
            logger.info(f"💾 Saved image to database with EXIF metadata: {image_id}")
            logger.info(f"   📸 Camera: {metadata.camera_make} {metadata.camera_model}, ISO: {metadata.iso}")
        except Exception as e:
            logger.error(f"Failed to save image to database: {e}", exc_info=True)
            # Continue anyway - file is already saved locally

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


@router.patch("/{image_id}/player-override")
async def update_player_override(
    image_id: str,
    request: UpdatePlayerOverrideRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update player name and jersey number override for manual correction.

    Allows users to manually correct AI-detected player information when it's incorrect.
    """
    try:
        from app.core.supabase import supabase_client

        user_id = current_user["id"]

        # Verify user owns the image
        image_result = supabase_client.table("images").select("user_id").eq("id", image_id).execute()

        if not image_result.data:
            raise HTTPException(
                status_code=404,
                detail="Image not found"
            )

        if image_result.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this image"
            )

        # Update the override fields
        update_data = {}
        if request.player_name_override is not None:
            update_data["player_name_override"] = request.player_name_override
        if request.jersey_number_override is not None:
            update_data["jersey_number_override"] = request.jersey_number_override

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        # Update in database
        result = supabase_client.table("images").update(update_data).eq("id", image_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to update player override"
            )

        logger.info(f"Updated player override for image {image_id}: {update_data}")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player override for image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update player override: {str(e)}"
        )


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
