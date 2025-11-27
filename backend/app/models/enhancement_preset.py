"""
Enhancement Preset Models for purpose-driven image optimization.
Defines presets like Instagram Mode, Story Mode, Print Mode, etc.
"""
from typing import Literal
from pydantic import BaseModel, Field
from app.models.image import PostProcessingRecommendations

# Type alias for preset names
PresetName = Literal["auto", "instagram", "story", "facebook", "snapchat", "print", "professional", "vibrant"]


class EnhancementPreset(BaseModel):
    """Configuration for a purpose-driven enhancement preset."""

    name: PresetName
    display_name: str
    description: str
    aspect_ratio: Literal["1:1", "4:5", "9:16", "16:9", "original"]
    quality: int = Field(default=95, ge=1, le=100)

    # Modifier adjustments applied ON TOP of AI recommendations
    exposure_modifier: float = 0.0  # Additional exposure adjustment in EV
    contrast_modifier: int = 0  # Additional contrast (-100 to +100)
    saturation_modifier: int = 0  # Additional saturation (-100 to +100)
    vibrance_modifier: int = 0  # Additional vibrance (-100 to +100)
    sharpness_modifier: int = 0  # Additional sharpness (0 to +100)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "instagram",
                "display_name": "Instagram Mode",
                "description": "Square crop with vibrant colors for Instagram Feed",
                "aspect_ratio": "1:1",
                "quality": 95,
                "vibrance_modifier": 20,
                "sharpness_modifier": 15
            }
        }


# Pre-defined enhancement presets
ENHANCEMENT_PRESETS: dict[PresetName, EnhancementPreset] = {
    "auto": EnhancementPreset(
        name="auto",
        display_name="Auto (AI Recommendations)",
        description="Apply AI-recommended enhancements without any preset modifiers",
        aspect_ratio="original",
        quality=95,
        exposure_modifier=0.0,
        contrast_modifier=0,
        saturation_modifier=0,
        vibrance_modifier=0,
        sharpness_modifier=0,
    ),

    "instagram": EnhancementPreset(
        name="instagram",
        display_name="Instagram Mode",
        description="Square crop with vibrant colors and extra sharpness for Instagram Feed",
        aspect_ratio="1:1",
        quality=95,
        vibrance_modifier=20,  # Extra vibrant for social media
        sharpness_modifier=15,  # Extra sharp for small screens
        saturation_modifier=5,  # Subtle saturation boost
    ),

    "story": EnhancementPreset(
        name="story",
        display_name="Story Mode",
        description="9:16 vertical crop optimized for Instagram Stories, TikTok, and Reels",
        aspect_ratio="9:16",
        quality=92,  # Slightly lower for mobile
        vibrance_modifier=15,
        sharpness_modifier=10,
        contrast_modifier=5,  # Punch for mobile screens
    ),

    "facebook": EnhancementPreset(
        name="facebook",
        display_name="Facebook Mode",
        description="4:5 vertical crop optimized for Facebook Feed and mobile viewing",
        aspect_ratio="4:5",
        quality=93,
        vibrance_modifier=12,  # Moderate vibrance for Facebook
        sharpness_modifier=12,
        saturation_modifier=3,  # Subtle saturation boost
        contrast_modifier=3,  # Slight contrast for engagement
    ),

    "snapchat": EnhancementPreset(
        name="snapchat",
        display_name="Snapchat Mode",
        description="9:16 vertical crop with high impact colors for Snapchat and vertical video",
        aspect_ratio="9:16",
        quality=90,  # Optimized for mobile delivery
        vibrance_modifier=18,  # High vibrance for Snapchat aesthetic
        sharpness_modifier=15,
        saturation_modifier=8,  # More saturated for mobile screens
        contrast_modifier=8,  # Strong contrast for impact
        exposure_modifier=0.1,  # Slight brightness boost
    ),

    "print": EnhancementPreset(
        name="print",
        display_name="Print Mode",
        description="High quality with natural colors for professional printing",
        aspect_ratio="original",  # Keep original aspect ratio
        quality=98,  # Maximum quality for printing
        exposure_modifier=0.0,  # No additional exposure
        contrast_modifier=-5,  # Slightly reduce contrast for print
        saturation_modifier=-3,  # Slightly muted for accurate colors
        sharpness_modifier=5,  # Subtle sharpening
    ),

    "professional": EnhancementPreset(
        name="professional",
        display_name="Professional Mode",
        description="Natural, balanced look with subtle adjustments",
        aspect_ratio="original",
        quality=95,
        exposure_modifier=0.0,
        contrast_modifier=0,
        saturation_modifier=0,
        sharpness_modifier=8,  # Gentle sharpening only
    ),

    "vibrant": EnhancementPreset(
        name="vibrant",
        display_name="Vibrant Mode",
        description="Eye-catching colors with maximum impact for social media",
        aspect_ratio="original",
        quality=95,
        exposure_modifier=0.2,  # Slight brightness boost
        contrast_modifier=10,
        saturation_modifier=15,
        vibrance_modifier=25,
        sharpness_modifier=20,
    ),
}


def get_preset(preset_name: PresetName) -> EnhancementPreset:
    """
    Get enhancement preset by name.

    Args:
        preset_name: Name of the preset to retrieve

    Returns:
        EnhancementPreset configuration

    Raises:
        KeyError: If preset not found
    """
    return ENHANCEMENT_PRESETS[preset_name]


def apply_preset_to_recommendations(
    recommendations: PostProcessingRecommendations,
    preset: EnhancementPreset
) -> PostProcessingRecommendations:
    """
    Apply preset modifiers ON TOP of AI recommendations.

    This allows presets to enhance AI recommendations with additional
    adjustments tailored for specific use cases (social media, print, etc.)

    Args:
        recommendations: AI-generated PostProcessingRecommendations
        preset: EnhancementPreset to apply

    Returns:
        Modified PostProcessingRecommendations with preset adjustments applied
    """
    # Create a copy to avoid modifying original
    modified = recommendations.model_copy(deep=True)

    # Apply modifiers
    if preset.exposure_modifier != 0.0:
        current_exposure = modified.exposure_adjustment or 0.0
        modified.exposure_adjustment = current_exposure + preset.exposure_modifier

    if preset.contrast_modifier != 0:
        current_contrast = modified.contrast_adjustment or 0
        modified.contrast_adjustment = current_contrast + preset.contrast_modifier

    if preset.saturation_modifier != 0:
        current_saturation = modified.saturation_adjustment or 0
        modified.saturation_adjustment = current_saturation + preset.saturation_modifier

    if preset.vibrance_modifier != 0:
        current_vibrance = modified.vibrance_adjustment or 0
        modified.vibrance_adjustment = current_vibrance + preset.vibrance_modifier

    if preset.sharpness_modifier != 0:
        current_sharpness = modified.sharpness_adjustment or 0
        modified.sharpness_adjustment = current_sharpness + preset.sharpness_modifier

    return modified


class BatchEnhancementRequest(BaseModel):
    """Request model for batch enhancement endpoint."""

    image_ids: list[str] = Field(..., min_length=1, max_length=100)
    preset: PresetName = Field(default="professional")
    user_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "image_ids": ["uuid1", "uuid2", "uuid3"],
                "preset": "instagram",
                "user_id": "user123"
            }
        }


class BatchEnhancementResponse(BaseModel):
    """Response model for batch enhancement endpoint."""

    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    total_images: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_abc123",
                "status": "queued",
                "total_images": 25,
                "message": "Batch enhancement job queued successfully"
            }
        }
