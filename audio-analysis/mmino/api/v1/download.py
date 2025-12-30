"""
Download endpoints
"""
import io
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, StreamingResponse

from mmino.core.config import settings
from mmino.core.storage import generate_presigned_url, download_bytes, get_file_metadata
from mmino.api.dependencies import get_job_owner
from mmino.db.session import get_db
from mmino.db import crud

router = APIRouter()

@router.get("/{job_id}")
async def download_file(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Download processed file
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, "Job is not completed")
    
    if not job.output_path:
        raise HTTPException(404, "Output file not found")
    
    # Parse bucket and object from output_path
    if "/" in job.output_path:
        bucket, object_name = job.output_path.split("/", 1)
    else:
        bucket = settings.PROCESSED_BUCKET
        object_name = job.output_path
    
    # Generate presigned URL
    download_url = generate_presigned_url(
        bucket_name=bucket,
        object_name=object_name,
        expiration=timedelta(hours=settings.DOWNLOAD_EXPIRY_HOURS)
    )
    
    if not download_url:
        raise HTTPException(500, "Failed to generate download URL")
    
    # Increment download count
    crud.increment_download_count(db, job_id)
    
    return RedirectResponse(url=download_url)

@router.get("/{job_id}/direct")
async def download_file_direct(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Direct download (stream file)
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, "Job is not completed")
    
    if not job.output_path:
        raise HTTPException(404, "Output file not found")
    
    # Parse bucket and object from output_path
    if "/" in job.output_path:
        bucket, object_name = job.output_path.split("/", 1)
    else:
        bucket = settings.PROCESSED_BUCKET
        object_name = job.output_path
    
    # Download file as bytes
    file_bytes = download_bytes(bucket, object_name)
    if not file_bytes:
        raise HTTPException(404, "File not found in storage")
    
    # Get metadata for headers
    metadata = get_file_metadata(bucket, object_name)
    
    # Increment download count
    crud.increment_download_count(db, job_id)
    
    # Create streaming response
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=metadata.get("content_type", "application/octet-stream") if metadata else "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={job.original_filename}",
            "Content-Length": str(len(file_bytes))
        }
    )

@router.get("/{job_id}/info")
async def get_download_info(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(get_job_owner),
    db = Depends(get_db)
):
    """
    Get download information without downloading
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, "Job is not completed")
    
    if not job.output_path:
        raise HTTPException(404, "Output file not found")
    
    # Parse bucket and object from output_path
    if "/" in job.output_path:
        bucket, object_name = job.output_path.split("/", 1)
    else:
        bucket = settings.PROCESSED_BUCKET
        object_name = job.output_path
    
    # Get file metadata
    metadata = get_file_metadata(bucket, object_name)
    
    return {
        "job_id": job_id,
        "filename": job.original_filename,
        "file_size": job.file_size,
        "content_type": metadata.get("content_type") if metadata else None,
        "download_count": job.download_count,
        "last_downloaded_at": job.last_downloaded_at.isoformat() if job.last_downloaded_at else None,
        "expires_at": job.expires_at.isoformat()
    }