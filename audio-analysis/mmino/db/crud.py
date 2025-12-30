"""
Database CRUD operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from . import models
from mmino.schemas import (
    JobCreate, JobUpdate, UserCreate, UserUpdate, 
    APIKeyCreate, JobStatus, OperationType
)

# ===== JOB CRUD =====

def create_job(
    db: Session, 
    job_id: str, 
    user_id: Optional[str], 
    job_data: JobCreate
) -> models.Job:
    """
    Create a new job
    """
    db_job = models.Job(
        job_id=uuid.UUID(job_id),
        original_filename=job_data.original_filename,
        input_path=job_data.input_path,
        operation=job_data.operation,
        params=job_data.params,
        expires_at=job_data.expires_at,
        user_id=uuid.UUID(user_id) if user_id else None,
        status=JobStatus.PENDING
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_job(db: Session, job_id: str) -> Optional[models.Job]:
    """
    Get job by ID
    """
    return db.query(models.Job).filter(models.Job.job_id == uuid.UUID(job_id)).first()


def get_job_by_id(db: Session, job_id: str) -> Optional[models.Job]:
    """
    Get job by ID (alias for get_job)
    """
    return get_job(db, job_id)


def get_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List[models.Job]:
    """
    Get jobs with filtering and pagination
    """
    query = db.query(models.Job)
    
    # Apply filters
    if filters:
        if "status" in filters:
            query = query.filter(models.Job.status == filters["status"])
        if "operation" in filters:
            query = query.filter(models.Job.operation == filters["operation"])
        if "user_id" in filters:
            query = query.filter(models.Job.user_id == uuid.UUID(filters["user_id"]))
        if "start_date" in filters:
            query = query.filter(models.Job.created_at >= filters["start_date"])
        if "end_date" in filters:
            query = query.filter(models.Job.created_at <= filters["end_date"])
    
    # Apply sorting
    if sort_order == "desc":
        query = query.order_by(desc(getattr(models.Job, sort_by)))
    else:
        query = query.order_by(asc(getattr(models.Job, sort_by)))
    
    # Apply pagination
    return query.offset(skip).limit(limit).all()


def get_user_jobs(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    operation: Optional[str] = None
) -> List[models.Job]:
    """
    Get jobs for a specific user
    """
    query = db.query(models.Job).filter(models.Job.user_id == uuid.UUID(user_id))
    
    if status:
        query = query.filter(models.Job.status == status)
    
    if operation:
        query = query.filter(models.Job.operation == operation)
    
    return query.order_by(models.Job.created_at.desc()).offset(skip).limit(limit).all()


def update_job(db: Session, job_id: str, job_update: JobUpdate) -> Optional[models.Job]:
    """
    Update job
    """
    db_job = get_job(db, job_id)
    if not db_job:
        return None
    
    update_data = job_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_job, field, value)
    
    db.commit()
    db.refresh(db_job)
    return db_job


def update_job_status(
    db: Session, 
    job_id: str, 
    status: JobStatus,
    error_message: Optional[str] = None
) -> Optional[models.Job]:
    """
    Update job status
    """
    db_job = get_job(db, job_id)
    if not db_job:
        return None
    
    db_job.status = status
    if error_message:
        db_job.error_message = error_message
    
    if status == JobStatus.COMPLETED:
        db_job.completed_at = datetime.utcnow()
        # Calculate processing time
        if db_job.created_at:
            db_job.processing_time = (datetime.utcnow() - db_job.created_at).total_seconds()
    
    db.commit()
    db.refresh(db_job)
    return db_job


def update_job_progress(db: Session, job_id: str, progress: float) -> Optional[models.Job]:
    """
    Update job progress
    """
    db_job = get_job(db, job_id)
    if not db_job:
        return None
    
    db_job.progress = min(100.0, max(0.0, progress))
    db.commit()
    db.refresh(db_job)
    return db_job


def delete_job(db: Session, job_id: str) -> bool:
    """
    Delete job
    """
    db_job = get_job(db, job_id)
    if not db_job:
        return False
    
    db.delete(db_job)
    db.commit()
    return True


def get_active_jobs(db: Session, limit: int = 100) -> List[models.Job]:
    """
    Get active (processing) jobs
    """
    return db.query(models.Job).filter(
        models.Job.status.in_([
            JobStatus.PENDING,
            JobStatus.PROCESSING,
            JobStatus.UPLOADING,
            JobStatus.DOWNLOADING
        ])
    ).order_by(models.Job.created_at.asc()).limit(limit).all()


def get_expired_jobs(db: Session, hours: int = 24) -> List[models.Job]:
    """
    Get jobs that have expired
    """
    expiry_time = datetime.utcnow() - timedelta(hours=hours)
    
    return db.query(models.Job).filter(
        models.Job.expires_at < datetime.utcnow(),
        models.Job.status != JobStatus.EXPIRED
    ).all()


def increment_download_count(db: Session, job_id: str) -> Optional[models.Job]:
    """
    Increment download count for a job
    """
    db_job = get_job(db, job_id)
    if not db_job:
        return None
    
    db_job.download_count += 1
    db_job.last_downloaded_at = datetime.utcnow()
    db.commit()
    db.refresh(db_job)
    return db_job


# ===== USER CRUD =====

def create_user(db: Session, user_data: UserCreate) -> models.User:
    """
    Create a new user
    """
    from mmino.core.security import get_password_hash
    hashed_password = get_password_hash(user_data.password)
    
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name if hasattr(user_data, 'full_name') else None
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: uuid.UUID) -> Optional[models.User]:
    """
    Get user by ID
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """
    Get user by ID (alias)
    """
    return get_user(db, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    Get user by email
    """
    return db.query(models.User).filter(func.lower(models.User.email) == func.lower(email)).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Get user by username
    """
    return db.query(models.User).filter(func.lower(models.User.username) == func.lower(username)).first()


def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = False
) -> List[models.User]:
    """
    Get users with pagination
    """
    query = db.query(models.User)
    
    if active_only:
        query = query.filter(models.User.is_active == True)
    
    return query.order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional[models.User]:
    """
    Update user
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        from mmino.core.security import get_password_hash
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: str) -> bool:
    """
    Delete user
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True


def increment_user_job_count(db: Session, user_id: str) -> Optional[models.User]:
    """
    Increment user's daily job count
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    # Check if we need to reset daily count
    now = datetime.utcnow()
    if now.date() > db_user.daily_job_reset_at.date():
        db_user.daily_job_count = 0
        db_user.daily_job_reset_at = now
    
    db_user.daily_job_count += 1
    db_user.updated_at = now
    db.commit()
    db.refresh(db_user)
    return db_user


def reset_user_job_counts(db: Session) -> int:
    """
    Reset daily job counts for all users
    Returns number of users updated
    """
    result = db.query(models.User).filter(
        models.User.daily_job_reset_at < datetime.utcnow() - timedelta(days=1)
    ).update({
        models.User.daily_job_count: 0,
        models.User.daily_job_reset_at: datetime.utcnow()
    })
    
    db.commit()
    return result


def update_user_storage(db: Session, user_id: str, file_size: int) -> Optional[models.User]:
    """
    Update user's storage usage
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.storage_used += file_size
    db.commit()
    db.refresh(db_user)
    return db_user


# ===== API KEY CRUD =====

def create_api_key(db: Session, user_id: str, api_key_data: APIKeyCreate) -> models.APIKey:
    """
    Create a new API key
    """
    from mmino.core.security import generate_api_key
    key_value = generate_api_key()
    
    db_api_key = models.APIKey(
        key=key_value,
        name=api_key_data.name,
        description=api_key_data.description if hasattr(api_key_data, 'description') else None,
        user_id=uuid.UUID(user_id),
        expires_at=api_key_data.expires_at if hasattr(api_key_data, 'expires_at') else None
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    return db_api_key


def get_api_key(db: Session, key: str) -> Optional[models.APIKey]:
    """
    Get API key by value
    """
    print(f"Querying API key with value: {key}, type: {type(key)}")
    print(f"Check for key {db.query(models.APIKey).filter(models.APIKey.key == key).first()}")
    return db.query(models.APIKey).filter(models.APIKey.key == key).first()


def get_user_api_keys(db: Session, user_id: str, active_only: bool = True) -> List[models.APIKey]:
    """
    Get API keys for a user
    """
    query = db.query(models.APIKey).filter(models.APIKey.user_id == uuid.UUID(user_id))
    
    if active_only:
        query = query.filter(models.APIKey.is_active == True)
    
    return query.order_by(models.APIKey.created_at.desc()).all()


def update_api_key(db: Session, key_id: str, is_active: bool) -> Optional[models.APIKey]:
    """
    Update API key status
    """
    db_api_key = db.query(models.APIKey).filter(models.APIKey.id == uuid.UUID(key_id)).first()
    if not db_api_key:
        return None
    
    db_api_key.is_active = is_active
    db_api_key.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_api_key)
    return db_api_key


def delete_api_key(db: Session, key_id: str) -> bool:
    """
    Delete API key
    """
    db_api_key = db.query(models.APIKey).filter(models.APIKey.id == uuid.UUID(key_id)).first()
    if not db_api_key:
        return False
    
    db.delete(db_api_key)
    db.commit()
    return True


def increment_api_key_request_count(db: Session, key: str) -> Optional[models.APIKey]:
    """
    Increment API key request count
    """
    db_api_key = get_api_key(db, key)
    if not db_api_key:
        return None
    
    now = datetime.utcnow()
    
    # Reset minute count if needed
    if now > db_api_key.request_reset_at + timedelta(minutes=1):
        db_api_key.request_count = 0
        db_api_key.request_reset_at = now
    
    # Reset daily count if needed
    if now.date() > db_api_key.daily_reset_at.date():
        db_api_key.daily_request_count = 0
        db_api_key.daily_reset_at = now
    
    db_api_key.request_count += 1
    db_api_key.daily_request_count += 1
    db_api_key.total_requests += 1
    db_api_key.last_used_at = now
    
    db.commit()
    db.refresh(db_api_key)
    return db_api_key


# ===== STATISTICS =====

def get_system_stats(db: Session) -> Dict[str, Any]:
    """
    Get system statistics
    """
    stats = {}
    
    # Job statistics
    total_jobs = db.query(func.count(models.Job.id)).scalar() or 0
    completed_jobs = db.query(func.count(models.Job.id)).filter(
        models.Job.status == JobStatus.COMPLETED
    ).scalar() or 0
    
    failed_jobs = db.query(func.count(models.Job.id)).filter(
        models.Job.status == JobStatus.FAILED
    ).scalar() or 0
    
    active_jobs = db.query(func.count(models.Job.id)).filter(
        models.Job.status.in_([
            JobStatus.PENDING,
            JobStatus.PROCESSING,
            JobStatus.UPLOADING,
            JobStatus.DOWNLOADING
        ])
    ).scalar() or 0
    
    # User statistics
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(
        models.User.is_active == True
    ).scalar() or 0
    
    # Storage statistics
    total_storage = db.query(func.coalesce(func.sum(models.Job.file_size), 0)).filter(
        models.Job.status == JobStatus.COMPLETED
    ).scalar() or 0
    
    # Average processing time
    avg_processing_time = db.query(func.avg(models.Job.processing_time)).filter(
        models.Job.status == JobStatus.COMPLETED,
        models.Job.processing_time.isnot(None)
    ).scalar() or 0
    
    # Most popular operation
    popular_op = db.query(
        models.Job.operation,
        func.count(models.Job.id).label('count')
    ).group_by(models.Job.operation).order_by(desc('count')).first()
    
    # Last 24 hours jobs
    last_24h = datetime.utcnow() - timedelta(hours=24)
    last_24h_jobs = db.query(func.count(models.Job.id)).filter(
        models.Job.created_at >= last_24h
    ).scalar() or 0
    
    stats.update({
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "active_jobs": active_jobs,
        "total_users": total_users,
        "active_users": active_users,
        "total_storage_used": total_storage,
        "average_processing_time": float(avg_processing_time),
        "busiest_operation": popular_op[0] if popular_op else None,
        "last_24h_jobs": last_24h_jobs,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return stats

def get_user_stats(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Get statistics for a specific user
    """
    stats = {}
    
    user_jobs = db.query(models.Job).filter(models.Job.user_id == uuid.UUID(user_id))
    
    total_jobs = user_jobs.count()
    completed_jobs = user_jobs.filter(models.Job.status == JobStatus.COMPLETED).count()
    failed_jobs = user_jobs.filter(models.Job.status == JobStatus.FAILED).count()
    
    # Storage used
    storage_used = db.query(func.coalesce(func.sum(models.Job.file_size), 0)).filter(
        models.Job.user_id == uuid.UUID(user_id),
        models.Job.status == JobStatus.COMPLETED
    ).scalar() or 0
    
    # Most used operation
    popular_op = db.query(
        models.Job.operation,
        func.count(models.Job.id).label('count')
    ).filter(
        models.Job.user_id == uuid.UUID(user_id)
    ).group_by(models.Job.operation).order_by(desc('count')).first()
    
    # Last 7 days activity
    last_7d = datetime.utcnow() - timedelta(days=7)
    last_7d_jobs = user_jobs.filter(models.Job.created_at >= last_7d).count()
    
    stats.update({
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "storage_used": storage_used,
        "most_used_operation": popular_op[0] if popular_op else None,
        "last_7d_jobs": last_7d_jobs,
        "daily_jobs_remaining": None  # Will be populated by user object
    })
    
    return stats


def cleanup_old_jobs(db: Session, days: int = 30) -> int:
    """
    Clean up jobs older than specified days
    Returns number of jobs deleted
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = db.query(models.Job).filter(
        models.Job.created_at < cutoff_date,
        models.Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.EXPIRED])
    ).delete()
    
    db.commit()
    return result


def log_system_event(
    db: Session,
    level: str,
    component: str,
    message: str,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> models.SystemLog:
    """
    Log system event
    """
    log_entry = models.SystemLog(
        level=level,
        component=component,
        message=message,
        user_id=uuid.UUID(user_id) if user_id else None,
        job_id=uuid.UUID(job_id) if job_id else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry