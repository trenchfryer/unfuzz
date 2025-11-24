"""
API endpoints for image enhancement and post-processing.
"""
import logging
import os
import glob
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import io

from app.services.image_enhancement import ImageEnhancementService
from app.models.image import PostProcessingRecommendations
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
enhancement_service = ImageEnhancementService()


@router.get("/preview/{image_id}")
async def generate_preview(image_id: str):
    """
    Generate a preview of the enhanced image based on post-processing recommendations.
    Returns a reduced-resolution preview for quick display in the UI.

    NOTE: This is a simplified version that creates test recommendations.
    In production, this would load actual analysis results from storage.
    """
    try:
        # Find image file
        image_pattern = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")
        matches = glob.glob(image_pattern)

        if not matches:
            raise HTTPException(status_code=404, detail="Image not found")

        image_path = matches[0]

        # For now, create test recommendations
        # In production, load these from analysis results stored with the image
        recommendations = PostProcessingRecommendations(
            exposure_adjustment=0.5,
            contrast_adjustment=10,
            saturation_adjustment=5,
            can_auto_fix=True
        )

        logger.info(f"Generating preview for image {image_id}")

        # Generate preview
        preview_bytes = enhancement_service.create_preview(
            image_path,
            recommendations,
            max_size=1200
        )

        # Return as image response
        return Response(
            content=preview_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename=preview_{image_id}.jpg"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview for {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enhance/{image_id}")
async def enhance_image(image_id: str):
    """
    Apply full-resolution enhancement to an image and return the enhanced version.
    This is the final enhanced image ready for download or saving to Google Drive.

    NOTE: This is a simplified version that creates test recommendations.
    In production, this would load actual analysis results from storage.
    """
    try:
        # Find image file
        image_pattern = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")
        matches = glob.glob(image_pattern)

        if not matches:
            raise HTTPException(status_code=404, detail="Image not found")

        image_path = matches[0]

        # For now, create test recommendations
        # In production, load these from analysis results stored with the image
        recommendations = PostProcessingRecommendations(
            exposure_adjustment=0.5,
            contrast_adjustment=10,
            saturation_adjustment=5,
            sharpness_adjustment=20,
            can_auto_fix=True
        )

        logger.info(f"Enhancing full-resolution image {image_id}")

        # Generate enhanced image
        enhanced_bytes = enhancement_service.enhance_image(
            image_path,
            recommendations
        )

        # Get original filename
        original_filename = image_doc.get("filename", "image.jpg")
        name_parts = original_filename.rsplit(".", 1)
        enhanced_filename = f"{name_parts[0]}_enhanced.jpg"

        # Return as downloadable image
        return Response(
            content=enhanced_bytes,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f'attachment; filename="{enhanced_filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enhancing image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{image_id}/can-enhance")
async def check_can_enhance(image_id: str):
    """
    Check if an image can be enhanced (has post-processing recommendations).
    Returns information about whether enhancement is available and recommended.

    NOTE: This is a simplified version. In production, this would check
    actual analysis results stored with the image.
    """
    try:
        # Find image file
        image_pattern = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")
        matches = glob.glob(image_pattern)

        if not matches:
            raise HTTPException(status_code=404, detail="Image not found")

        # For now, always return that enhancement is available
        # In production, load actual analysis results
        return {
            "can_enhance": True,
            "recommended": True,
            "post_processing": {
                "exposure_adjustment": 0.5,
                "contrast_adjustment": 10,
                "saturation_adjustment": 5,
                "can_auto_fix": True
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking enhancement status for {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
