"""
Configuration management for video text inpainting service
"""

import os
import pytz
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from decouple import config

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Video Text Inpainting Service"
    app_version: str = "1.0.0"
    debug: bool = config("DEBUG", default=False, cast=bool)
    environment: str = config("ENVIRONMENT", default="development")
    
    # Server settings
    host: str = config("HOST", default="0.0.0.0")
    port: int = config("PORT", default=8000, cast=int)
    reload: bool = config("RELOAD", default=True, cast=bool)
    
    # Security settings
    secret_key: str = config("SECRET_KEY", default="your-secret-key-here-change-in-production")
    access_token_expire_minutes: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    refresh_token_expire_days: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=30, cast=int)
    algorithm: str = "HS256"
    
    # Database settings
    database_url: str = config("DATABASE_URL", default="postgresql://user:password@localhost:5432/video_inpainting")
    database_echo: bool = config("DATABASE_ECHO", default=False, cast=bool)
    
    # Redis settings
    redis_url: str = config("REDIS_URL", default="redis://localhost:6379/0")

    # Celery settings - fall back to REDIS_URL if not explicitly set
    @property
    def celery_broker_url(self) -> str:
        return config("CELERY_BROKER_URL", default=self.redis_url)

    @property
    def celery_result_backend(self) -> str:
        return config("CELERY_RESULT_BACKEND", default=self.redis_url)
    
    # AWS settings
    aws_access_key_id: str = config("AWS_ACCESS_KEY_ID", default="")
    aws_secret_access_key: str = config("AWS_SECRET_ACCESS_KEY", default="")
    aws_region: str = config("AWS_REGION", default="us-east-2")
    aws_s3_bucket: str = config("AWS_S3_BUCKET", default="taylorswiftnyu")
    
    # Ghostcut API settings
    ghostcut_app_key: str = config("GHOSTCUT_APP_KEY", default="")
    ghostcut_app_secret: str = config("GHOSTCUT_APP_SECRET", default="")
    ghostcut_uid: str = config("GHOSTCUT_UID", default="")
    ghostcut_api_key: str = config("GHOSTCUT_API_KEY", default="")
    ghostcut_api_url: str = config("GHOSTCUT_API_URL", default="https://api.ghostcut.com")

    # Sync.so API settings (for Pro Video Editor segment-based lip-sync)
    sync_api_key: str = config("SYNC_API_KEY", default="")
    sync_api_url: str = config("SYNC_API_URL", default="https://api.sync.so")
    
    # File upload settings
    max_upload_size_mb: int = config("MAX_UPLOAD_SIZE_MB", default=1000, cast=int)
    allowed_video_extensions: List[str] = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    upload_path: str = config("UPLOAD_PATH", default="/app/uploads")
    upload_temp_dir: str = config("UPLOAD_TEMP_DIR", default="./temp_uploads")
    api_base_url: str = config("API_BASE_URL", default="http://localhost:8000")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert cors_origins string to list"""
        return [origin.strip() for origin in self.cors_origins.split(',')]
    
    # Rate limiting
    rate_limit_requests_per_minute: int = config("RATE_LIMIT_REQUESTS_PER_MINUTE", default=60, cast=int)
    
    # Email settings (for notifications)
    smtp_host: str = config("SMTP_HOST", default="")
    smtp_port: int = config("SMTP_PORT", default=587, cast=int)
    smtp_username: str = config("SMTP_USERNAME", default="")
    smtp_password: str = config("SMTP_PASSWORD", default="")
    smtp_use_tls: bool = config("SMTP_USE_TLS", default=True, cast=bool)
    email_from: str = config("EMAIL_FROM", default="noreply@example.com")
    
    # Frontend settings
    frontend_url: str = config("FRONTEND_URL", default="http://localhost:80")
    cors_origins: str = config("CORS_ORIGINS", default="http://localhost:80")
    
    # Processing settings
    default_processing_timeout_minutes: int = config("DEFAULT_PROCESSING_TIMEOUT_MINUTES", default=180, cast=int)
    max_concurrent_jobs_per_user: int = config("MAX_CONCURRENT_JOBS_PER_USER", default=3, cast=int)
    
    # Credit system
    default_credits_new_user: int = config("DEFAULT_CREDITS_NEW_USER", default=100, cast=int)
    credits_per_video_minute: int = config("CREDITS_PER_VIDEO_MINUTE", default=10, cast=int)
    
    # Monitoring and logging
    log_level: str = config("LOG_LEVEL", default="INFO")
    enable_metrics: bool = config("ENABLE_METRICS", default=True, cast=bool)
    
    # Timezone
    timezone: str = config("TZ", default="America/Chicago")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env

# Global settings instance
settings = Settings()

# Timezone utility
def get_local_timezone():
    """Get the configured timezone object"""
    return pytz.timezone(settings.timezone)

def get_local_time():
    """Get current time in the configured timezone"""
    import datetime
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    local_tz = get_local_timezone()
    return utc_now.astimezone(local_tz)

# Validate critical settings
def validate_settings():
    """Validate critical configuration settings"""
    errors = []
    
    if not settings.secret_key or settings.secret_key == "your-secret-key-here-change-in-production":
        if settings.environment == "production":
            errors.append("SECRET_KEY must be set in production")
    
    if not settings.database_url:
        errors.append("DATABASE_URL is required")
    
    if settings.environment == "production":
        if not settings.ghostcut_app_key:
            errors.append("GHOSTCUT_APP_KEY is required in production")
        if not settings.ghostcut_app_secret:
            errors.append("GHOSTCUT_APP_SECRET is required in production")
        if not settings.ghostcut_uid:
            errors.append("GHOSTCUT_UID is required in production")
        if not settings.sync_api_key:
            errors.append("SYNC_API_KEY is required in production")
        if not settings.aws_access_key_id:
            errors.append("AWS_ACCESS_KEY_ID is required in production")
        if not settings.aws_secret_access_key:
            errors.append("AWS_SECRET_ACCESS_KEY is required in production")
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))

# Helper functions
def get_database_url() -> str:
    """Get database URL with proper formatting"""
    return settings.database_url

def get_redis_url() -> str:
    """Get Redis URL with proper formatting"""
    return settings.redis_url

def is_development() -> bool:
    """Check if running in development mode"""
    return settings.environment == "development"

def is_production() -> bool:
    """Check if running in production mode"""
    return settings.environment == "production"

def get_upload_path(user_id: str, filename: str) -> str:
    """Generate upload path for user files"""
    return os.path.join(settings.upload_temp_dir, str(user_id), filename)

def get_s3_key(user_id: str, job_id: str, filename: str) -> str:
    """Generate S3 key for file storage"""
    return f"users/{user_id}/jobs/{job_id}/{filename}"