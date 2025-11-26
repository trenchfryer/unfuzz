from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class QualityTier(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    REJECT = "reject"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageFactorScores(BaseModel):
    # Technical Quality (12 factors)
    sharpness: float = Field(..., ge=0, le=100)
    exposure: float = Field(..., ge=0, le=100)
    color_accuracy: float = Field(..., ge=0, le=100)
    noise_grain: float = Field(..., ge=0, le=100)
    dynamic_range: float = Field(..., ge=0, le=100)

    # Composition (8 factors)
    rule_of_thirds: float = Field(..., ge=0, le=100)
    subject_placement: float = Field(..., ge=0, le=100)
    framing: float = Field(..., ge=0, le=100)
    leading_lines: float = Field(..., ge=0, le=100)
    balance: float = Field(..., ge=0, le=100)
    depth: float = Field(..., ge=0, le=100)
    negative_space: float = Field(..., ge=0, le=100)
    perspective: float = Field(..., ge=0, le=100)

    # Subject-Specific (10 factors)
    facial_detection: float = Field(..., ge=0, le=100)
    eye_status: float = Field(..., ge=0, le=100)
    facial_expression: float = Field(..., ge=0, le=100)
    body_language: float = Field(..., ge=0, le=100)
    subject_attention: float = Field(..., ge=0, le=100)
    group_dynamics: float = Field(..., ge=0, le=100)
    motion_blur: float = Field(..., ge=0, le=100)
    subject_lighting: float = Field(..., ge=0, le=100)
    skin_tones: float = Field(..., ge=0, le=100)
    subject_framing: float = Field(..., ge=0, le=100)

    # Artistic (5 factors)
    lighting_quality: float = Field(..., ge=0, le=100)
    color_harmony: float = Field(..., ge=0, le=100)
    emotional_impact: float = Field(..., ge=0, le=100)
    uniqueness: float = Field(..., ge=0, le=100)
    professional_polish: float = Field(..., ge=0, le=100)


class SubjectAnalysis(BaseModel):
    faces_detected: int = 0
    eyes_status: str = "unknown"  # all_open, some_closed, blink_detected
    primary_subject: Optional[str] = None
    has_people: bool = False


class CameraSettingsRecommendations(BaseModel):
    """Specific camera settings recommendations based on EXIF analysis"""
    iso_recommendation: Optional[str] = None  # e.g., "Reduce ISO to 800-1600 to minimize noise"
    aperture_recommendation: Optional[str] = None  # e.g., "Use f/2.8-f/4 for sharper subject with background separation"
    shutter_speed_recommendation: Optional[str] = None  # e.g., "Increase to 1/500s to freeze motion"
    exposure_compensation: Optional[str] = None  # e.g., "+0.7 EV to brighten shadows"
    white_balance: Optional[str] = None  # e.g., "Use manual WB 5500K for consistent color"
    focus_mode: Optional[str] = None  # e.g., "Use continuous AF for moving subjects"
    metering_mode: Optional[str] = None  # e.g., "Spot metering on subject's face"
    general_tips: List[str] = []  # Additional shooting tips


class PostProcessingRecommendations(BaseModel):
    """Automated post-processing adjustments that can be applied"""
    exposure_adjustment: Optional[float] = None  # -2.0 to +2.0 EV
    contrast_adjustment: Optional[float] = None  # -100 to +100
    highlights_adjustment: Optional[float] = None  # -100 to +100 (recover blown highlights)
    shadows_adjustment: Optional[float] = None  # -100 to +100 (lift shadows)
    whites_adjustment: Optional[float] = None  # -100 to +100
    blacks_adjustment: Optional[float] = None  # -100 to +100
    saturation_adjustment: Optional[float] = None  # -100 to +100
    vibrance_adjustment: Optional[float] = None  # -100 to +100
    sharpness_adjustment: Optional[float] = None  # 0 to +100
    noise_reduction: Optional[float] = None  # 0 to 100 (strength)
    temperature_adjustment: Optional[int] = None  # -100 to +100 (Kelvin shift)
    tint_adjustment: Optional[int] = None  # -100 to +100 (green/magenta)
    can_auto_fix: bool = False  # Whether automated enhancement is recommended


class ImageAnalysisResult(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    quality_tier: QualityTier
    factor_scores: ImageFactorScores
    detected_issues: List[str] = []
    critical_defects: List[str] = []
    is_reject: bool = False
    ai_summary: str
    recommendations: List[str] = []
    subject_analysis: SubjectAnalysis
    camera_settings: Optional[CameraSettingsRecommendations] = None
    post_processing: Optional[PostProcessingRecommendations] = None
    # Team mode jersey detection
    jersey_number: Optional[str] = None
    jersey_confidence: Optional[float] = Field(None, ge=0, le=1)
    # Group photo support
    is_group_photo: Optional[bool] = False
    detected_jersey_numbers: Optional[List[Dict[str, Any]]] = []
    player_names: Optional[List[str]] = []


class ImageMetadata(BaseModel):
    filename: str
    file_size: int
    width: int
    height: int
    format: str
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[float] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    capture_time: Optional[datetime] = None
    exif_data: Optional[Dict[str, Any]] = None


class ImageUploadResponse(BaseModel):
    id: str
    filename: str
    url: str
    thumbnail_url: str
    metadata: ImageMetadata
    status: AnalysisStatus = AnalysisStatus.PENDING


class ImageAnalysisResponse(BaseModel):
    id: str
    filename: str
    url: str
    thumbnail_url: str
    metadata: ImageMetadata
    analysis: Optional[ImageAnalysisResult] = None
    analysis_status: AnalysisStatus
    analysis_completed_at: Optional[datetime] = None
    is_duplicate: bool = False
    duplicate_group_id: Optional[str] = None
    user_selected: Optional[bool] = None
    user_rating: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str
    settings: Optional[Dict[str, Any]] = {}


class ProjectResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    status: str
    total_images: int = 0
    processed_images: int = 0
    settings: Dict[str, Any] = {}


class ExportRequest(BaseModel):
    project_id: str
    destination: str  # 'local', 'google_drive', 's3'
    image_ids: Optional[List[str]] = None  # If None, export all selected
    export_settings: Optional[Dict[str, Any]] = {}
