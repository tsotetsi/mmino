"""
Job management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from mmino.api.dependencies import (
    get_pagination_params, get_sorting_params, get_filter_params,
    get_job_owner, require_auth_dep, get_current_active_user_dep
)
from mmino.db.session import get_db
from mmino.db import crud
from mmino.schemas import JobResponse, JobDetailResponse, JobListResponse
from mmino.core.config import settings

router = APIRouter()

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    pagination: Dict[str, int] = Depends(get_pagination_params),
    sorting: Dict[str, str] = Depends(get_sorting_params),
    filters: Dict[str, Any] = Depends(get_filter_params),
    auth_info: Dict[str, Any] = Depends(require_auth_dep),
    db = Depends(get_db)
):
    """
    List jobs with filtering and pagination
    """
    user_id = auth_info.get("user_id")
    is_superuser = auth_info.get("is_superuser", False)
    
    # Non-superusers can only see their own jobs
    if not is_superuser and user_id:
        filters["user_id"] = user_id
    
    jobs = crud.get_jobs(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        filters=filters,
        sort_by=sorting["sort_by"],
        sort_order=sorting["sort_order"]
    )
    
    total_jobs = db.query(crud.models.Job).count()
    
    return JobListResponse(
        jobs=[JobResponse.from_orm(job) for job in jobs],
        total=total_jobs,
        page=pagination["skip"] // pagination["limit"] + 1,
        pages=(total_jobs + pagination["limit"] - 1) // pagination["limit"]
    )

@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Get job details
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return JobDetailResponse.from_orm(job)

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Get job status
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "estimated_completion": None  # Could be calculated
    }

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Delete a job
    """
    success = crud.delete_job(db, job_id)
    if not success:
        raise HTTPException(404, "Job not found")
    
    return {"message": "Job deleted successfully"}

@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Retry a failed job
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "failed":
        raise HTTPException(400, "Only failed jobs can be retried")
    
    # Update job status and trigger processing
    job.status = "pending"
    job.progress = 0
    job.error_message = None
    job.retry_count += 1
    db.commit()
    
    # Trigger processing (would need to import and call the task)
    # process_audio_task.delay(job_id, job.operation.value, job.params)
    
    return {
        "message": "Job queued for retry",
        "job_id": job_id,
        "status": "pending"
    }

@router.get("/batch/status")
async def get_batch_status(
    job_ids: str = Query(..., description="Comma-separated list of job IDs"),
    auth_info: Dict[str, Any] = Depends(require_auth_dep),
    db = Depends(get_db)
):
    """
    Get status for multiple jobs
    """
    ids = job_ids.split(",")
    if len(ids) > 50:
        raise HTTPException(400, "Maximum 50 jobs per batch request")
    
    user_id = auth_info.get("user_id")
    is_superuser = auth_info.get("is_superuser", False)
    
    results = []
    for job_id in ids:
        job = crud.get_job(db, job_id.strip())
        if job:
            # Check access
            if is_superuser or (user_id and str(job.user_id) == user_id):
                results.append({
                    "job_id": job_id,
                    "status": job.status.value,
                    "progress": job.progress,
                    "operation": job.operation.value
                })
    
    return {
        "jobs": results,
        "total": len(results),
        "requested": len(ids)
    }

@router.get("/user/recent")
async def get_recent_user_jobs(
    limit: int = Query(10, ge=1, le=100),
    auth_info: Dict[str, Any] = Depends(require_auth_dep),
    db = Depends(get_db)
):
    """
    Get current user's recent jobs
    """
    user_id = auth_info.get("user_id")
    if not user_id:
        raise HTTPException(401, "Authentication required")
    
    jobs = crud.get_user_jobs(db, user_id, limit=limit)
    
    return {
        "jobs": [JobResponse.from_orm(job) for job in jobs],
        "total": len(jobs)
    }