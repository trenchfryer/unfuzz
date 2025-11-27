"""
Batch Enhancement Service using Redis Queue for background processing.
Handles batch enhancement jobs with real-time progress tracking via WebSocket.
"""
import logging
import os
import glob
from typing import List, Dict, Any
from redis import Redis
from rq import Queue, get_current_job
from rq.job import Job
import time

from app.core.config import settings
from app.services.image_enhancement import ImageEnhancementService
from app.models.enhancement_preset import (
    get_preset,
    apply_preset_to_recommendations,
    PresetName
)
from app.models.image import PostProcessingRecommendations

logger = logging.getLogger(__name__)

# Initialize Redis connection and queue
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0))
)
enhancement_queue = Queue('enhancement', connection=redis_conn)


def enhance_single_image(
    image_id: str,
    preset_name: PresetName,
    job_id: str,
    current_index: int,
    total_images: int
) -> Dict[str, Any]:
    """
    Enhance a single image (worker function for RQ).

    This function runs in the background worker process.

    Args:
        image_id: UUID of the image to enhance
        preset_name: Name of the enhancement preset
        job_id: Job ID for progress tracking
        current_index: Current image index (0-based)
        total_images: Total number of images in batch

    Returns:
        Dict with enhancement results
    """
    try:
        logger.info(f"[Job {job_id}] Enhancing image {current_index + 1}/{total_images}: {image_id}")

        # Find image file
        image_pattern = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")
        matches = glob.glob(image_pattern)

        if not matches:
            logger.error(f"Image not found: {image_id}")
            return {
                "image_id": image_id,
                "status": "failed",
                "error": "Image file not found"
            }

        image_path = matches[0]

        # Get preset configuration
        preset = get_preset(preset_name)

        # TODO: Load actual AI recommendations from database/storage
        # For now, using default recommendations
        base_recommendations = PostProcessingRecommendations(
            exposure_adjustment=0.3,
            contrast_adjustment=8,
            saturation_adjustment=5,
            sharpness_adjustment=10,
            can_auto_fix=True
        )

        # Apply preset modifiers to base recommendations
        final_recommendations = apply_preset_to_recommendations(
            base_recommendations,
            preset
        )

        # Enhance image with preset settings
        enhancement_service = ImageEnhancementService()
        enhanced_bytes = enhancement_service.enhance_image(
            image_path,
            final_recommendations,
            aspect_ratio=preset.aspect_ratio,
            quality=preset.quality
        )

        # Save enhanced image
        enhanced_filename = f"{image_id}_enhanced_{preset_name}.jpg"
        enhanced_path = os.path.join(settings.UPLOAD_FOLDER, "enhanced", enhanced_filename)

        # Create enhanced directory if it doesn't exist
        os.makedirs(os.path.dirname(enhanced_path), exist_ok=True)

        # Write enhanced image
        with open(enhanced_path, 'wb') as f:
            f.write(enhanced_bytes)

        logger.info(f"[Job {job_id}] Enhanced image saved: {enhanced_path}")

        return {
            "image_id": image_id,
            "status": "success",
            "enhanced_path": enhanced_path,
            "enhanced_filename": enhanced_filename,
            "preset": preset_name,
            "size_bytes": len(enhanced_bytes)
        }

    except Exception as e:
        logger.error(f"[Job {job_id}] Error enhancing image {image_id}: {e}", exc_info=True)
        return {
            "image_id": image_id,
            "status": "failed",
            "error": str(e)
        }


def batch_enhance_images(
    image_ids: List[str],
    preset_name: PresetName,
    user_id: str
) -> Dict[str, Any]:
    """
    Batch enhance multiple images (main worker function for RQ).

    This function processes all images sequentially and updates job metadata
    for progress tracking.

    Args:
        image_ids: List of image UUIDs to enhance
        preset_name: Name of the enhancement preset
        user_id: User ID (for authorization)

    Returns:
        Dict with batch enhancement results
    """
    job = get_current_job()
    job_id = job.id if job else 'unknown'

    logger.info(f"[Job {job_id}] Starting batch enhancement: {len(image_ids)} images with preset '{preset_name}'")

    results = []
    total_images = len(image_ids)
    successful = 0
    failed = 0

    start_time = time.time()

    for index, image_id in enumerate(image_ids):
        # Update job metadata for progress tracking
        if job:
            job.meta['status'] = 'processing'
            job.meta['current'] = index + 1
            job.meta['total'] = total_images
            job.meta['message'] = f"Enhancing image {index + 1} of {total_images}..."
            job.save_meta()

        # Enhance single image
        result = enhance_single_image(
            image_id,
            preset_name,
            job_id,
            index,
            total_images
        )

        results.append(result)

        if result['status'] == 'success':
            successful += 1
        else:
            failed += 1

        # Small delay to avoid overwhelming the system
        time.sleep(0.1)

    end_time = time.time()
    duration = end_time - start_time

    # Final job metadata update
    if job:
        job.meta['status'] = 'completed'
        job.meta['current'] = total_images
        job.meta['total'] = total_images
        job.meta['message'] = f"Completed! {successful} successful, {failed} failed"
        job.meta['duration_seconds'] = duration
        job.save_meta()

    logger.info(
        f"[Job {job_id}] Batch enhancement completed: "
        f"{successful} successful, {failed} failed in {duration:.2f}s"
    )

    return {
        "job_id": job_id,
        "status": "completed",
        "total_images": total_images,
        "successful": successful,
        "failed": failed,
        "duration_seconds": duration,
        "results": results
    }


class BatchEnhancementService:
    """Service for managing batch enhancement jobs."""

    def __init__(self):
        self.queue = enhancement_queue
        self.redis = redis_conn

    def enqueue_batch_job(
        self,
        image_ids: List[str],
        preset_name: PresetName,
        user_id: str
    ) -> str:
        """
        Enqueue a batch enhancement job.

        Args:
            image_ids: List of image UUIDs to enhance
            preset_name: Name of the enhancement preset
            user_id: User ID (for authorization)

        Returns:
            Job ID for tracking
        """
        # Enqueue the job
        job = self.queue.enqueue(
            batch_enhance_images,
            image_ids,
            preset_name,
            user_id,
            job_timeout='10m',  # 10 minute timeout
            result_ttl=3600,  # Keep results for 1 hour
            failure_ttl=3600  # Keep failures for 1 hour
        )

        # Initialize job metadata for progress tracking
        job.meta['status'] = 'queued'
        job.meta['current'] = 0
        job.meta['total'] = len(image_ids)
        job.meta['message'] = f"Queued {len(image_ids)} images for enhancement"
        job.meta['preset'] = preset_name
        job.meta['user_id'] = user_id
        job.save_meta()

        logger.info(f"Enqueued batch enhancement job: {job.id} ({len(image_ids)} images)")

        return job.id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the current status of a batch enhancement job.

        Args:
            job_id: Job ID to query

        Returns:
            Dict with job status information
        """
        try:
            job = Job.fetch(job_id, connection=self.redis)

            status = job.get_status()
            meta = job.meta or {}

            return {
                "job_id": job_id,
                "status": status,  # queued, started, finished, failed
                "current": meta.get('current', 0),
                "total": meta.get('total', 0),
                "message": meta.get('message', ''),
                "preset": meta.get('preset'),
                "user_id": meta.get('user_id'),
                "result": job.result if status == 'finished' else None,
                "error": job.exc_info if status == 'failed' else None
            }

        except Exception as e:
            logger.error(f"Error fetching job status for {job_id}: {e}")
            return {
                "job_id": job_id,
                "status": "unknown",
                "error": str(e)
            }

    def get_enhanced_images(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get list of enhanced images from a completed job.

        Args:
            job_id: Job ID to query

        Returns:
            List of enhanced image metadata
        """
        try:
            job = Job.fetch(job_id, connection=self.redis)

            if job.get_status() != 'finished':
                return []

            result = job.result
            if not result or 'results' not in result:
                return []

            # Filter to only successful enhancements
            enhanced_images = [
                r for r in result['results']
                if r['status'] == 'success'
            ]

            return enhanced_images

        except Exception as e:
            logger.error(f"Error fetching enhanced images for {job_id}: {e}")
            return []
