"""
SQLAlchemy database models
"""
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, Enum, Boolean, 
    Text, ForeignKey, BigInteger, Float, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import datetime
import enum

from mmino.db.base import Base


class JobStatus(str, enum.Enum):
    """Status of audio processing jobs"""
    PENDING = "pending"
    UPLOADED = "uploaded"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OperationType(str, enum.Enum):
    """Types of audio operations"""
    CONVERT = "convert"
    TRIM = "trim"
    NORMALIZE = "normalize"
    EXTRACT_AUDIO = "extract_audio"
    MERGE = "merge"
    ADD_EFFECTS = "add_effects"
    COMPRESS = "compress"
    SPECTROGRAM = "spectrogram"
    CONCATENATE = "concatenate"
    REVERSE = "reverse"
    CHANGE_SPEED = "change_speed"
    CHANGE_PITCH = "change_pitch"


class Job(Base):
    """Audio processing job model"""
    __tablename__ = "jobs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Public job identifier (exposed to users)
    job_id = Column(
        UUID(as_uuid=True), 
        unique=True, 
        index=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # File information
    original_filename = Column(String(512), nullable=False)
    input_path = Column(String(1024), nullable=False)  # MinIO path
    output_path = Column(String(1024), nullable=True)  # MinIO path
    
    # Operation details
    operation = Column(
        Enum(OperationType, name="operation_type"), 
        nullable=False
    )
    params = Column(JSON, nullable=False, default=dict)
    
    # Status tracking
    status = Column(
        Enum(JobStatus, name="job_status"), 
        default=JobStatus.PENDING,
        nullable=False
    )
    error_message = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    retry_count = Column(Integer, default=0)
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # File metadata
    file_size = Column(BigInteger, nullable=True)  # in bytes
    duration = Column(Float, nullable=True)  # in seconds
    bitrate = Column(Integer, nullable=True)  # in kbps
    sample_rate = Column(Integer, nullable=True)  # in Hz
    channels = Column(Integer, nullable=True)
    format = Column(String(32), nullable=True)
    codec = Column(String(32), nullable=True)
    
    # Download tracking
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Performance metrics
    processing_time = Column(Float, nullable=True)  # in seconds
    queue_time = Column(Float, nullable=True)  # in seconds
    
    # Worker information
    worker_id = Column(String(128), nullable=True)
    task_id = Column(String(128), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    
    # Indexes
    __table_args__ = (
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_expires_at", "expires_at"),
        Index("ix_jobs_operation", "operation"),
        Index("ix_jobs_user_created", "user_id", "created_at"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        CheckConstraint("file_size > 0", name="file_size_positive"),
    )
    
    def __repr__(self):
        return f"<Job {self.job_id}: {self.operation} - {self.status}>"
    
    @validates('progress')
    def validate_progress(self, key, value):
        """Validate progress is between 0 and 100"""
        if not 0 <= value <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return value
    
    @property
    def is_expired(self) -> bool:
        """Check if job has expired"""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get age of job in seconds"""
        return (datetime.now(self.created_at.tzinfo) - self.created_at).total_seconds()


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # API limits
    max_file_size = Column(
        BigInteger, 
        default=100 * 1024 * 1024,  # 100MB
        nullable=False
    )
    max_daily_jobs = Column(Integer, default=50, nullable=False)
    max_concurrent_jobs = Column(Integer, default=5, nullable=False)
    daily_job_count = Column(Integer, default=0, nullable=False)
    daily_job_reset_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Storage quota (bytes)
    storage_quota = Column(BigInteger, default=10 * 1024 * 1024 * 1024)  # 10GB
    storage_used = Column(BigInteger, default=0)
    
    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email)),
        Index("ix_users_username_lower", func.lower(username)),
        Index("ix_users_created_at", "created_at"),
        CheckConstraint("max_file_size > 0", name="max_file_size_positive"),
        CheckConstraint("max_daily_jobs >= 0", name="max_daily_jobs_non_negative"),
        CheckConstraint("storage_used >= 0", name="storage_used_non_negative"),
        CheckConstraint("storage_quota >= 0", name="storage_quota_non_negative"),
    )
    
    def __repr__(self):
        return f"<User {self.username}: {self.email}>"
    
    @property
    def can_create_job(self) -> bool:
        """Check if user can create a new job"""
        if not self.is_active:
            return False
        
        # Check daily limit
        reset_time = self.daily_job_reset_at
        now = datetime.now(reset_time.tzinfo)
        
        if now.date() > reset_time.date():
            # Reset daily count
            return True
        
        return self.daily_job_count < self.max_daily_jobs
    
    @property
    def storage_percentage(self) -> float:
        """Get storage usage percentage"""
        if self.storage_quota == 0:
            return 0.0
        return (self.storage_used / self.storage_quota) * 100


class APIKey(Base):
    """API Key authentication model"""
    __tablename__ = "api_keys"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # Key information
    key = Column(String(512), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # User relationship
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=60, nullable=False)
    requests_per_day = Column(Integer, default=1000, nullable=False)
    
    # Tracking
    total_requests = Column(BigInteger, default=0, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    daily_request_count = Column(Integer, default=0, nullable=False)
    request_reset_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    daily_reset_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Permissions
    can_upload = Column(Boolean, default=True, nullable=False)
    can_download = Column(Boolean, default=True, nullable=False)
    can_list_jobs = Column(Boolean, default=True, nullable=False)
    can_delete_jobs = Column(Boolean, default=False, nullable=False)
    max_file_size = Column(
        BigInteger, 
        default=100 * 1024 * 1024,  # 100MB
        nullable=False
    )
    
    # Metadata
    ip_whitelist = Column(JSON, nullable=True)  # List of allowed IPs
    user_agent_restriction = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_created_at", "created_at"),
        Index("ix_api_keys_expires_at", "expires_at"),
        CheckConstraint("requests_per_minute > 0", name="requests_per_minute_positive"),
        CheckConstraint("max_file_size > 0", name="api_key_max_file_size_positive"),
    )
    
    def __repr__(self):
        return f"<APIKey {self.name}: {self.user_id}>"
    
    @property
    def is_expired(self) -> bool:
        """Check if API key has expired"""
        if not self.expires_at:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is valid for use"""
        return (
            self.is_active 
            and not self.is_expired
            and self.user.is_active
        )


class SystemLog(Base):
    """System log for auditing and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Log details
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    component = Column(String(64), nullable=False)  # api, worker, storage, etc.
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Context
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    job_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to jobs.job_id
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_system_logs_level_component", "level", "component"),
        Index("ix_system_logs_user_id", "user_id"),
        Index("ix_system_logs_job_id", "job_id"),
        Index("ix_system_logs_created_at_desc", created_at.desc()),
    )


class FailedJob(Base):
    """Track failed jobs for analysis and retry"""
    __tablename__ = "failed_jobs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Job reference
    job_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Failure details
    error_type = Column(String(128), nullable=False)
    error_message = Column(Text, nullable=False)
    error_traceback = Column(Text, nullable=True)
    
    # Context
    worker_id = Column(String(128), nullable=True)
    task_id = Column(String(128), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    failed_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    resolved = Column(Boolean, default=False, nullable=False)
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_failed_jobs_job_id", "job_id"),
        Index("ix_failed_jobs_failed_at", "failed_at"),
        Index("ix_failed_jobs_resolved", "resolved"),
        Index("ix_failed_jobs_error_type", "error_type"),
    )
    
    # Relationships
    job = relationship("Job", foreign_keys=[job_id])


class MonthlyStats(Base):
    """Monthly statistics for reporting"""
    __tablename__ = "monthly_stats"
    
    # Composite primary key
    year = Column(Integer, primary_key=True)
    month = Column(Integer, primary_key=True)  # 1-12
    
    # Job statistics
    total_jobs = Column(Integer, default=0, nullable=False)
    completed_jobs = Column(Integer, default=0, nullable=False)
    failed_jobs = Column(Integer, default=0, nullable=False)
    cancelled_jobs = Column(Integer, default=0, nullable=False)
    
    # User statistics
    active_users = Column(Integer, default=0, nullable=False)
    new_users = Column(Integer, default=0, nullable=False)
    
    # Storage statistics
    total_storage_used = Column(BigInteger, default=0, nullable=False)
    average_file_size = Column(Float, default=0.0, nullable=False)
    
    # Performance statistics
    average_processing_time = Column(Float, default=0.0, nullable=False)
    average_queue_time = Column(Float, default=0.0, nullable=False)
    
    # Popular operations
    most_popular_operation = Column(String(32), nullable=True)
    operation_counts = Column(JSON, nullable=True)  # {operation: count}
    
    # Timestamps
    calculated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        CheckConstraint("month >= 1 AND month <= 12", name="valid_month"),
        CheckConstraint("year >= 2020", name="valid_year"),
        Index("ix_monthly_stats_year_month", "year", "month", unique=True),
    )