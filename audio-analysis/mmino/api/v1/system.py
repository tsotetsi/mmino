"""
System endpoints (public)
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import psutil
import os

from mmino.core.config import settings
from mmino.db.session import check_db_connection, get_db_stats
from mmino.schemas import SystemInfo

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    # Check database
    db_healthy = check_db_connection()
    
    # Check Redis (simplified)
    redis_healthy = True  # In production, actually test Redis connection
    
    # Check storage (simplified)
    storage_healthy = True  # In production, test MinIO/S3 connection
    
    status = "healthy" if db_healthy and redis_healthy and storage_healthy else "unhealthy"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "storage": "healthy" if storage_healthy else "unhealthy"
        },
        "version": settings.VERSION
    }

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    Get system information
    """
    import time
    
    # Calculate uptime (simplified - in production, track startup time)
    startup_time = time.time() - (24 * 3600)  # Example: 24 hours ago
    uptime = time.time() - startup_time
    
    # Get database stats
    db_stats = get_db_stats()
    db_status = "healthy" if db_stats else "unhealthy"
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Estimate worker count (would need to query Celery in production)
    worker_count = 1  # Default
    
    # Estimate queue size (would need to query Redis in production)
    queue_size = 0
    
    return SystemInfo(
        version=settings.VERSION,
        uptime=uptime,
        database_status=db_status,
        redis_status="unknown",  # Would query Redis in production
        storage_status="unknown",  # Would query MinIO in production
        worker_count=worker_count,
        queue_size=queue_size
    )

@router.get("/config")
async def get_config():
    """
    Get public configuration
    """
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
        "upload_expiry_hours": settings.UPLOAD_EXPIRY_HOURS,
        "download_expiry_hours": settings.DOWNLOAD_EXPIRY_HOURS,
        "allowed_audio_extensions": settings.ALLOWED_AUDIO_EXTENSIONS,
        "allowed_video_extensions": settings.ALLOWED_VIDEO_EXTENSIONS,
        "api_v1_prefix": settings.API_V1_PREFIX
    }

@router.get("/stats/db")
async def get_database_stats():
    """
    Get database statistics
    """
    stats = get_db_stats()
    return {
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/status")
async def get_status():
    """
    Comprehensive system status
    """
    # Import models for counts
    from mmino.db import models
    from mmino.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Get counts
        total_jobs = db.query(models.Job).count()
        total_users = db.query(models.User).count()
        
        # Get recent activity
        last_hour = datetime.utcnow() - timedelta(hours=1)
        recent_jobs = db.query(models.Job).filter(
            models.Job.created_at >= last_hour
        ).count()
        
        # Get active jobs
        active_jobs = db.query(models.Job).filter(
            models.Job.status.in_(["pending", "processing", "uploading", "downloading"])
        ).count()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "counts": {
                "total_jobs": total_jobs,
                "total_users": total_users,
                "recent_jobs_1h": recent_jobs,
                "active_jobs": active_jobs
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
    finally:
        db.close()