"""
Configuration settings for the MminoIO Audio Processing API
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator, PostgresDsn, RedisDsn, AnyHttpUrl, ByteSize
from typing import List, Optional, Dict, Any, Union
import secrets
from functools import lru_cache


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = Field("MminoIO Audio Processing API", env="mmino")
    VERSION: str = Field("1.0.0", env="VERSION")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # API
    API_V1_PREFIX: str = Field("/api/v1", env="API_V1_PREFIX")
    SERVER_HOST: str = Field("0.0.0.0", env="SERVER_HOST")
    SERVER_PORT: int = Field(8000, env="SERVER_PORT")
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:8000", # FastAPI app
            "http://localhost:5173", # Vite dev server
        ], 
        env="ALLOWED_ORIGINS"
    )

    # Database
    POSTGRES_HOST: str = Field("postgres", env="POSTGRES_HOST")
    POSTGRES_USER: str = Field("mmino_admin", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("B32qUm3cG5j90yMEwSkYA==", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("mmino_db", env="POSTGRES_DB")
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        )
    
    # Redis
    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_BROKER_DB: int = 0
    CELERY_RESULT_BACKEND_DB: int = 1
    
    @validator("CELERY_BROKER_URL", pre=True)
    def assemble_celery_broker_url(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return str(RedisDsn.build(
            scheme="redis",
            password=values.get("REDIS_PASSWORD"),
            host=values.get("REDIS_HOST"),
            port=values.get("REDIS_PORT"),
            path=f"/{values.get('CELERY_BROKER_DB', 0)}",
        ))
    
    @validator("CELERY_RESULT_BACKEND", pre=True)
    def assemble_celery_result_backend_url(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
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
    MINIO_SECRET_KEY: str = Field("minioadmin123", env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(False, env="MINIO_SECURE")
    S3_ENDPOINT_URL: Optional[AnyHttpUrl] = None
    
    @validator("S3_ENDPOINT_URL", pre=True)
    def assemble_s3_endpoint_url(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        
        scheme = "https" if values.get("MINIO_SECURE") else "http"
        return f"{scheme}://{values.get('MINIO_ENDPOINT')}"
    
    # Buckets
    UPLOAD_BUCKET: str = Field("uploads", env="UPLOAD_BUCKET")
    PROCESSED_BUCKET: str = Field("processed", env="PROCESSED_BUCKET")
    ARCHIVE_BUCKET: str = Field("archived", env="ARCHIVE_BUCKET")
    
    # File Limits
    MAX_UPLOAD_SIZE: ByteSize = Field(ByteSize(524288000), env="MAX_UPLOAD_SIZE")  # 500MB
    MAX_CONCURRENT_JOBS: int = Field(10, env="MAX_CONCURRENT_JOBS")
    UPLOAD_EXPIRY_HOURS: int = Field(24, env="UPLOAD_EXPIRY_HOURS")
    DOWNLOAD_EXPIRY_HOURS: int = Field(24, env="DOWNLOAD_EXPIRY_HOURS")
    
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
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # Worker Settings
    CELERY_WORKER_CONCURRENCY: int = Field(4, env="CELERY_WORKER_CONCURRENCY")
    TASK_TIME_LIMIT: int = Field(300, env="TASK_TIME_LIMIT")  # 5 minutes
    TASK_SOFT_TIME_LIMIT: int = Field(240, env="TASK_SOFT_TIME_LIMIT")  # 4 minutes
    TASK_MAX_RETRIES: int = Field(3, env="TASK_MAX_RETRIES")
    
    # Email (for notifications - optional)
    SMTP_HOST: Optional[str] = Field(None, env="SMTP_HOST")
    SMTP_PORT: Optional[int] = Field(None, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[str] = Field(None, env="EMAILS_FROM_EMAIL")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    
    # Health Check
    HEALTH_CHECK_INTERVAL: int = Field(30, env="HEALTH_CHECK_INTERVAL")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(9090, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()