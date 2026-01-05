"""
File upload endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import Optional, Dict, Any
import uuid
import os
from datetime import datetime, timedelta
import logging

from mmino.core.config import settings
from mmino.core.storage import upload_file
from mmino.core.security import sanitize_filename, validate_file_extension, require_auth
from mmino.worker.tasks import process_audio_task
from mmino.db.session import get_db
from mmino.db import crud
from mmino.schemas import (
    JobCreate, UploadResponse, ConvertParams, TrimParams, 
    NormalizeParams, SpectrogramParams, OperationType
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    operation: OperationType = OperationType.CONVERT,
    params: Optional[Dict[str, Any]] = None,
    auth_info: Dict[str, Any] = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Upload audio file for processing
    
    Supported operations:
    - convert: Convert audio format
    - trim: Trim audio file
    - normalize: Normalize audio loudness
    - extract_audio: Extract audio from video
    - compress: Apply audio compression
    - spectrogram: Generate spectrogram image
    """
    # Check if user can create new job
    user_id = auth_info.get("user_id")
    if user_id:
        user = crud.get_user_by_id(db, user_id)
        if not user or not user.can_create_job:
            raise HTTPException(
                status_code=400,
                detail="Daily job limit exceeded or account inactive"
            )
    
    # Validate file
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    # Sanitize filename
    original_filename = sanitize_filename(file.filename)
    
    # Validate file extension
    if not validate_file_extension(original_filename):
        raise HTTPException(
            400, 
            f"Unsupported file type. Allowed: {settings.ALLOWED_AUDIO_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS}"
        )
    
    # Generate unique ID
    job_id = str(uuid.uuid4())
    input_filename = f"{job_id}_{original_filename}"
    
    # Create temporary file
    temp_dir = "/tmp/audio_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, input_filename)
    
    try:
        # Save uploaded file to temp location
        file_size = 0
        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
                file_size += len(chunk)
                
                # Check file size limit
                if file_size > settings.MAX_UPLOAD_SIZE:
                    os.remove(temp_path)
                    raise HTTPException(
                        413, 
                        f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
                    )
                
                buffer.write(chunk)
        
        logger.info(f"File saved to temp: {temp_path}, size: {file_size} bytes")
        
        # Upload to MinIO
        success = upload_file(
            bucket_name=settings.UPLOAD_BUCKET,
            object_name=input_filename,
            file_path=temp_path,
            content_type=file.content_type
        )
        
        if not success:
            raise HTTPException(500, "Failed to upload file to storage")
        
        # Parse and validate parameters based on operation
        validated_params = validate_operation_params(operation, params)
        
        # Create job record
        expires_at = datetime.utcnow() + timedelta(hours=settings.UPLOAD_EXPIRY_HOURS)
        
        job_data = JobCreate(
            original_filename=original_filename,
            input_path=f"{settings.UPLOAD_BUCKET}/{input_filename}",
            operation=operation,
            params=validated_params,
            expires_at=expires_at
        )
        
        job = crud.create_job(db, job_id, user_id, job_data)
        
        # Update user's daily job count
        if user_id:
            crud.increment_user_job_count(db, user_id)
        
        # Trigger async processing
        process_audio_task.apply_async(
            args=[job_id, operation.value, validated_params],
            queue='audio_processing'
        )
        
        return UploadResponse(
            job_id=uuid.UUID(job_id),
            status="processing",
            message="File uploaded successfully",
            check_status=f"{settings.API_V1_PREFIX}/jobs/{job_id}/status",
            download=f"{settings.API_V1_PREFIX}/download/{job_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@router.post("/batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    operation: OperationType = OperationType.CONVERT,
    params: Optional[Dict[str, Any]] = None,
    auth_info: Dict[str, Any] = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Upload multiple files for batch processing
    """
    user_id = auth_info.get("user_id")
    
    # Check batch size limit
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per batch")
    
    job_ids = []
    
    for file in files:
        # Create individual job for each file
        job_id = str(uuid.uuid4())
        original_filename = sanitize_filename(file.filename)
        
        if not validate_file_extension(original_filename):
            continue  # Skip invalid files
        
        # Save to temp and upload (simplified for batch)
        temp_dir = "/tmp/audio_batch"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{job_id}_{original_filename}")
        
        try:
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Upload to MinIO
            upload_file(
                bucket_name=settings.UPLOAD_BUCKET,
                object_name=f"{job_id}_{original_filename}",
                file_path=temp_path,
                content_type=file.content_type
            )
            
            # Create job
            expires_at = datetime.utcnow() + timedelta(hours=settings.UPLOAD_EXPIRY_HOURS)
            validated_params = validate_operation_params(operation, params)
            
            job_data = JobCreate(
                original_filename=original_filename,
                input_path=f"{settings.UPLOAD_BUCKET}/{job_id}_{original_filename}",
                operation=operation,
                params=validated_params,
                expires_at=expires_at
            )
            
            crud.create_job(db, job_id, user_id, job_data)
            
            # Trigger processing
            background_tasks.add_task(
                process_audio_task.delay,
                job_id,
                operation.value,
                validated_params
            )
            
            job_ids.append(job_id)
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    return {
        "message": f"Started processing {len(job_ids)} files",
        "job_ids": job_ids,
        "check_status": f"{settings.API_V1_PREFIX}/jobs/batch/status?job_ids={','.join(job_ids)}"
    }

def validate_operation_params(operation: OperationType, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate operation-specific parameters
    """
    if not params:
        params = {}
    
    if operation == OperationType.CONVERT:
        # Set defaults for convert operation
        validated = ConvertParams(**params).dict()
    elif operation == OperationType.TRIM:
        validated = TrimParams(**params).dict()
    elif operation == OperationType.NORMALIZE:
        validated = NormalizeParams(**params).dict()
    elif operation == OperationType.SPECTROGRAM:
        validated = SpectrogramParams(**params).dict()
    else:
        # For other operations, use params as-is
        validated = params
    
    return validated

@router.get("/limits")
async def get_upload_limits(auth_info: Dict[str, Any] = Depends(require_auth)):
    """
    Get upload limits for the current user
    """
    user_id = auth_info.get("user_id")
    
    if not user_id:
        # Default limits for anonymous users
        return {
            "max_file_size": settings.MAX_UPLOAD_SIZE,
            "allowed_extensions": settings.ALLOWED_AUDIO_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS,
            "max_concurrent_jobs": 1,
            "is_authenticated": False
        }
    
    # Get user-specific limits
    db = next(get_db())
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        
        return {
            "max_file_size": user.max_file_size,
            "max_daily_jobs": user.max_daily_jobs,
            "daily_jobs_remaining": max(0, user.max_daily_jobs - user.daily_job_count),
            "max_concurrent_jobs": user.max_concurrent_jobs,
            "storage_quota": user.storage_quota,
            "storage_used": user.storage_used,
            "storage_percentage": user.storage_percentage,
            "allowed_extensions": settings.ALLOWED_AUDIO_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS,
            "is_authenticated": True
        }
    finally:
        db.close()