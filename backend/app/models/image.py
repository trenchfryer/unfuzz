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
