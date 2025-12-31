from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List


# User update schema
class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    avatar_url: Optional[str] = None
    max_file_size: Optional[int] = None
    max_daily_jobs: Optional[int] = None
    max_concurrent_jobs: Optional[int] = None
    storage_quota: Optional[int] = None

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            if "@" not in v:
                raise ValueError("Invalid email format")
        return v

    @validator('max_file_size')
    def validate_max_file_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Max file size must be positive")
        return v

    @validator('max_daily_jobs')
    def validate_max_daily_jobs(cls, v):
        if v is not None and v < 0:
            raise ValueError("Max daily jobs cannot be negative")
        return v

# Enums matching models
class JobStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class OperationType(str, Enum):
    CONVERT = "convert"
    TRIM = "trim"
    NORMALIZE = "normalize"
    EXTRACT_AUDIO = "extract_audio"
    MERGE = "merge"
    ADD_EFFECTS = "add_effects"
    COMPRESS = "compress"
    SPECTROGRAM = "spectrogram"

# Base schemas
class JobBase(BaseModel):
    operation: OperationType
    params: Dict[str, Any] = Field(default_factory=dict)

class JobCreate(JobBase):
    original_filename: str
    input_path: str
    expires_at: datetime

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    completed_at: Optional[datetime] = None

# Response schemas
class JobResponse(JobBase):
    job_id: uuid.UUID
    original_filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class JobDetailResponse(JobResponse):
    file_size: Optional[int] = None
    duration: Optional[int] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    input_path: str
    output_path: Optional[str] = None
    params: Dict[str, Any]
    download_count: int = 0
    last_downloaded_at: Optional[datetime] = None

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    pages: int

# Upload schemas
class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
    check_status: str
    download: str

# Operation-specific parameter schemas
class ConvertParams(BaseModel):
    format: str = "mp3"
    bitrate: int = Field(192, ge=64, le=320)
    samplerate: int = Field(44100, ge=8000, le=192000)
    channels: int = Field(2, ge=1, le=2)
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac']
        if v.lower() not in allowed_formats:
            raise ValueError(f"Format must be one of {allowed_formats}")
        return v.lower()

class TrimParams(BaseModel):
    start: float = Field(0.0, ge=0.0, description="Start time in seconds")
    duration: Optional[float] = Field(None, gt=0.0, description="Duration in seconds")
    end: Optional[float] = Field(None, gt=0.0, description="End time in seconds")
    
    @validator('end')
    def validate_times(cls, v, values):
        if v is not None and 'start' in values and v <= values['start']:
            raise ValueError("End time must be greater than start time")
        return v
    
    @validator('duration')
    def validate_duration(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v

class NormalizeParams(BaseModel):
    target: float = Field(-16.0, ge=-30.0, le=0.0, description="Target LUFS level")
    peak: float = Field(-1.0, ge=-10.0, le=0.0, description="True peak level")
    loudness_range: int = Field(11, ge=1, le=20, description="Loudness range target")

class SpectrogramParams(BaseModel):
    width: int = Field(1024, ge=256, le=4096)
    height: int = Field(512, ge=128, le=2048)
    colormap: str = Field("viridis", description="Matplotlib colormap name")
    db_range: int = Field(80, ge=40, le=120)

# User schemas
class UserBase(BaseModel):
    email: str
    username: str

# User create schema
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 32:
            raise ValueError("Username must be between 3 and 32 characters")
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    is_superuser: bool = False
    
    class Config:
        from_attributes = True

# API Key create schema
class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    requests_per_minute: Optional[int] = 60
    requests_per_day: Optional[int] = 1000
    can_upload: Optional[bool] = True
    can_download: Optional[bool] = True
    can_list_jobs: Optional[bool] = True
    can_delete_jobs: Optional[bool] = False
    max_file_size: Optional[int] = 100 * 1024 * 1024  # 100MB

# API Key response schema
class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    total_requests: int
    can_upload: bool
    can_download: bool
    can_list_jobs: bool
    can_delete_jobs: bool
    max_file_size: int

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Stats schemas
class UserStats(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    storage_used: int
    most_used_operation: Optional[str] = None
    last_7d_jobs: int
    daily_jobs_remaining: Optional[int] = None

    class Config:
        from_attributes = True

# System info schemas
class SystemInfo(BaseModel):
    version: str
    uptime: float  # seconds
    database_status: str
    redis_status: str
    storage_status: str
    worker_count: int
    queue_size: int

# System health
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    service: str
    database: bool = False
    redis: bool = False
    minio: bool = False
    
    class Config:
        from_attributes = True

# Statistics
class SystemStats(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_jobs: int
    total_storage_used: int  # bytes
    average_processing_time: float  # seconds
    busiest_operation: str
    last_24h_jobs: int
    
    class Config:
        from_attributes = True