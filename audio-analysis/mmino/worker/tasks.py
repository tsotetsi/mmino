from celery import Celery, Task
from celery.utils.log import get_task_logger
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from mmino.core.config import settings
from mmino.core.storage import minio_client, s3_client
from mmino.worker.processor import AudioProcessor, ProcessingError
from mmino.db.session import SessionLocal
from mmino.db import crud
from mmino.schemas import JobUpdate, JobStatus

# Logger
logger = get_task_logger(__name__)

# Initialize Celery
celery_app = Celery("audio_worker")

# Load configuration from Pydantic settings
celery_config = settings.model_dump()
celery_app.config_from_object(celery_config, namespace='CELERY')


# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.TASK_TIME_LIMIT,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    task_routes={
        'app.worker.tasks.process_audio': {'queue': 'audio_processing'},
        'app.worker.tasks.cleanup_expired_files': {'queue': 'maintenance'},
    },
    task_queues={
        'audio_processing': {
            'exchange': 'audio_processing',
            'routing_key': 'audio_processing',
        },
        'maintenance': {
            'exchange': 'maintenance',
            'routing_key': 'maintenance',
        },
    }
)

class BaseTask(Task):
    """Base task with database session handling"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up the database session after task completion"""
        if self._db is not None:
            self._db.close()
            self._db = None

@celery_app.task(bind=True, base=BaseTask, name="process_audio", max_retries=3)
def process_audio_task(self, job_id: str, operation: str, params: Dict[str, Any]):
    """Process audio file asynchronously"""
    
    logger.info(f"Starting audio processing task for job {job_id}")
    
    # Update job status to processing
    try:
        crud.update_job_status(self.db, job_id, JobStatus.PROCESSING)
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        self.retry(countdown=60)
    
    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Find input file in MinIO
            objects = list(minio_client.list_objects("uploads", prefix=job_id))
            if not objects:
                raise FileNotFoundError(f"No input file found for job {job_id}")
            
            input_file = objects[0]
            local_input = os.path.join(tmpdir, "input" + os.path.splitext(input_file.object_name)[1])
            
            # Download from MinIO
            self.update_state(state="DOWNLOADING", meta={"progress": 10})
            logger.info(f"Downloading {input_file.object_name} from MinIO")
            
            minio_client.fget_object("uploads", input_file.object_name, local_input)
            
            # Get file metadata
            processor = AudioProcessor(local_input)
            metadata = processor.get_metadata()
            
            # Update job with metadata
            update_data = JobUpdate(
                file_size=os.path.getsize(local_input),
                duration=metadata.get("duration"),
                bitrate=metadata.get("bitrate"),
                sample_rate=metadata.get("sample_rate"),
                channels=metadata.get("channels")
            )
            crud.update_job(self.db, job_id, update_data)
            
            # Process audio based on operation
            self.update_state(state="PROCESSING", meta={"progress": 30})
            logger.info(f"Processing {operation} with params {params}")
            
            if operation == "convert":
                output_path = processor.convert(
                    format=params.get("format", "mp3"),
                    bitrate=params.get("bitrate", 192),
                    samplerate=params.get("samplerate", 44100),
                    channels=params.get("channels", 2)
                )
            elif operation == "trim":
                output_path = processor.trim(
                    start=params.get("start", 0),
                    duration=params.get("duration"),
                    end=params.get("end")
                )
            elif operation == "normalize":
                output_path = processor.normalize(
                    target=params.get("target", -16.0),
                    peak=params.get("peak", -1.0),
                    loudness_range=params.get("loudness_range", 11)
                )
            elif operation == "extract_audio":
                output_path = processor.extract_audio(
                    format=params.get("format", "mp3")
                )
            elif operation == "compress":
                output_path = processor.compress(
                    threshold=params.get("threshold", -20),
                    ratio=params.get("ratio", 4.0),
                    attack=params.get("attack", 5),
                    release=params.get("release", 50)
                )
            elif operation == "spectrogram":
                output_path = processor.generate_spectrogram(
                    width=params.get("width", 1024),
                    height=params.get("height", 512),
                    colormap=params.get("colormap", "viridis"),
                    db_range=params.get("db_range", 80)
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            # Upload result to MinIO
            self.update_state(state="UPLOADING", meta={"progress": 80})
            logger.info(f"Uploading result to MinIO")
            
            output_ext = os.path.splitext(output_path)[1][1:]  # Remove dot
            output_filename = f"{job_id}_result.{output_ext}"
            output_key = f"processed/{output_filename}"
            
            minio_client.fput_object("processed", output_filename, output_path)
            
            # Generate presigned URL for download (valid for 24 hours)
            download_url = minio_client.presigned_get_object(
                "processed",
                output_filename,
                expires=timedelta(hours=24)
            )
            
            # Update job as completed
            self.update_state(state="COMPLETED", meta={"progress": 100})
            update_data = JobUpdate(
                status=JobStatus.COMPLETED,
                output_path=output_key,
                completed_at=datetime.utcnow()
            )
            crud.update_job(self.db, job_id, update_data)
            
            logger.info(f"Job {job_id} completed successfully")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": output_key,
                "download_url": download_url,
                "file_size": os.path.getsize(output_path),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except ProcessingError as e:
            logger.error(f"Processing error for job {job_id}: {e}")
            update_data = JobUpdate(
                status=JobStatus.FAILED,
                error_message=str(e)
            )
            crud.update_job(self.db, job_id, update_data)
            raise self.retry(exc=e, countdown=60)
            
        except Exception as e:
            logger.error(f"Unexpected error for job {job_id}: {e}")
            update_data = JobUpdate(
                status=JobStatus.FAILED,
                error_message=f"Internal server error: {str(e)}"
            )
            crud.update_job(self.db, job_id, update_data)
            raise

@celery_app.task(name="cleanup_expired_files", bind=True, base=BaseTask)
def cleanup_expired_files(self):
    """Clean up expired files from storage"""
    logger.info("Starting expired files cleanup")
    
    try:
        # Find expired jobs
        expired_jobs = crud.get_expired_jobs(self.db, hours=settings.UPLOAD_EXPIRY_HOURS)
        
        deleted_count = 0
        for job in expired_jobs:
            try:
                # Delete from MinIO
                if job.input_path:
                    bucket, key = job.input_path.split('/', 1)
                    minio_client.remove_object(bucket, key)
                
                if job.output_path and job.status == JobStatus.COMPLETED:
                    bucket, key = job.output_path.split('/', 1)
                    minio_client.remove_object(bucket, key)
                
                # Mark as expired in database
                crud.update_job_status(self.db, job.job_id, JobStatus.EXPIRED)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cleanup job {job.job_id}: {e}")
                continue
        
        logger.info(f"Cleanup completed: {deleted_count} files removed")
        return {"deleted_count": deleted_count, "status": "completed"}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise

@celery_app.task(name="generate_statistics")
def generate_statistics():
    """Generate system statistics"""
    try:
        db = SessionLocal()
        stats = crud.get_system_stats(db)
        db.close()
        
        # Could send to monitoring system here
        logger.info(f"System stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to generate statistics: {e}")
        return None

# Periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-expired-files-every-hour': {
        'task': 'app.worker.tasks.cleanup_expired_files',
        'schedule': 3600.0,  # Every hour
    },
    'generate-daily-stats': {
        'task': 'app.worker.tasks.generate_statistics',
        'schedule': 86400.0,  # Every day
    },
}