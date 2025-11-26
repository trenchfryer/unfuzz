import json
from typing import Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai
from PIL import Image
from app.core.config import settings
from app.models.image import (
    ImageAnalysisResult,
    ImageFactorScores,
    SubjectAnalysis,
    QualityTier,
    CameraSettingsRecommendations,
    PostProcessingRecommendations
)
import logging
import asyncio
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted

logger = logging.getLogger(__name__)


def serialize_exif(data: Any) -> Any:
    """
    Recursively convert datetime objects to strings for JSON serialization.
    """
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, dict):
        return {k: serialize_exif(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_exif(item) for item in data]
    else:
        return data


class GeminiVisionService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def _create_analysis_prompt(
        self,
        exif_data: Optional[Dict] = None,
        sequence_info: Optional[Dict] = None,
        team_mode: bool = False,
        player_roster: Optional[list[Dict]] = None,
        team_colors: Optional[Dict] = None
    ) -> str:
        """Create comprehensive analysis prompt for Gemini Vision API."""
        prompt = """
Analyze this photograph as a professional photography expert. Evaluate the image across these specific criteria and provide scores (0-100) for each:

TECHNICAL QUALITY (12 factors):
1. sharpness: Overall image sharpness and critical focus accuracy
2. exposure: Brightness balance, histogram quality, highlight/shadow management
3. color_accuracy: White balance correctness, color cast, natural saturation
4. noise_grain: ISO noise levels, digital artifacts
5. dynamic_range: Tonal range utilization, shadow/highlight detail preservation

COMPOSITION (8 factors):
6. rule_of_thirds: Subject placement on compositional power points
7. subject_placement: Main subject positioning effectiveness
8. framing: Edge management, aspect ratio optimization
9. leading_lines: Visual flow and eye guidance elements
10. balance: Visual weight distribution and harmony
11. depth: Foreground/midground/background separation quality
12. negative_space: Effective space utilization around subjects
13. perspective: Camera angle and distortion management

SUBJECT QUALITY (10 factors - if people present, otherwise score based on main subject):
14. facial_detection: Faces clearly visible and well-positioned (or main subject clarity)
15. eye_status: Eyes open/closed detection - CRITICAL FACTOR (score 0 if eyes closed/blinking)
16. facial_expression: Natural vs forced, emotional appropriateness
17. body_language: Pose naturalness and effectiveness
18. subject_attention: Engagement level and gaze direction
19. group_dynamics: Coordination among multiple subjects
20. motion_blur: Assess if blur is intentional vs accidental (lower score for accidental)
21. subject_lighting: Face/subject illumination quality
22. skin_tones: Natural color reproduction (or subject color accuracy)
23. subject_framing: Proper headroom, no awkward crops at joints

ARTISTIC QUALITY (5 factors):
24. lighting_quality: Light direction, character, and mood creation
25. color_harmony: Overall color palette cohesion
26. emotional_impact: Story-telling ability and mood conveyance
27. uniqueness: Creative differentiation and originality
28. professional_polish: Overall refinement and print-worthiness

CRITICAL ASSESSMENT:
- Flag any closed eyes or blinks as automatic rejection
- Identify severe blur, extreme exposure issues, or corruption
- Note if image appears to be duplicate/very similar to typical shots

CAMERA SETTINGS FEEDBACK (if EXIF data provided):
- Analyze ISO, aperture, shutter speed, and exposure settings from EXIF
- Provide SPECIFIC actionable recommendations for what settings to change in their camera
- Base recommendations on detected issues (e.g., high ISO causing noise, slow shutter causing motion blur)
- Include general shooting tips relevant to the scene and camera settings used

POST-PROCESSING RECOMMENDATIONS:
- Provide specific numeric adjustment values for automated enhancement
- Base adjustments on detected issues (e.g., underexposure, color casts, low contrast)
- Set can_auto_fix=true only if automated adjustments would significantly improve the image
- All adjustment values should be realistic and applicable in standard photo editing software"""

        # Add team/jersey detection section if team mode is enabled
        if team_mode and player_roster:
            # Build team color context string
            color_context = ""
            if team_colors:
                home_colors = []
                away_colors = []

                if team_colors.get("home", {}).get("primary"):
                    home_colors.append(f"Primary: {team_colors['home']['primary']}")
                if team_colors.get("home", {}).get("secondary"):
                    home_colors.append(f"Secondary: {team_colors['home']['secondary']}")
                if team_colors.get("home", {}).get("tertiary"):
                    home_colors.append(f"Tertiary: {team_colors['home']['tertiary']}")

                if team_colors.get("away", {}).get("primary"):
                    away_colors.append(f"Primary: {team_colors['away']['primary']}")
                if team_colors.get("away", {}).get("secondary"):
                    away_colors.append(f"Secondary: {team_colors['away']['secondary']}")
                if team_colors.get("away", {}).get("tertiary"):
                    away_colors.append(f"Tertiary: {team_colors['away']['tertiary']}")

                if home_colors:
                    color_context += f"\nHome Jersey Colors: {', '.join(home_colors)}"
                if away_colors:
                    color_context += f"\nAway Jersey Colors: {', '.join(away_colors)}"

            prompt += f"""

TEAM MODE - PLAYER AND JERSEY DETECTION:
This image is being analyzed in TEAM MODE for player identification.

Player Roster:
{json.dumps(player_roster, indent=2)}
{color_context}

CRITICAL PLAYER DETECTION INSTRUCTIONS:
- FOCUS ON IDENTIFYING ALL PLAYERS IN THE TEAM'S COLORS (as specified above)
- DO NOT identify players wearing opposing team colors/jerseys
- The team we're tracking wears the colors specified above
- Opposing players (in different colored jerseys) should be IGNORED
- Look for jersey numbers on the front, back, or sides of uniforms
- Examine ALL visible jersey numbers but ONLY report numbers for players in OUR team's colors
- Report ALL detected jersey numbers with confidence level (0.0 to 1.0)
- Consider image quality when assessing confidence (blurry numbers = lower confidence)

GROUP PHOTO DETECTION:
- Determine if this is a single player photo or a GROUP photo with multiple team players
- If multiple team players are visible (2 or more), set is_group_photo=true
- For group photos, detect and list ALL visible jersey numbers from OUR team
- Match detected jersey numbers to player names from the roster
- List player names comma-separated when multiple players detected

Include in your response:
- is_group_photo: true if 2+ team players are visible, false for single player
- detected_jersey_numbers: Array of objects with "number" (string), "confidence" (0.0-1.0), and "player_name" (from roster match or null)
- primary_jersey_number: The most prominent/clear jersey number (or null if none detected)
- jersey_confidence: Confidence for the primary jersey number (0.0-1.0)
- player_names: Array of player names detected (from roster matches), empty if none
- team_logo_match: true/false if team logo appears to match (or null if logo not visible)
"""

        prompt += """

Provide response in this EXACT JSON format:
{
  "overall_score": <0-100>,
  "quality_tier": "excellent|good|acceptable|poor|reject",
  "factor_scores": {
    "sharpness": <0-100>,
    "exposure": <0-100>,
    "color_accuracy": <0-100>,
    "noise_grain": <0-100>,
    "dynamic_range": <0-100>,
    "rule_of_thirds": <0-100>,
    "subject_placement": <0-100>,
    "framing": <0-100>,
    "leading_lines": <0-100>,
    "balance": <0-100>,
    "depth": <0-100>,
    "negative_space": <0-100>,
    "perspective": <0-100>,
    "facial_detection": <0-100>,
    "eye_status": <0-100>,
    "facial_expression": <0-100>,
    "body_language": <0-100>,
    "subject_attention": <0-100>,
    "group_dynamics": <0-100>,
    "motion_blur": <0-100>,
    "subject_lighting": <0-100>,
    "skin_tones": <0-100>,
    "subject_framing": <0-100>,
    "lighting_quality": <0-100>,
    "color_harmony": <0-100>,
    "emotional_impact": <0-100>,
    "uniqueness": <0-100>,
    "professional_polish": <0-100>
  },
  "detected_issues": ["issue1", "issue2"],
  "critical_defects": [],
  "is_reject": false,
  "ai_summary": "Brief 2-3 sentence summary of image quality and characteristics",
  "recommendations": ["recommendation1", "recommendation2"],
  "subject_analysis": {
    "faces_detected": 0,
    "eyes_status": "all_open|some_closed|blink_detected|no_faces",
    "primary_subject": "description",
    "has_people": false
  },
  "camera_settings": {
    "iso_recommendation": "Specific ISO advice or null",
    "aperture_recommendation": "Specific aperture advice or null",
    "shutter_speed_recommendation": "Specific shutter speed advice or null",
    "exposure_compensation": "Specific EV adjustment advice or null",
    "white_balance": "Specific WB advice or null",
    "focus_mode": "Specific focus mode advice or null",
    "metering_mode": "Specific metering advice or null",
    "general_tips": ["tip1", "tip2"]
  },
  "post_processing": {
    "exposure_adjustment": <-2.0 to +2.0 or null>,
    "contrast_adjustment": <-100 to +100 or null>,
    "highlights_adjustment": <-100 to +100 or null>,
    "shadows_adjustment": <-100 to +100 or null>,
    "whites_adjustment": <-100 to +100 or null>,
    "blacks_adjustment": <-100 to +100 or null>,
    "saturation_adjustment": <-100 to +100 or null>,
    "vibrance_adjustment": <-100 to +100 or null>,
    "sharpness_adjustment": <0 to +100 or null>,
    "noise_reduction": <0 to 100 or null>,
    "temperature_adjustment": <-100 to +100 or null>,
    "tint_adjustment": <-100 to +100 or null>,
    "can_auto_fix": <true if adjustments would help significantly, false otherwise>
  }"""

        # Add jersey detection fields to JSON format if team mode
        if team_mode:
            prompt += """,
  "jersey_detection": {
    "is_group_photo": false,
    "detected_jersey_numbers": [{"number": "23", "confidence": 0.95, "player_name": "John Smith"}],
    "primary_jersey_number": "23",
    "jersey_confidence": 0.95,
    "player_names": ["John Smith"],
    "team_logo_match": true
  }"""

        prompt += """
}
"""

        if exif_data:
            serializable_exif = serialize_exif(exif_data)
            prompt += f"\n\nImage EXIF Data:\n{json.dumps(serializable_exif, indent=2)}"

        if sequence_info:
            serializable_sequence = serialize_exif(sequence_info)
            prompt += f"\n\nSequence Context:\n{json.dumps(serializable_sequence, indent=2)}"

        prompt += "\n\nBe critical but fair. Apply professional photography standards. Closed eyes or blinks should result in rejection (is_reject: true, eye_status score: 0). Return ONLY valid JSON."

        return prompt

    async def analyze_image(
        self,
        image_path: str,
        exif_data: Optional[Dict] = None,
        sequence_info: Optional[Dict] = None,
        team_mode: bool = False,
        player_roster: Optional[list[Dict]] = None,
        team_logo_path: Optional[str] = None,
        team_colors: Optional[Dict] = None
    ) -> ImageAnalysisResult:
        """
        Analyze image using Gemini Vision API.

        Args:
            image_path: Path to the image file
            exif_data: Optional EXIF metadata
            sequence_info: Optional sequence/burst information

        Returns:
            ImageAnalysisResult with all scoring factors
        """
        try:
            # Load image
            img = Image.open(image_path)

            # OPTIMIZATION 1: Resize large images to max 2048px (preserves quality, 5-10x faster)
            max_dimension = 2048
            if img.width > max_dimension or img.height > max_dimension:
                logger.info(f"Resizing image from {img.width}x{img.height} to fit {max_dimension}px")
                # Calculate new dimensions maintaining aspect ratio
                if img.width > img.height:
                    new_width = max_dimension
                    new_height = int((max_dimension / img.width) * img.height)
                else:
                    new_height = max_dimension
                    new_width = int((max_dimension / img.height) * img.width)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized to {new_width}x{new_height}")

            # Create prompt
            prompt = self._create_analysis_prompt(exif_data, sequence_info, team_mode, player_roster, team_colors)

            # Prepare content for Gemini
            content_parts = [prompt, img]

            # Add team logo if provided in team mode
            if team_mode and team_logo_path:
                try:
                    logo_img = Image.open(team_logo_path)
                    # Resize logo to reasonable size (max 512px)
                    max_logo_size = 512
                    if logo_img.width > max_logo_size or logo_img.height > max_logo_size:
                        if logo_img.width > logo_img.height:
                            new_width = max_logo_size
                            new_height = int((max_logo_size / logo_img.width) * logo_img.height)
                        else:
                            new_height = max_logo_size
                            new_width = int((max_logo_size / logo_img.height) * logo_img.width)
                        logo_img = logo_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Add logo to content with context
                    content_parts.insert(1, "Team Logo (for reference):")
                    content_parts.insert(2, logo_img)
                    logger.info("Added team logo to analysis")
                except Exception as e:
                    logger.warning(f"Failed to load team logo: {e}")

            # Call Gemini Vision API with retry logic for timeouts
            logger.info(f"Sending image to Gemini for analysis (team_mode={team_mode})...")

            max_retries = 3
            retry_delay = 2  # Start with 2 seconds
            last_error = None

            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        content_parts,
                        generation_config=genai.GenerationConfig(
                            temperature=0.3,
                            max_output_tokens=6144  # Optimized: Reduced from 8192, but enough for full JSON responses
                        )
                    )
                    break  # Success, exit retry loop
                except (DeadlineExceeded, ResourceExhausted) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Gemini API timeout/rate limit (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Gemini API failed after {max_retries} attempts")
                        raise ValueError(f"Gemini API timeout after {max_retries} retries. Please try again later.") from e

            # Parse response
            logger.info(f"Gemini response candidates count: {len(response.candidates) if hasattr(response, 'candidates') else 0}")

            # Check if we have candidates
            if not response.candidates or len(response.candidates) == 0:
                logger.error("No candidates in Gemini response")
                logger.error(f"Response prompt_feedback: {response.prompt_feedback if hasattr(response, 'prompt_feedback') else 'N/A'}")
                raise ValueError("Gemini did not return any analysis candidates. The image may have been blocked by safety filters.")

            # Check the candidate's finish_reason
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else None
            logger.info(f"Candidate finish_reason: {finish_reason}")
            logger.info(f"Candidate safety_ratings: {candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else 'N/A'}")

            # Check if response was truncated due to max tokens (finish_reason == 2)
            if finish_reason == 2:
                logger.warning("Response truncated due to MAX_TOKENS. Retrying with increased token limit...")
                # Retry with higher token limit using full content_parts (includes team logo if present)
                response = self.model.generate_content(
                    content_parts,
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=8192  # Increased limit for retry
                    )
                )
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else None
                    logger.info(f"Retry finish_reason: {finish_reason}")
                else:
                    raise ValueError("Retry failed: No candidates returned")

            # Try to get content - handle different response formats
            content = None
            try:
                # Try the simple text accessor first
                content = response.text
                logger.info("Got response using response.text accessor")
            except (ValueError, AttributeError) as e:
                logger.info(f"response.text failed ({e}), trying parts accessor...")
                # Fall back to parts accessor
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                    if parts and len(parts) > 0:
                        content = parts[0].text
                        logger.info("Got response using parts accessor")
                    else:
                        logger.error("No parts in candidate content")
                        logger.error(f"Candidate content: {candidate.content if hasattr(candidate, 'content') else 'N/A'}")
                        raise ValueError(f"Gemini response blocked. Finish reason: {finish_reason}")

            if not content:
                raise ValueError("Could not extract content from Gemini response")

            logger.info(f"Gemini response: {content[:200]}...")

            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            elif content.startswith("```"):
                content = content[3:]  # Remove ```

            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```

            content = content.strip()

            # Parse JSON response
            analysis_data = json.loads(content)

            # Convert to Pydantic models
            factor_scores = ImageFactorScores(**analysis_data["factor_scores"])
            subject_analysis = SubjectAnalysis(**analysis_data["subject_analysis"])

            # Parse camera settings if present
            camera_settings = None
            if "camera_settings" in analysis_data and analysis_data["camera_settings"]:
                camera_settings = CameraSettingsRecommendations(**analysis_data["camera_settings"])

            # Parse post-processing recommendations if present
            post_processing = None
            if "post_processing" in analysis_data and analysis_data["post_processing"]:
                post_processing = PostProcessingRecommendations(**analysis_data["post_processing"])

            # Extract jersey detection data if present (team mode)
            CONFIDENCE_THRESHOLD = 0.90
            jersey_detection = analysis_data.get("jersey_detection", {})

            # Filter primary jersey by confidence threshold
            primary_jersey_number = jersey_detection.get("primary_jersey_number")
            jersey_confidence = jersey_detection.get("jersey_confidence")

            # Don't report primary jersey if confidence is too low
            if jersey_confidence and jersey_confidence < CONFIDENCE_THRESHOLD:
                logger.info(f"⚠️ Primary jersey #{primary_jersey_number} confidence too low ({jersey_confidence:.2f} < {CONFIDENCE_THRESHOLD}), filtering out")
                primary_jersey_number = None
                jersey_confidence = None

            is_group_photo = jersey_detection.get("is_group_photo", False)

            # Filter detected jerseys by confidence threshold (80% minimum)
            all_detected_jerseys = jersey_detection.get("detected_jersey_numbers", [])
            detected_jersey_numbers = [
                jersey for jersey in all_detected_jerseys
                if jersey.get("confidence", 0) >= CONFIDENCE_THRESHOLD
            ]

            # Extract player names from high-confidence detections only
            player_names = [
                jersey.get("player_name")
                for jersey in detected_jersey_numbers
                if jersey.get("player_name")
            ]

            # Log filtered vs total detections
            if is_group_photo and all_detected_jerseys:
                filtered_count = len(all_detected_jerseys) - len(detected_jersey_numbers)
                if filtered_count > 0:
                    logger.info(f"🔍 Filtered out {filtered_count} low-confidence detections (below {CONFIDENCE_THRESHOLD*100}%)")

            result = ImageAnalysisResult(
                overall_score=analysis_data["overall_score"],
                quality_tier=QualityTier(analysis_data["quality_tier"]),
                factor_scores=factor_scores,
                detected_issues=analysis_data.get("detected_issues", []),
                critical_defects=analysis_data.get("critical_defects", []),
                is_reject=analysis_data.get("is_reject", False),
                ai_summary=analysis_data["ai_summary"],
                recommendations=analysis_data.get("recommendations", []),
                subject_analysis=subject_analysis,
                camera_settings=camera_settings,
                post_processing=post_processing,
                jersey_number=primary_jersey_number,
                jersey_confidence=jersey_confidence,
                is_group_photo=is_group_photo,
                detected_jersey_numbers=detected_jersey_numbers,
                player_names=player_names
            )

            logger.info(f"Analysis completed: Overall score {result.overall_score}, Tier: {result.quality_tier}")
            if is_group_photo:
                logger.info(f"🎯 GROUP PHOTO detected with {len(detected_jersey_numbers)} players: {', '.join(player_names)}")
                for jersey in detected_jersey_numbers:
                    logger.info(f"  - #{jersey.get('number')} {jersey.get('player_name', 'Unknown')} (confidence: {jersey.get('confidence', 0):.2f})")
            elif primary_jersey_number:
                logger.info(f"Jersey detected: #{primary_jersey_number} (confidence: {jersey_confidence})")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Error analyzing image: {e}", exc_info=True)
            raise

    async def batch_analyze_images(
        self,
        image_paths: list[str],
        exif_data_list: Optional[list[Dict]] = None,
        sequence_info_list: Optional[list[Dict]] = None
    ) -> list[ImageAnalysisResult]:
        """
        Analyze multiple images in sequence.

        Args:
            image_paths: List of image file paths
            exif_data_list: Optional list of EXIF data dicts
            sequence_info_list: Optional list of sequence info dicts

        Returns:
            List of ImageAnalysisResult objects
        """
        results = []

        exif_data_list = exif_data_list or [None] * len(image_paths)
        sequence_info_list = sequence_info_list or [None] * len(image_paths)

        for i, image_path in enumerate(image_paths):
            try:
                result = await self.analyze_image(
                    image_path,
                    exif_data_list[i],
                    sequence_info_list[i]
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {image_path}: {e}")
                # Continue with other images
                continue

        return results
