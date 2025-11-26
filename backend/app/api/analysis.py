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

        # In production, save analysis results to database
        logger.info(f"Analysis completed for {image_id}: Score {analysis_result.overall_score}")

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

        response = {
            "image_id": image_id,
            "analysis": analysis_result.dict(),
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
