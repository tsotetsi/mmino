"""
Configuration settings for the MminoIO Audio Processing API
"""
from functools import lru_cache
import secrets
from typing import List, Optional, Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, PostgresDsn, RedisDsn, AnyHttpUrl, ByteSize


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = Field(default="MminoIO Audio Processing API", env="mmino")
    VERSION: str = Field(default="1.0.0", env="VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_V1_PREFIX: str = Field(default="/api/v1", env="API_V1_PREFIX")
    SERVER_HOST: str = Field(default="0.0.0.0", env="SERVER_HOST")
    SERVER_PORT: int = Field(default=8000, env="SERVER_PORT")
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:8000", # FastAPI app
            "http://localhost:5173", # Vite dev server
        ], 
        env="ALLOWED_ORIGINS"
    )

    # Database
    POSTGRES_HOST: str = Field(default="postgres", env="POSTGRES_HOST")
    POSTGRES_USER: str = Field(default="mmino_admin", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="B32qUm3cG5j90yMEwSkYA==", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="mmino_db", env="POSTGRES_DB")
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info: Any) -> Any:
        if isinstance(v, str):
            return v
        values = info.data
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        )
    
    # Redis
    REDIS_HOST: str = Field(default="redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_BROKER_DB: int = 0
    CELERY_RESULT_BACKEND_DB: int = 1
    
    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker_url(cls, v: Any, info: Any) -> Any:
        if isinstance(v, str):
            return v
        values = info.data
        return str(RedisDsn.build(
            scheme="redis",
            password=values.get("REDIS_PASSWORD"),
            host=values.get("REDIS_HOST"),
            port=values.get("REDIS_PORT"),
            path=f"/{values.get('CELERY_BROKER_DB', 0)}",
        ))
    
    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_result_backend_url(cls, v: Any, info: Any) -> Any:
        if isinstance(v, str):
            return v
        values = info.data
        return str(RedisDsn.build(
            scheme="redis",
            password=values.get("REDIS_PASSWORD"),
            host=values.get("REDIS_HOST"),
            port=values.get("REDIS_PORT"),
            path=f"/{values.get('CELERY_RESULT_BACKEND_DB', 1)}",
        ))
    
    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    S3_ENDPOINT_URL: Optional[AnyHttpUrl] = None
    
    @field_validator("S3_ENDPOINT_URL", mode="before")
    @classmethod
    def assemble_s3_endpoint_url(cls, v: Any, info: Any) -> Any:
        if isinstance(v, str):
            return v
        values = info.data
        scheme = "https" if values.get("MINIO_SECURE") else "http"
        return f"{scheme}://{values.get('MINIO_ENDPOINT')}"
    
    # Buckets
    UPLOAD_BUCKET: str = Field(default="uploads", env="UPLOAD_BUCKET")
    PROCESSED_BUCKET: str = Field(default="processed", env="PROCESSED_BUCKET")
    ARCHIVE_BUCKET: str = Field(default="archived", env="ARCHIVE_BUCKET")
    
    # File Limits
    MAX_UPLOAD_SIZE: ByteSize = Field(default=ByteSize(524288000), env="MAX_UPLOAD_SIZE")  # 500MB
    MAX_CONCURRENT_JOBS: int = Field(default=10, env="MAX_CONCURRENT_JOBS")
    UPLOAD_EXPIRY_HOURS: int = Field(default=24, env="UPLOAD_EXPIRY_HOURS")
    DOWNLOAD_EXPIRY_HOURS: int = Field(default=24, env="DOWNLOAD_EXPIRY_HOURS")
    
    # Allowed file types
    ALLOWED_AUDIO_EXTENSIONS: List[str] = Field(
        default=[".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma"],
        env="ALLOWED_AUDIO_EXTENSIONS"
    )
    
    ALLOWED_VIDEO_EXTENSIONS: List[str] = Field(
        default=[".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"],
        env="ALLOWED_VIDEO_EXTENSIONS"
    )
    
    ALLOWED_IMAGE_EXTENSIONS: List[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"],
        env="ALLOWED_IMAGE_EXTENSIONS"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # Worker Settings
    CELERY_WORKER_CONCURRENCY: int = Field(default=4, env="CELERY_WORKER_CONCURRENCY")
    TASK_TIME_LIMIT: int = Field(default=300, env="TASK_TIME_LIMIT")  # 5 minutes
    TASK_SOFT_TIME_LIMIT: int = Field(default=240, env="TASK_SOFT_TIME_LIMIT")  # 4 minutes
    TASK_MAX_RETRIES: int = Field(default=3, env="TASK_MAX_RETRIES")
    
    # Email (for notifications - optional)
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: Optional[int] = Field(default=None, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[str] = Field(default=None, env="EMAILS_FROM_EMAIL")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    
    # Health Check
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    model_config = SettingsConfigDict(
            env_file=".env", 
            case_sensitive=True,
            extra="ignore" # Important: Ignores extra env vars
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    """
    return Settings()

# Global settings instance
settings = get_settings()