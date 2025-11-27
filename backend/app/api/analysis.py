from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from app.models.image import ImageAnalysisResponse
from app.services.openai_vision import OpenAIVisionService
from app.services.gemini_vision import GeminiVisionService
from app.services.duplicate_detector import DuplicateDetector
from app.utils.image_processing import ImageProcessor
from app.core.config import settings
from app.core.supabase import supabase_client
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services based on configuration
if settings.VISION_PROVIDER == "gemini":
    vision_service = GeminiVisionService()
    logger.info("Using Google Gemini for image analysis")
else:
    vision_service = OpenAIVisionService()
    logger.info("Using OpenAI GPT for image analysis")

duplicate_detector = DuplicateDetector()


@router.post("/analyze/{image_id}")
async def analyze_single_image(
    image_id: str,
    team_id: Optional[str] = Query(None, description="Team ID for jersey detection")
):
    """
    Analyze a single image using AI Vision API (OpenAI or Gemini).

    Returns complete analysis with all 30+ factor scores.
    If team_id is provided, enables jersey number detection.
    """
    try:
        # Fetch image details from database (including stored EXIF metadata)
        db_image = supabase_client.table("images").select("*").eq("id", image_id).execute()

        if not db_image.data or len(db_image.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Image not found in database: {image_id}"
            )

        image_record = db_image.data[0]

        # Construct file path from database record
        image_path = os.path.join(settings.UPLOAD_FOLDER, f"{image_id}_*")
        import glob
        matches = glob.glob(image_path)

        if not matches:
            raise HTTPException(
                status_code=404,
                detail=f"Image file not found: {image_id}"
            )

        image_path = matches[0]

        # Use EXIF data from database (stored during upload before WebP conversion)
        exif_data = image_record.get("exif_data", {}) or {}

        # If database has no EXIF, build from individual fields
        if not exif_data:
            exif_data = {
                "Make": image_record.get("camera_make"),
                "Model": image_record.get("camera_model"),
                "LensModel": image_record.get("lens_model"),
                "FocalLength": image_record.get("focal_length"),
                "FNumber": image_record.get("aperture"),
                "ExposureTime": image_record.get("shutter_speed"),
                "ISOSpeedRatings": image_record.get("iso"),
                "ISO": image_record.get("iso"),
                "DateTime": image_record.get("capture_time"),
            }

        if exif_data and any(exif_data.values()):
            logger.info(f"📸 Retrieved EXIF from database: Camera: {exif_data.get('Make')} {exif_data.get('Model')}, ISO: {exif_data.get('ISO') or exif_data.get('ISOSpeedRatings')}")
        else:
            logger.warning(f"⚠️ No EXIF data found in database for image: {image_id}")

        # Fetch team data if team_id provided
        team_mode = False
        player_roster = None
        team_logo_path = None
        team_colors = None

        if team_id:
            try:
                # Get team details
                team_response = supabase_client.table("teams").select("*").eq("id", team_id).execute()
                if team_response.data:
                    team = team_response.data[0]
                    team_mode = True

                    # Extract team colors (prefer home colors, fallback to legacy colors)
                    team_colors = {
                        "home": {
                            "primary": team.get("home_primary_color") or team.get("primary_color"),
                            "secondary": team.get("home_secondary_color") or team.get("secondary_color"),
                            "tertiary": team.get("home_tertiary_color")
                        },
                        "away": {
                            "primary": team.get("away_primary_color"),
                            "secondary": team.get("away_secondary_color"),
                            "tertiary": team.get("away_tertiary_color")
                        }
                    }

                    # Log team colors for debugging
                    if team_colors["home"]["primary"]:
                        logger.info(f"🎨 Team colors - Home: {team_colors['home']['primary']}, {team_colors['home']['secondary']}")
                    if team_colors["away"]["primary"]:
                        logger.info(f"🎨 Team colors - Away: {team_colors['away']['primary']}, {team_colors['away']['secondary']}")

                    # Get players for this team
                    players_response = supabase_client.table("players").select("*").eq("team_id", team_id).eq("is_active", True).execute()

                    if players_response.data:
                        # Format player data for AI prompt
                        player_roster = [
                            {
                                "id": p["id"],  # Include ID for database matching
                                "jersey_number": p["jersey_number"],
                                "name": f"{p['first_name']} {p['last_name']}",
                                "position": p.get("position"),
                                "grade_year": p.get("grade_year")
                            }
                            for p in players_response.data
                        ]
                        logger.info(f"Loaded {len(player_roster)} players for team {team_id}")

                    # Get team logo path if available
                    if team.get("logo_storage_path"):
                        # In production, download from Supabase storage
                        # For now, we'll skip the logo unless it's locally available
                        logger.info(f"Team has logo: {team['logo_storage_path']}")

            except Exception as e:
                logger.warning(f"Failed to fetch team data for {team_id}: {e}")
                # Continue without team mode if fetch fails

        # Analyze image
        logger.info(f"Starting analysis for image: {image_id} (team_mode={team_mode})")
        analysis_result = await vision_service.analyze_image(
            image_path=image_path,
            exif_data=exif_data,
            team_mode=team_mode,
            player_roster=player_roster,
            team_logo_path=team_logo_path,
            team_colors=team_colors
        )

        # Compute hashes for duplicate detection
        dhash, phash = duplicate_detector.compute_hashes(image_path)

        # Save analysis results to database
        logger.info(f"Analysis completed for {image_id}: Score {analysis_result.overall_score}")

        update_data = {
            "analysis_status": "completed",
            "analysis_completed_at": "now()",
            "overall_score": float(analysis_result.overall_score) if analysis_result.overall_score else None,
            "scores": analysis_result.factor_scores.dict() if analysis_result.factor_scores else None,
            "ai_summary": analysis_result.ai_summary,
            "detected_issues": analysis_result.detected_issues,
            "recommendations": analysis_result.recommendations,
            "critical_defects": analysis_result.critical_defects,
            "quality_tier": analysis_result.quality_tier,
            "phash": phash,
            "dhash": dhash,
            "faces_detected": analysis_result.subject_analysis.faces_detected if analysis_result.subject_analysis else None,
            "eyes_status": analysis_result.subject_analysis.eyes_status if analysis_result.subject_analysis else None,
            "has_people": analysis_result.subject_analysis.has_people if analysis_result.subject_analysis else False,
        }

        # Serialize camera_settings and post_processing to JSON-compatible dict
        camera_settings = getattr(analysis_result, 'camera_settings', None)
        post_processing = getattr(analysis_result, 'post_processing', None)

        if camera_settings:
            update_data["camera_settings"] = camera_settings.dict() if hasattr(camera_settings, 'dict') else camera_settings
        if post_processing:
            update_data["post_processing"] = post_processing.dict() if hasattr(post_processing, 'dict') else post_processing

        # Add team-specific fields if team mode was used
        if team_mode:
            update_data["team_mode_enabled"] = True
            update_data["team_id"] = team_id
            update_data["detected_jersey_number"] = getattr(analysis_result, 'jersey_number', None)
            update_data["player_confidence"] = float(analysis_result.jersey_confidence) if getattr(analysis_result, 'jersey_confidence', None) else None

            # Add group photo fields (gracefully handle missing attributes)
            update_data["is_group_photo"] = getattr(analysis_result, 'is_group_photo', False)
            update_data["player_names"] = getattr(analysis_result, 'player_names', None)
            update_data["detected_jersey_numbers"] = getattr(analysis_result, 'detected_jersey_numbers', None)

            # Match player from roster if single player photo (with error handling)
            try:
                if analysis_result.jersey_number and player_roster and not getattr(analysis_result, 'is_group_photo', False):
                    matching_player = next(
                        (p for p in player_roster if p.get("jersey_number") == analysis_result.jersey_number),
                        None
                    )
                    if matching_player and "id" in matching_player:
                        update_data["player_id"] = matching_player["id"]
                        logger.info(f"✅ Matched jersey #{analysis_result.jersey_number} to player ID: {matching_player['id']}")
                    elif analysis_result.jersey_number:
                        logger.warning(f"⚠️ No match found for jersey #{analysis_result.jersey_number} in roster (manual edit may be needed)")
            except Exception as player_match_error:
                logger.error(f"⚠️ Error matching player: {player_match_error} (continuing without player match)")
                # Continue without failing - user can manually edit later

        # Save to database
        try:
            result = supabase_client.table("images").update(update_data).eq("id", image_id).execute()
            if result.data:
                logger.info(f"💾 Saved analysis results to database for image {image_id} (phash: {phash[:16]}..., dhash: {dhash[:16]}...)")
            else:
                logger.warning(f"⚠️ Database update returned no data for image {image_id}")
        except Exception as db_error:
            logger.error(f"❌ Failed to save analysis to database: {db_error}")
            # Don't fail the request, just log the error

        # Format EXIF metadata for frontend display
        metadata = None
        if exif_data:
            metadata = {
                "camera_make": exif_data.get("Make"),
                "camera_model": exif_data.get("Model"),
                "lens_model": exif_data.get("LensModel"),
                "focal_length": exif_data.get("FocalLength"),
                "aperture": exif_data.get("FNumber"),
                "shutter_speed": exif_data.get("ExposureTime"),
                "iso": exif_data.get("ISOSpeedRatings") or exif_data.get("ISO"),
                "white_balance": exif_data.get("WhiteBalance"),
                "flash": exif_data.get("Flash"),
                "date_taken": exif_data.get("DateTime") or exif_data.get("DateTimeOriginal"),
            }
            logger.info(f"📦 Returning metadata to frontend: Camera={metadata.get('camera_make')} {metadata.get('camera_model')}, ISO={metadata.get('iso')}")
        else:
            logger.info(f"📦 No metadata to return for image {image_id}")

        # Safely convert analysis result to dict
        try:
            analysis_dict = analysis_result.dict()
        except Exception as e:
            logger.error(f"Failed to serialize analysis result with .dict(): {e}")
            # Fallback to manual serialization with correct attribute names
            analysis_dict = {
                "overall_score": getattr(analysis_result, 'overall_score', 0),
                "quality_tier": getattr(analysis_result, 'quality_tier', 'unknown'),
                "ai_summary": getattr(analysis_result, 'ai_summary', None),
                "factor_scores": getattr(analysis_result, 'factor_scores', {}),
                "detected_issues": getattr(analysis_result, 'detected_issues', []),
                "critical_defects": getattr(analysis_result, 'critical_defects', []),
                "is_reject": getattr(analysis_result, 'is_reject', False),
                "recommendations": getattr(analysis_result, 'recommendations', []),
                "subject_analysis": getattr(analysis_result, 'subject_analysis', {}),
                "camera_settings": getattr(analysis_result, 'camera_settings', None),
                "post_processing": getattr(analysis_result, 'post_processing', None),
            }

        response = {
            "image_id": image_id,
            "analysis": analysis_dict,
            "metadata": metadata,
            "dhash": dhash,
            "phash": phash,
            "status": "completed"
        }

        # Add jersey detection info if team mode was enabled
        if team_mode:
            response["team_id"] = team_id
            response["jersey_number"] = analysis_result.jersey_number
            response["jersey_confidence"] = analysis_result.jersey_confidence

            # Group photo detection
            response["is_group_photo"] = getattr(analysis_result, 'is_group_photo', False)
            response["detected_jersey_numbers"] = getattr(analysis_result, 'detected_jersey_numbers', [])
            response["player_names"] = getattr(analysis_result, 'player_names', [])

            # Debug logging for group photos
            if response["is_group_photo"]:
                logger.info(f"🔍 GROUP PHOTO response data:")
                logger.info(f"   - detected_jersey_numbers: {response['detected_jersey_numbers']}")
                logger.info(f"   - player_names: {response['player_names']}")

            # Look up player name from roster (for single player photos)
            if analysis_result.jersey_number and player_roster and not response["is_group_photo"]:
                logger.info(f"🔍 Attempting to match jersey number '{analysis_result.jersey_number}' (type: {type(analysis_result.jersey_number).__name__})")
                logger.info(f"🔍 Roster has {len(player_roster)} players with jersey numbers: {[p['jersey_number'] for p in player_roster]}")
                matching_player = next(
                    (p for p in player_roster if p["jersey_number"] == analysis_result.jersey_number),
                    None
                )
                if matching_player:
                    response["player_name"] = matching_player["name"]
                    logger.info(f"Matched jersey #{analysis_result.jersey_number} to player: {matching_player['name']}")
                else:
                    logger.warning(f"❌ No match found for jersey #{analysis_result.jersey_number} in roster")

            # Log group photo detection
            if response["is_group_photo"] and response["player_names"]:
                logger.info(f"Group photo detected with players: {', '.join(response['player_names'])}")

        return response

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
async def detect_duplicates(
    project_id: Optional[str] = Query(None, description="Optional project ID to limit detection"),
    user_id: Optional[str] = Query(None, description="Optional user ID to detect duplicates for all user images")
):
    """
    Detect duplicate and similar images using SQL-based exact hash matching.

    Groups images with identical perceptual hashes (exact duplicates).
    """
    try:
        # Use SQL query to find groups of images with identical hashes
        # This is much faster and more reliable than Python-based comparison

        logger.info("Detecting duplicates using SQL hash matching...")

        # Fetch all images with their hashes
        query = supabase_client.table("images").select("id, filename, phash, dhash, overall_score, capture_time")
        query = query.not_.is_("phash", "null").not_.is_("dhash", "null")

        if project_id:
            query = query.eq("project_id", project_id)

        result = query.execute()
        images = result.data

        if not images:
            return {
                "project_id": project_id,
                "duplicate_groups": [],
                "total_images": 0,
                "total_duplicates": 0,
                "message": "No images with hashes found"
            }

        logger.info(f"Found {len(images)} images with hashes")

        # Group images by their hash combination
        hash_groups = {}
        for img in images:
            hash_key = f"{img['phash']}|{img['dhash']}"
            if hash_key not in hash_groups:
                hash_groups[hash_key] = []
            hash_groups[hash_key].append(img)

        # Filter to only groups with more than 1 image (duplicates)
        duplicate_groups = []
        total_duplicates = 0

        import uuid
        for hash_key, group_images in hash_groups.items():
            if len(group_images) <= 1:
                continue  # Skip non-duplicates

            # Sort by overall_score (highest first), then by filename
            sorted_images = sorted(
                group_images,
                key=lambda x: (-(x.get('overall_score') or 0), x['filename'])
            )

            # Best image is the one with highest score
            best_image = sorted_images[0]
            group_id = str(uuid.uuid4())

            # Update database for all images in group
            for img in group_images:
                is_best = (img['id'] == best_image['id'])
                supabase_client.table("images").update({
                    "duplicate_group_id": group_id,
                    "is_duplicate": not is_best,
                }).eq("id", img['id']).execute()

            duplicate_groups.append({
                "group_id": group_id,
                "image_ids": [img['id'] for img in group_images],
                "best_image_id": best_image['id'],
                "count": len(group_images),
                "filenames": [img['filename'] for img in group_images],
            })

            total_duplicates += len(group_images)

        logger.info(f"✅ Found {len(duplicate_groups)} duplicate groups with {total_duplicates} total images")

        return {
            "project_id": project_id,
            "duplicate_groups": duplicate_groups,
            "total_images": len(images),
            "total_duplicates": total_duplicates,
            "total_groups": len(duplicate_groups),
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
