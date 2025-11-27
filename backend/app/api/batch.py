"""
API endpoints for batch operations (enhancement, downloads).
"""
import logging
import os
import asyncio
import json
from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from stream_zip import stream_zip, ZIP_64
from datetime import datetime, timedelta

from app.models.enhancement_preset import (
    BatchEnhancementRequest,
    BatchEnhancementResponse,
    ENHANCEMENT_PRESETS
)
from app.services.batch_enhancement import BatchEnhancementService
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
batch_service = BatchEnhancementService()


@router.post("/enhancement", response_model=BatchEnhancementResponse)
async def start_batch_enhancement(request: BatchEnhancementRequest):
    """
    Start a batch enhancement job.

    This endpoint queues images for background processing and returns immediately
    with a job ID that can be used to track progress via WebSocket or polling.

    Args:
        request: BatchEnhancementRequest with image_ids, preset, and user_id

    Returns:
        BatchEnhancementResponse with job_id and status
    """
    try:
        # Validate image count
        if len(request.image_ids) == 0:
            raise HTTPException(status_code=400, detail="No images provided")

        if len(request.image_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 images per batch. Please split into multiple batches."
            )

        # Enqueue the batch job
        job_id = batch_service.enqueue_batch_job(
            image_ids=request.image_ids,
            preset_name=request.preset,
            user_id=request.user_id
        )

        logger.info(
            f"Batch enhancement job started: {job_id} "
            f"({len(request.image_ids)} images, preset: {request.preset})"
        )

        return BatchEnhancementResponse(
            job_id=job_id,
            status="queued",
            total_images=len(request.image_ids),
            message=f"Batch enhancement job queued successfully with {len(request.image_ids)} images"
        )

    except Exception as e:
        logger.error(f"Error starting batch enhancement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enhancement/{job_id}/status")
async def get_batch_status(job_id: str):
    """
    Get the current status of a batch enhancement job.

    Use this endpoint for polling-based progress tracking (not recommended,
    prefer WebSocket for real-time updates).

    Args:
        job_id: Job ID from start_batch_enhancement

    Returns:
        Job status including progress information
    """
    try:
        status = batch_service.get_job_status(job_id)

        if status['status'] == 'unknown':
            raise HTTPException(status_code=404, detail="Job not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enhancement/{job_id}/download")
async def download_batch_zip(job_id: str):
    """
    Download all enhanced images from a completed batch job as a ZIP file.

    Uses stream-zip for memory-efficient ZIP generation that can handle
    100+ high-resolution images without running out of memory.

    Args:
        job_id: Job ID from start_batch_enhancement

    Returns:
        StreamingResponse with ZIP file
    """
    try:
        # Get job status to verify it's completed
        status = batch_service.get_job_status(job_id)

        if status['status'] == 'unknown':
            raise HTTPException(status_code=404, detail="Job not found")

        if status['status'] != 'finished':
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed yet. Current status: {status['status']}"
            )

        # Get list of enhanced images
        enhanced_images = batch_service.get_enhanced_images(job_id)

        if not enhanced_images:
            raise HTTPException(
                status_code=404,
                detail="No enhanced images found for this job"
            )

        logger.info(f"Generating ZIP for job {job_id} with {len(enhanced_images)} images")

        # Generator function for stream-zip
        def file_generator():
            """Generator that yields file data for streaming ZIP creation."""
            for img in enhanced_images:
                enhanced_path = img['enhanced_path']

                if not os.path.exists(enhanced_path):
                    logger.warning(f"Enhanced image not found: {enhanced_path}")
                    continue

                # Get file stats
                stat_result = os.stat(enhanced_path)
                modified_at = datetime.fromtimestamp(stat_result.st_mtime)

                # Read file in chunks
                def read_file():
                    with open(enhanced_path, 'rb') as f:
                        while chunk := f.read(65536):  # 64KB chunks
                            yield chunk

                # Yield tuple for stream-zip
                # (filename, modified_at, file_mode, ZIP_64, file_data_generator)
                yield (
                    img['enhanced_filename'],  # Filename in ZIP
                    modified_at,  # Modification time
                    0o644,  # File permissions
                    ZIP_64,  # Use ZIP64 format for large files
                    read_file()  # Generator for file data
                )

        # Generate ZIP filename
        preset_name = status.get('preset', 'enhanced')
        zip_filename = f"unfuzz_batch_{job_id[:8]}_{preset_name}.zip"

        # Create streaming ZIP
        zipped_chunks = stream_zip(file_generator())

        # Return as streaming response
        return StreamingResponse(
            zipped_chunks,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating ZIP for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_available_presets():
    """
    Get list of available enhancement presets.

    Returns information about all preset configurations including
    their display names, descriptions, and settings.

    Returns:
        Dict of preset configurations
    """
    return {
        "presets": [
            {
                "name": preset.name,
                "display_name": preset.display_name,
                "description": preset.description,
                "aspect_ratio": preset.aspect_ratio,
                "quality": preset.quality
            }
            for preset in ENHANCEMENT_PRESETS.values()
        ]
    }


@router.websocket("/ws/enhancement/{job_id}")
async def websocket_enhancement_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time batch enhancement progress tracking.

    Connects to a running batch enhancement job and sends progress updates
    in real-time as images are processed.

    Args:
        websocket: WebSocket connection
        job_id: Job ID to track

    WebSocket Message Format:
        {
            "job_id": "abc123",
            "status": "processing",  // queued, started, processing, finished, failed
            "current": 12,
            "total": 52,
            "message": "Enhancing image 12 of 52...",
            "percent": 23.0
        }
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for job: {job_id}")

    try:
        last_current = 0
        consecutive_same = 0

        while True:
            # Fetch current job status
            status = batch_service.get_job_status(job_id)

            if status['status'] == 'unknown':
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "error",
                    "message": "Job not found"
                })
                await websocket.close(code=1008, reason="Job not found")
                break

            # Calculate progress percentage
            current = status.get('current', 0)
            total = status.get('total', 0)
            percent = (current / total * 100) if total > 0 else 0

            # Prepare progress message
            progress_data = {
                "job_id": job_id,
                "status": status['status'],
                "current": current,
                "total": total,
                "message": status.get('message', ''),
                "percent": round(percent, 1)
            }

            # Send progress update
            await websocket.send_json(progress_data)

            # Check if job is finished or failed
            if status['status'] in ['finished', 'failed']:
                logger.info(f"Job {job_id} completed with status: {status['status']}")

                # Send final message with results
                if status['status'] == 'finished':
                    result = status.get('result', {})
                    progress_data['successful'] = result.get('successful', 0)
                    progress_data['failed'] = result.get('failed', 0)
                    progress_data['duration_seconds'] = result.get('duration_seconds', 0)
                    await websocket.send_json(progress_data)

                # Close connection
                await asyncio.sleep(0.5)  # Give client time to receive final message
                await websocket.close(code=1000, reason="Job completed")
                break

            # Detect if job is stuck
            if current == last_current:
                consecutive_same += 1
                if consecutive_same > 60:  # 60 seconds without progress
                    logger.warning(f"Job {job_id} appears stuck at {current}/{total}")
                    await websocket.send_json({
                        "job_id": job_id,
                        "status": "warning",
                        "message": "Job may be stuck. Please check logs."
                    })
                    consecutive_same = 0
            else:
                consecutive_same = 0
                last_current = current

            # Wait before next update (poll every 1 second)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job: {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "job_id": job_id,
                "status": "error",
                "message": str(e)
            })
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass


@router.post("/enhancement/{job_id}/save-to-library")
async def save_batch_to_library(job_id: str, current_user: dict = Depends(get_current_user)):
    """
    Save all enhanced images from a completed batch job to the library.

    This endpoint:
    1. Verifies the batch job is completed
    2. Gets the list of successfully enhanced images
    3. Creates library entries for each enhanced image

    Args:
        job_id: The batch job ID
        current_user: Authenticated user from dependency injection

    Returns:
        Dict with count of saved images
    """
    try:
        from app.core.supabase import supabase_client
        from app.core.config import settings
        from uuid import UUID
        import os

        user_id = current_user["id"]

        # Get job status
        status = batch_service.get_job_status(job_id)

        if status['status'] == 'unknown':
            raise HTTPException(status_code=404, detail="Job not found")

        if status['status'] != 'finished':
            raise HTTPException(
                status_code=400,
                detail=f"Job must be finished before saving to library. Current status: {status['status']}"
            )

        # Get enhanced images from job
        enhanced_images = batch_service.get_enhanced_images(job_id)

        if not enhanced_images:
            raise HTTPException(
                status_code=404,
                detail="No enhanced images found for this job"
            )

        logger.info(f"Saving {len(enhanced_images)} enhanced images to library from job {job_id}")

        saved_count = 0
        failed_count = 0

        for img in enhanced_images:
            try:
                # Extract image ID from filename or path
                image_id = img['image_id']
                enhanced_path = img['enhanced_path']
                enhanced_filename = img['enhanced_filename']

                # Fetch original image to get player metadata
                original_img_result = supabase_client.table("images").select(
                    "team_id, player_id, player_name_override, jersey_number_override, is_group_photo, player_names, detected_jersey_numbers"
                ).eq("id", image_id).execute()

                original_img = original_img_result.data[0] if original_img_result.data else {}

                # Create library entry in database with player metadata copied from original
                library_entry = {
                    "user_id": user_id,
                    "original_image_id": image_id,
                    "team_id": original_img.get("team_id"),
                    "player_id": original_img.get("player_id"),
                    "enhanced_url": f"/uploads/enhanced/{enhanced_filename}",
                    "enhanced_storage_path": enhanced_path,
                    "thumbnail_url": None,  # Can generate later if needed
                    "download_count": 0,
                    "player_name_override": original_img.get("player_name_override"),
                    "jersey_number_override": original_img.get("jersey_number_override"),
                    "title": None,
                    "description": f"Batch enhanced image (job: {job_id[:8]})",
                    "tags": ["batch_enhanced"],
                }

                # Save to database
                result = supabase_client.table("enhanced_images").insert(library_entry).execute()

                if result.data:
                    saved_count += 1
                    logger.info(f"✅ Saved {enhanced_filename} to library")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Failed to save {enhanced_filename} to library")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error saving image {img.get('image_id')} to library: {e}")

        logger.info(
            f"Batch save completed for job {job_id}: "
            f"{saved_count} saved, {failed_count} failed"
        )

        return {
            "job_id": job_id,
            "saved_count": saved_count,
            "failed_count": failed_count,
            "total_images": len(enhanced_images)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving batch to library for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
