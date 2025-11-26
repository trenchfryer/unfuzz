from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "UnFuzz API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3005",
        "http://localhost:8000",
        "https://unfuzz.vercel.app"
    ]

    # AI Vision Provider
    VISION_PROVIDER: str = "gemini"  # "openai" or "gemini"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.1"
    OPENAI_MAX_TOKENS: int = 1500
    OPENAI_TEMPERATURE: float = 0.3

    # Google Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    DATABASE_URL: str

    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".jpg", ".jpeg", ".png", ".heic",
        ".cr2", ".nef", ".arw", ".dng", ".raf"
    ]
    UPLOAD_FOLDER: str = "./uploads"

    # Image Optimization Settings
    # Storage: Resize images to max dimension for storage (saves 70-80% space vs 6000px originals)
    IMAGE_MAX_DIMENSION: int = 3000  # Max width or height for stored images (good for 8x10" prints at 300dpi)
    # Analysis: Images are further resized to 2048px when sent to Gemini (already implemented)

    # Format & Compression
    USE_WEBP_STORAGE: bool = True  # Convert to WebP for 25-35% smaller files
    JPEG_QUALITY: int = 90  # Quality for JPEG storage (90 = excellent, 85 = very good)
    WEBP_QUALITY: int = 88  # Quality for WebP storage (88 ≈ JPEG 90)

    # Thumbnails
    THUMBNAIL_SIZE: int = 400  # Thumbnail max dimension (pixels)
    THUMBNAIL_QUALITY: int = 75  # Lower quality OK for thumbnails (saves bandwidth)

    # Cleanup
    DELETE_TEMP_FILES: bool = True  # Clean up RAW converted files and temp files

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = "../.env"
        case_sensitive = True


settings = Settings()
