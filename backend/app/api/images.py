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


class JerseyNumberDetection(BaseModel):
    """Model for a detected jersey number in a group photo."""
    number: str
    confidence: float
    player_name: Optional[str] = None


class UpdateGroupPhotoDataRequest(BaseModel):
    detected_jersey_numbers: Optional[List[JerseyNumberDetection]] = None
    player_names: Optional[List[str]] = None


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

        # Verify image exists
        image_result = supabase_client.table("images").select("id").eq("id", image_id).execute()

        if not image_result.data:
            raise HTTPException(
                status_code=404,
                detail="Image not found"
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


@router.patch("/{image_id}/group-photo-data")
async def update_group_photo_data(
    image_id: str,
    request: UpdateGroupPhotoDataRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update group photo player data (detected jersey numbers and player names arrays).

    For group photos with multiple players detected.
    """
    try:
        from app.core.supabase import supabase_client

        logger.info(f"Updating group photo data for image {image_id}")
        logger.info(f"Request data: detected_jersey_numbers={request.detected_jersey_numbers}, player_names={request.player_names}")

        # Verify image exists
        image_result = supabase_client.table("images").select("id").eq("id", image_id).execute()

        if not image_result.data:
            raise HTTPException(
                status_code=404,
                detail="Image not found"
            )

        # Update the group photo arrays
        # Convert Pydantic models to dicts for database
        update_data = {}
        if request.detected_jersey_numbers is not None:
            update_data["detected_jersey_numbers"] = [
                jersey.model_dump() for jersey in request.detected_jersey_numbers
            ]
        if request.player_names is not None:
            update_data["player_names"] = request.player_names

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        logger.info(f"Updating database with: {update_data}")

        # Update in database
        result = supabase_client.table("images").update(update_data).eq("id", image_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to update group photo data"
            )

        logger.info(f"✅ Updated group photo data for image {image_id}")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating group photo data for image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update group photo data: {str(e)}"
        )


@router.get("/")
async def get_images(
    team_id: Optional[str] = None,
    player_id: Optional[str] = None,
    quality_tier: Optional[str] = None,
    hide_duplicates: bool = False,
    in_library: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get images with optional filtering.

    Supports filtering by:
    - team_id: Filter by team
    - player_id: Filter by player
    - quality_tier: excellent, good, acceptable, poor
    - hide_duplicates: If true, only show best from each duplicate group
    - in_library: If false, exclude images saved to library (default: show all)
    - limit/offset: Pagination

    Returns images grouped by duplicate_group_id if duplicates exist.
    """
    try:
        from app.core.supabase import supabase_client

        # Build query
        query = supabase_client.table("images").select("*")

        # Apply filters
        if team_id:
            query = query.eq("team_id", team_id)
        if player_id:
            query = query.eq("player_id", player_id)
        if quality_tier:
            query = query.eq("quality_tier", quality_tier)
        if hide_duplicates:
            # Only show images that aren't marked as duplicates
            query = query.or_("is_duplicate.is.null,is_duplicate.eq.false")

        # NOTE: in_library parameter is NO LONGER used to filter workspace images
        # Workspace should ALWAYS show all original images, regardless of whether
        # they have enhanced copies in the library. The is_saved_to_library flag
        # is just an indicator, not a filter criteria.
        #
        # This ensures that:
        # 1. Saving an enhanced copy to library doesn't hide the original from workspace
        # 2. Deleting from library doesn't affect the workspace
        # 3. Users can create multiple enhanced versions of the same original

        # Order by capture time or created_at
        query = query.order("created_at", desc=True)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        result = query.execute()
        images = result.data

        # Enrich images with player names by joining with players table
        player_ids = [img.get('player_id') for img in images if img.get('player_id')]
        player_map = {}

        if player_ids:
            try:
                # Fetch player names in batch
                players_result = supabase_client.table("players").select("id,first_name,last_name").in_("id", player_ids).execute()
                player_map = {
                    p['id']: f"{p['first_name']} {p['last_name']}"
                    for p in players_result.data
                }
            except Exception as e:
                logger.warning(f"Could not fetch player names: {e}")

        # Add player_name to each image
        for img in images:
            player_id = img.get('player_id')
            if player_id and player_id in player_map:
                img['player_name'] = player_map[player_id]

        # Group images by duplicate_group_id
        grouped_images = []
        duplicate_groups = {}

        for img in images:
            group_id = img.get('duplicate_group_id')

            if group_id:
                # This image is part of a duplicate group
                if group_id not in duplicate_groups:
                    duplicate_groups[group_id] = {
                        'group_id': group_id,
                        'images': [],
                        'best_image_id': None,
                        'count': 0
                    }

                duplicate_groups[group_id]['images'].append(img)
                duplicate_groups[group_id]['count'] += 1

                # Track which is the best (is_duplicate = false)
                if not img.get('is_duplicate'):
                    duplicate_groups[group_id]['best_image_id'] = img['id']
            else:
                # Standalone image, not a duplicate
                grouped_images.append({
                    'image': img,
                    'is_group': False,
                    'group': None
                })

        # Add duplicate groups to result
        for group_id, group_data in duplicate_groups.items():
            # Sort images in group by score (best first)
            group_data['images'].sort(
                key=lambda x: -(x.get('overall_score') or 0)
            )

            best_image = next(
                (img for img in group_data['images'] if img['id'] == group_data['best_image_id']),
                group_data['images'][0]
            )

            grouped_images.append({
                'image': best_image,  # Show best image
                'is_group': True,
                'group': {
                    'id': group_id,
                    'count': group_data['count'],
                    'images': group_data['images'],
                    'best_image_id': group_data['best_image_id']
                }
            })

        logger.info(f"Fetched {len(images)} images, grouped into {len(grouped_images)} items")

        return {
            'images': grouped_images,
            'total': len(images),
            'offset': offset,
            'limit': limit,
            'filters': {
                'team_id': team_id,
                'player_id': player_id,
                'quality_tier': quality_tier,
                'hide_duplicates': hide_duplicates
            }
        }

    except Exception as e:
        logger.error(f"Error fetching images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """
    Delete an image by ID.

    Removes from storage and database.
    """
    try:
        from app.core.supabase import supabase_client

        # Get image info first
        result = supabase_client.table("images").select("original_url,thumbnail_url").eq("id", image_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Image not found")

        image_data = result.data[0]

        # Delete files from storage
        try:
            # Delete original image
            if image_data.get('original_url'):
                file_path = os.path.join(settings.UPLOAD_FOLDER, os.path.basename(image_data['original_url']))
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")

            # Delete thumbnail
            if image_data.get('thumbnail_url'):
                thumb_path = os.path.join(settings.UPLOAD_FOLDER, os.path.basename(image_data['thumbnail_url']))
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    logger.info(f"Deleted thumbnail: {thumb_path}")
        except Exception as e:
            logger.warning(f"Error deleting files for image {image_id}: {e}")
            # Continue with database deletion even if file deletion fails

        # Delete from database
        supabase_client.table("images").delete().eq("id", image_id).execute()

        logger.info(f"Successfully deleted image {image_id}")

        return {
            "id": image_id,
            "message": "Image deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
