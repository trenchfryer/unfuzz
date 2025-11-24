import base64
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.image import ImageAnalysisResult, ImageFactorScores, SubjectAnalysis, QualityTier
import logging

logger = logging.getLogger(__name__)


class OpenAIVisionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for OpenAI API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _create_analysis_prompt(self, exif_data: Optional[Dict] = None, sequence_info: Optional[Dict] = None) -> str:
        """Create comprehensive analysis prompt for OpenAI Vision API."""
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
  }
}
"""

        if exif_data:
            prompt += f"\n\nImage EXIF Data:\n{json.dumps(exif_data, indent=2)}"

        if sequence_info:
            prompt += f"\n\nSequence Context:\n{json.dumps(sequence_info, indent=2)}"

        prompt += "\n\nBe critical but fair. Apply professional photography standards. Closed eyes or blinks should result in rejection (is_reject: true, eye_status score: 0). Return ONLY valid JSON."

        return prompt

    async def analyze_image(
        self,
        image_path: str,
        exif_data: Optional[Dict] = None,
        sequence_info: Optional[Dict] = None
    ) -> ImageAnalysisResult:
        """
        Analyze image using OpenAI Vision API.

        Args:
            image_path: Path to the image file
            exif_data: Optional EXIF metadata
            sequence_info: Optional sequence/burst information

        Returns:
            ImageAnalysisResult with all scoring factors
        """
        try:
            # Encode image
            base64_image = self._encode_image(image_path)

            # Create prompt
            prompt = self._create_analysis_prompt(exif_data, sequence_info)

            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional photography expert analyzing images for quality assessment. Provide detailed, accurate scores based on professional photography standards. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                response_format={"type": "json_object"}
            )

            # Parse response
            content = response.choices[0].message.content
            logger.info(f"OpenAI response: {content[:200]}...")

            # Parse JSON response
            analysis_data = json.loads(content)

            # Convert to Pydantic models
            factor_scores = ImageFactorScores(**analysis_data["factor_scores"])
            subject_analysis = SubjectAnalysis(**analysis_data["subject_analysis"])

            result = ImageAnalysisResult(
                overall_score=analysis_data["overall_score"],
                quality_tier=QualityTier(analysis_data["quality_tier"]),
                factor_scores=factor_scores,
                detected_issues=analysis_data.get("detected_issues", []),
                critical_defects=analysis_data.get("critical_defects", []),
                is_reject=analysis_data.get("is_reject", False),
                ai_summary=analysis_data["ai_summary"],
                recommendations=analysis_data.get("recommendations", []),
                subject_analysis=subject_analysis
            )

            logger.info(f"Analysis completed: Overall score {result.overall_score}, Tier: {result.quality_tier}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
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
