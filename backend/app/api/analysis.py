from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from app.models.image import ImageAnalysisResponse
from app.services.openai_vision import OpenAIVisionService
from app.services.duplicate_detector import DuplicateDetector
from app.utils.image_processing import ImageProcessor
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
vision_service = OpenAIVisionService()
duplicate_detector = DuplicateDetector()


@router.post("/analyze/{image_id}")
async def analyze_single_image(image_id: str):
    """
    Analyze a single image using OpenAI Vision API.

    Returns complete analysis with all 30+ factor scores.
    """
    try:
        # In production, fetch image details from database
        # For now, construct path based on ID
        image_path = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")

        # Find matching file
        import glob
        matches = glob.glob(image_path)

        if not matches:
            raise HTTPException(
                status_code=404,
                detail=f"Image not found: {image_id}"
            )

        image_path = matches[0]

        # Extract EXIF for context
        exif_data = ImageProcessor.extract_exif_data(image_path)

        # Analyze image
        logger.info(f"Starting analysis for image: {image_id}")
        analysis_result = await vision_service.analyze_image(
            image_path=image_path,
            exif_data=exif_data
        )

        # Compute hashes for duplicate detection
        dhash, phash = duplicate_detector.compute_hashes(image_path)

        # In production, save analysis results to database
        logger.info(f"Analysis completed for {image_id}: Score {analysis_result.overall_score}")

        return {
            "image_id": image_id,
            "analysis": analysis_result.dict(),
            "dhash": dhash,
            "phash": phash,
            "status": "completed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-batch")
async def analyze_batch_images(
    image_ids: List[str],
    background_tasks: BackgroundTasks
):
    """
    Analyze multiple images in batch.

    Processes images sequentially and returns results.
    For large batches, consider using background job queue.
    """
    try:
        results = []

        for image_id in image_ids:
            try:
                result = await analyze_single_image(image_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {image_id}: {e}")
                results.append({
                    "image_id": image_id,
                    "status": "failed",
                    "error": str(e)
                })

        return {
            "total": len(image_ids),
            "completed": len([r for r in results if r.get("status") == "completed"]),
            "failed": len([r for r in results if r.get("status") == "failed"]),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in batch analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-duplicates")
async def detect_duplicates(project_id: str):
    """
    Detect duplicate and similar images in a project.

    Groups similar images and identifies burst sequences.
    """
    try:
        # In production, fetch all images for project from database
        # For now, return mock response

        # Example of how to use duplicate detector:
        # image_data = [
        #     {"id": "1", "dhash": "...", "phash": "...", "capture_time": ...},
        #     ...
        # ]
        # duplicate_groups = duplicate_detector.find_duplicate_groups(image_data)
        # burst_sequences = duplicate_detector.find_burst_sequences(image_data)

        return {
            "project_id": project_id,
            "duplicate_groups": [],
            "burst_sequences": [],
            "message": "Duplicate detection completed"
        }

    except Exception as e:
        logger.error(f"Error detecting duplicates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-select/{project_id}")
async def smart_select(
    project_id: str,
    selection_threshold: float = 75.0,
    auto_reject_closed_eyes: bool = True
):
    """
    Automatically select best images from a project.

    Uses AI scores, duplicate detection, and user preferences to
    select the top images automatically.

    Args:
        project_id: Project to select from
        selection_threshold: Minimum score for auto-selection (0-100)
        auto_reject_closed_eyes: Automatically reject images with closed eyes
    """
    try:
        # In production:
        # 1. Fetch all analyzed images for project
        # 2. Apply rejection rules (closed eyes, critical defects)
        # 3. Remove duplicates (keep best from each group)
        # 4. Sort by overall_score
        # 5. Select images above threshold
        # 6. Update database with selections

        return {
            "project_id": project_id,
            "total_images": 0,
            "selected_count": 0,
            "rejected_count": 0,
            "duplicate_groups_processed": 0,
            "message": "Smart selection completed"
        }

    except Exception as e:
        logger.error(f"Error in smart selection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{image_id}")
async def get_analysis_status(image_id: str):
    """
    Check analysis status for an image.

    Returns current status (pending, analyzing, completed, failed)
    and progress information if available.
    """
    # TODO: Implement status lookup from database or job queue
    return {
        "image_id": image_id,
        "status": "pending",
        "progress": 0,
        "estimated_time_remaining": None
    }
