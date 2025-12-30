"""
Admin endpoints
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta

from mmino.api.dependencies import get_current_superuser_dep
from mmino.db.session import get_db
from mmino.db import crud, models
from mmino.schemas import SystemStats, UserResponse
from mmino.core.config import settings

router = APIRouter()

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Get system statistics (admin only)
    """
    stats = crud.get_system_stats(db)
    return SystemStats(**stats)

@router.get("/jobs/summary")
async def get_jobs_summary(
    days: int = Query(7, ge=1, le=365),
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Get job summary for specified days (admin only)
    """
    from sqlalchemy import func, Date
    
    # Get jobs grouped by day and status
    summary = db.query(
        func.date(models.Job.created_at).label('date'),
        models.Job.status,
        func.count(models.Job.id).label('count')
    ).filter(
        models.Job.created_at >= datetime.utcnow() - timedelta(days=days)
    ).group_by(
        func.date(models.Job.created_at),
        models.Job.status
    ).order_by(
        func.date(models.Job.created_at).desc()
    ).all()
    
    # Format results
    result = {}
    for date, status, count in summary:
        date_str = date.isoformat()
        if date_str not in result:
            result[date_str] = {}
        result[date_str][status.value] = count
    
    return {
        "period_days": days,
        "summary": result,
        "total_days": len(result)
    }

@router.get("/storage/usage")
async def get_storage_usage(
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Get storage usage statistics (admin only)
    """
    from sqlalchemy import func
    
    # Get storage by user
    storage_by_user = db.query(
        models.User.username,
        func.coalesce(func.sum(models.Job.file_size), 0).label('storage_used')
    ).outerjoin(
        models.Job,
        models.Job.user_id == models.User.id
    ).filter(
        models.Job.status == "completed"
    ).group_by(
        models.User.id
    ).order_by(
        func.coalesce(func.sum(models.Job.file_size), 0).desc()
    ).limit(20).all()
    
    # Get storage by bucket
    # This would require querying MinIO/S3 directly
    # For now, estimate from database
    
    total_storage = db.query(
        func.coalesce(func.sum(models.Job.file_size), 0)
    ).filter(
        models.Job.status == "completed"
    ).scalar() or 0
    
    return {
        "total_storage_bytes": total_storage,
        "total_storage_human": f"{total_storage / (1024**3):.2f} GB",
        "top_users": [
            {"username": username, "storage_used": storage}
            for username, storage in storage_by_user
        ]
    }

@router.post("/cleanup/old-jobs")
async def cleanup_old_jobs(
    days: int = Query(30, ge=1, le=365),
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Clean up jobs older than specified days (admin only)
    """
    deleted_count = crud.cleanup_old_jobs(db, days)
    
    return {
        "message": f"Deleted {deleted_count} jobs older than {days} days",
        "deleted_count": deleted_count,
        "days_threshold": days
    }

@router.post("/reset/daily-counts")
async def reset_daily_counts(
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Reset daily job counts for all users (admin only)
    """
    updated_count = crud.reset_user_job_counts(db)
    
    return {
        "message": f"Reset daily job counts for {updated_count} users",
        "updated_count": updated_count
    }

@router.get("/health")
async def get_system_health(
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Get system health status (admin only)
    """
    import psutil
    import os
    from datetime import datetime
    
    # Database health
    db_healthy = False
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except:
        pass
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Process info
    process = psutil.Process(os.getpid())
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": db_healthy
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        },
        "process": {
            "memory_mb": process.memory_info().rss / (1024**2),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "uptime_seconds": (datetime.utcnow() - datetime.fromtimestamp(process.create_time())).total_seconds()
        }
    }

@router.get("/logs")
async def get_system_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Get system logs (admin only)
    """
    query = db.query(models.SystemLog)
    
    if level:
        query = query.filter(models.SystemLog.level == level)
    
    if component:
        query = query.filter(models.SystemLog.component == component)
    
    logs = query.order_by(
        models.SystemLog.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "level": log.level,
                "component": log.component,
                "message": log.message,
                "user_id": str(log.user_id) if log.user_id else None,
                "job_id": str(log.job_id) if log.job_id else None,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
                "details": log.details
            }
            for log in logs
        ],
        "total": query.count(),
        "skip": skip,
        "limit": limit
    }