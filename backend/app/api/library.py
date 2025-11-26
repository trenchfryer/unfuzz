"""
Enhanced Images Library endpoints
Manage saved/enhanced images with player associations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import logging
from datetime import datetime
import os

from app.core.auth import get_current_user
from app.core.supabase import supabase_client
from app.core.config import settings

router = APIRouter(prefix="/library", tags=["library"])
logger = logging.getLogger(__name__)


# Models
class SaveEnhancedImageRequest(BaseModel):
    original_image_id: UUID
    team_id: Optional[UUID] = None
    player_id: Optional[UUID] = None
    player_name_override: Optional[str] = None
    jersey_number_override: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    save_original: bool = False  # If True, save original instead of enhanced
    post_processing: Optional[dict] = None  # Enhancement settings from analysis


class UpdatePlayerOverrideRequest(BaseModel):
    player_name: Optional[str] = None
    jersey_number: Optional[str] = None


class EnhancedImageResponse(BaseModel):
    id: UUID
    user_id: UUID
    original_image_id: UUID
    team_id: Optional[UUID]
    player_id: Optional[UUID]
    enhanced_url: str
    thumbnail_url: Optional[str]
    player_name_override: Optional[str]
    jersey_number_override: Optional[str]
    title: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    download_count: int
    created_at: datetime
    updated_at: datetime


@router.post("/save", response_model=EnhancedImageResponse, status_code=status.HTTP_201_CREATED)
async def save_enhanced_image(
    request: SaveEnhancedImageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Save an enhanced image to the library.
    Generates the enhanced image, saves it permanently, and stores the reference.
    """
    try:
        import os
        from app.services.image_enhancement import ImageEnhancementService
        from app.models.image import PostProcessingRecommendations
        from app.core.config import settings

        user_id = current_user["id"]

        # Fetch the original image data
        original_image = supabase_client.table("images").select("*").eq("id", str(request.original_image_id)).execute()

        if not original_image.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original image not found"
            )

        image_data = original_image.data[0]

        # Note: images table doesn't have user_id, it's managed by RLS policies
        # The fact that we can fetch it means the user has access via RLS

        # Prepare file paths
        original_path = os.path.join(settings.UPLOAD_FOLDER, os.path.basename(image_data["original_url"]))

        logger.info(f"🔍 Save request - save_original={request.save_original}, original_image_id={request.original_image_id}")

        if request.save_original:
            # Save original - just copy the file
            import shutil
            enhanced_filename = f"original_{request.original_image_id}.jpg"
            enhanced_path = os.path.join(settings.UPLOAD_FOLDER, "enhanced", enhanced_filename)
            os.makedirs(os.path.dirname(enhanced_path), exist_ok=True)
            shutil.copy2(original_path, enhanced_path)
            post_processing_data = {}
            logger.info(f"📁 SAVING ORIGINAL: Copied to {enhanced_path}")
        else:
            # Generate the enhanced image
            enhanced_filename = f"enhanced_{request.original_image_id}.jpg"
            enhanced_path = os.path.join(settings.UPLOAD_FOLDER, "enhanced", enhanced_filename)
            os.makedirs(os.path.dirname(enhanced_path), exist_ok=True)

            # Use post_processing data from request (sent by frontend)
            post_processing_data = request.post_processing or {}

            logger.info(f"✨ SAVING ENHANCED: Will enhance with settings: {post_processing_data}")

            # Create PostProcessingRecommendations object
            post_processing = PostProcessingRecommendations(
                exposure_adjustment=post_processing_data.get("exposure_adjustment", 0),
                contrast_adjustment=post_processing_data.get("contrast_adjustment", 0),
                saturation_adjustment=post_processing_data.get("saturation_adjustment", 0),
                vibrance_adjustment=post_processing_data.get("vibrance_adjustment", 0),
                sharpness_adjustment=post_processing_data.get("sharpness_adjustment", 0),
                noise_reduction=post_processing_data.get("noise_reduction", 0),
                highlights_adjustment=post_processing_data.get("highlights_adjustment"),
                shadows_adjustment=post_processing_data.get("shadows_adjustment"),
                whites_adjustment=post_processing_data.get("whites_adjustment"),
                blacks_adjustment=post_processing_data.get("blacks_adjustment"),
                temperature_adjustment=post_processing_data.get("temperature_adjustment"),
                tint_adjustment=post_processing_data.get("tint_adjustment"),
                can_auto_fix=post_processing_data.get("can_auto_fix", False)
            )

            # Enhance and save the image
            enhancement_service = ImageEnhancementService()
            enhancement_service.enhance_image(original_path, post_processing, enhanced_path)
            logger.info(f"Enhanced image saved locally to: {enhanced_path}")

        # Upload to Supabase Storage
        storage_path = f"user-{user_id}/{enhanced_filename}"

        try:
            # Read the enhanced file
            with open(enhanced_path, 'rb') as file:
                file_bytes = file.read()

            # Upload to Supabase Storage bucket
            logger.info(f"☁️ Uploading to Supabase Storage: {storage_path}")
            upload_response = supabase_client.storage.from_("enhanced-images").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )

            # Get public URL
            public_url = supabase_client.storage.from_("enhanced-images").get_public_url(storage_path)
            logger.info(f"✅ Uploaded to Supabase Storage. Public URL: {public_url}")

            # Clean up local file (optional - saves disk space)
            try:
                os.remove(enhanced_path)
                logger.info(f"🗑️ Cleaned up local file: {enhanced_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup local file: {cleanup_error}")

        except Exception as storage_error:
            logger.error(f"Failed to upload to Supabase Storage: {storage_error}")
            # Fallback to local storage if Supabase upload fails
            public_url = f"/uploads/enhanced/{enhanced_filename}"
            storage_path = f"enhanced/{enhanced_filename}"
            logger.warning(f"⚠️ Using local storage fallback: {public_url}")

        # Create the database record
        enhanced_data = {
            "user_id": user_id,
            "original_image_id": str(request.original_image_id),
            "team_id": str(request.team_id) if request.team_id else None,
            "player_id": str(request.player_id) if request.player_id else None,
            "enhanced_url": public_url,
            "enhanced_storage_path": storage_path,
            "thumbnail_url": image_data.get("thumbnail_url"),
            "enhancement_settings": post_processing_data,
            "player_name_override": request.player_name_override,
            "jersey_number_override": request.jersey_number_override,
            "title": request.title,
            "description": request.description,
            "tags": request.tags
        }

        logger.info(f"💾 Database record - enhanced_url: {public_url}, storage_path: {storage_path}")

        response = supabase_client.table("enhanced_images").insert(enhanced_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save enhanced image record"
            )

        # Mark original image as saved to library
        supabase_client.table("images").update({"is_saved_to_library": True}).eq("id", str(request.original_image_id)).execute()

        logger.info(f"Enhanced image saved to library: {response.data[0]['id']} by user {user_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving enhanced image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save enhanced image: {str(e)}"
        )


@router.get("/", response_model=List[EnhancedImageResponse])
async def list_enhanced_images(
    current_user: dict = Depends(get_current_user),
    team_id: Optional[UUID] = None,
    player_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's enhanced images library with optional filters
    """
    try:
        user_id = current_user["id"]

        # Build query
        query = supabase_client.table("enhanced_images").select("*").eq("user_id", user_id)

        if team_id:
            query = query.eq("team_id", str(team_id))

        if player_id:
            query = query.eq("player_id", str(player_id))

        query = query.order("created_at", desc=True).limit(limit).offset(offset)

        response = query.execute()

        return response.data

    except Exception as e:
        logger.error(f"Error listing enhanced images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list enhanced images: {str(e)}"
        )


@router.patch("/{image_id}/player-override", response_model=EnhancedImageResponse)
async def update_player_override(
    image_id: UUID,
    request: UpdatePlayerOverrideRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update player name/jersey number override (manual correction)
    """
    try:
        user_id = current_user["id"]

        # Verify ownership
        image = supabase_client.table("enhanced_images").select("user_id").eq("id", str(image_id)).execute()

        if not image.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enhanced image not found"
            )

        if image.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this image"
            )

        # Update override fields
        update_data = {}
        if request.player_name is not None:
            update_data["player_name_override"] = request.player_name
        if request.jersey_number is not None:
            update_data["jersey_number_override"] = request.jersey_number

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        response = supabase_client.table("enhanced_images").update(update_data).eq("id", str(image_id)).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update player override"
            )

        logger.info(f"Player override updated for enhanced image {image_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player override: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update player override: {str(e)}"
        )


@router.patch("/{image_id}/increment-download")
async def increment_download_count(
    image_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Increment download count when user downloads an image
    """
    try:
        user_id = current_user["id"]

        # Verify ownership
        image = supabase_client.table("enhanced_images").select("user_id, download_count").eq("id", str(image_id)).execute()

        if not image.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enhanced image not found"
            )

        if image.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this image"
            )

        # Increment download count
        current_count = image.data[0].get("download_count", 0)
        supabase_client.table("enhanced_images").update({
            "download_count": current_count + 1,
            "last_downloaded_at": datetime.now().isoformat()
        }).eq("id", str(image_id)).execute()

        return {"success": True, "download_count": current_count + 1}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error incrementing download count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increment download count: {str(e)}"
        )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enhanced_image(
    image_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an enhanced image from the library
    """
    try:
        user_id = current_user["id"]

        # Verify ownership
        image = supabase_client.table("enhanced_images").select("user_id, original_image_id").eq("id", str(image_id)).execute()

        if not image.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enhanced image not found"
            )

        if image.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this image"
            )

        original_image_id = image.data[0]["original_image_id"]

        # Delete enhanced image
        supabase_client.table("enhanced_images").delete().eq("id", str(image_id)).execute()

        # Check if there are any other enhanced versions of this original image
        remaining = supabase_client.table("enhanced_images").select("id").eq("original_image_id", original_image_id).execute()

        # If no more enhanced versions, mark original as not saved
        if not remaining.data:
            supabase_client.table("images").update({"is_saved_to_library": False}).eq("id", original_image_id).execute()

        logger.info(f"Enhanced image deleted from library: {image_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting enhanced image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete enhanced image: {str(e)}"
        )
