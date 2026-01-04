"""
Storage utilities for MinIO/S3 object storage.
"""
from datetime import timedelta
import io
import logging
import os
import tempfile
from typing import Optional, List, Dict, Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from minio import Minio

from mmino.core.config import settings

logger = logging.getLogger(__name__)

# Init MinIO client.
try:
    minio_client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

    # Test connection and buckets existence.
    if not minio_client.bucket_exists(settings.UPLOAD_BUCKET):
        minio_client.make_bucket(settings.UPLOAD_BUCKET)
        logger.info(f"Created bucket: {settings.UPLOAD_BUCKET}")
    
    if not minio_client.bucket_exists(settings.PROCESSED_BUCKET):
        minio_client.make_bucket(settings.PROCESSED_BUCKET)
        logger.info(f"Created bucket: {settings.PROCESSED_BUCKET}")
    
    if not minio_client.bucket_exists(settings.ARCHIVE_BUCKET):
        minio_client.make_bucket(settings.ARCHIVE_BUCKET)
        logger.info(f"Created bucket: {settings.ARCHIVE_BUCKET}")
        
except Exception as e:
    logger.error(f"Failed to initialize MinIO client: {e}")
    minio_client = None

# Initialize S3 client (boto3) for compatibility.
try:
    s3_client = boto3.client(
        's3',
        endpoint_url=str(settings.S3_ENDPOINT_URL),
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'  # Required for MinIO
    )
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    s3_client = None


def upload_file(
    bucket_name: str,
    object_name: str,
    file_path: str,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> bool:
    """
    Upload a file to storage
    """
    try:
        if minio_client:
            minio_client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
                metadata=metadata
            )
        elif s3_client:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            s3_client.upload_file(
                Filename=file_path,
                Bucket=bucket_name,
                Key=object_name,
                ExtraArgs=extra_args
            )
        else:
            logger.error("No storage client available.")
            return False
        
        logger.info(f"Uploaded {object_name} to {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload {object_name}: {e}")
        return False


def upload_bytes(
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> bool:
    """
    Upload bytes data to storage.
    """
    try:
        if minio_client:
            data_stream = io.BytesIO(data)
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(data),
                content_type=content_type,
                metadata=metadata
            )
        elif s3_client:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=data,
                **extra_args
            )
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Uploaded {object_name} to {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload {object_name}: {e}")
        return False


def download_file(
    bucket_name: str,
    object_name: str,
    file_path: str
) -> bool:
    """
    Download a file from storage.
    """
    try:
        if minio_client:
            minio_client.fget_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path
            )
        elif s3_client:
            s3_client.download_file(
                Bucket=bucket_name,
                Key=object_name,
                Filename=file_path
            )
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Downloaded {object_name} from {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {object_name}: {e}")
        return False


def download_bytes(
    bucket_name: str,
    object_name: str
) -> Optional[bytes]:
    """
    Download file as bytes from storage
    """
    try:
        if minio_client:
            response = minio_client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            )
            data = response.read()
            response.close()
            response.release_conn()
            
        elif s3_client:
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=object_name
            )
            data = response['Body'].read()
            
        else:
            logger.error("No storage client available")
            return None
        
        logger.info(f"Downloaded {object_name} from {bucket_name}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to download {object_name}: {e}")
        return None


def generate_presigned_url(
    bucket_name: str,
    object_name: str,
    expiration: timedelta = timedelta(hours=24),
    method: str = "get"
) -> Optional[str]:
    """
    Generate a presigned URL for temporary access
    """
    try:
        if minio_client:
            if method.lower() == "get":
                url = minio_client.presigned_get_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=expiration
                )
            elif method.lower() == "put":
                url = minio_client.presigned_put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=expiration
                )
            else:
                logger.error(f"Unsupported method: {method}")
                return None
        
        elif s3_client:
            if method.lower() == "get":
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_name
                    },
                    ExpiresIn=expiration.total_seconds()
                )
            elif method.lower() == "put":
                url = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_name
                    },
                    ExpiresIn=expiration.total_seconds()
                )
            else:
                logger.error(f"Unsupported method: {method}")
                return None
        
        else:
            logger.error("No storage client available")
            return None
        
        logger.info(f"Generated presigned URL for {object_name}")
        return url
        
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
        return None


def delete_file(
    bucket_name: str,
    object_name: str
) -> bool:
    """
    Delete a file from storage
    """
    try:
        if minio_client:
            minio_client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name
            )
        elif s3_client:
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=object_name
            )
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Deleted {object_name} from {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete {object_name}: {e}")
        return False


def file_exists(
    bucket_name: str,
    object_name: str
) -> bool:
    """
    Check if a file exists in storage
    """
    try:
        if minio_client:
            # MinIO doesn't have a direct exists method, so we try to stat
            minio_client.stat_object(bucket_name, object_name)
            return True
        elif s3_client:
            try:
                s3_client.head_object(Bucket=bucket_name, Key=object_name)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise
        else:
            logger.error("No storage client available")
            return False
        
    except Exception as e:
        if "NoSuchKey" in str(e) or "Not Found" in str(e) or "404" in str(e):
            return False
        logger.error(f"Error checking if {object_name} exists: {e}")
        return False


def get_file_size(
    bucket_name: str,
    object_name: str
) -> Optional[int]:
    """
    Get file size in bytes
    """
    try:
        if minio_client:
            stat = minio_client.stat_object(bucket_name, object_name)
            return stat.size
        elif s3_client:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_name)
            return response['ContentLength']
        else:
            logger.error("No storage client available")
            return None
        
    except Exception as e:
        logger.error(f"Failed to get size of {object_name}: {e}")
        return None


def list_files(
    bucket_name: str,
    prefix: str = "",
    recursive: bool = True
) -> List[Dict[str, Any]]:
    """
    List files in a bucket
    """
    files = []
    
    try:
        if minio_client:
            objects = minio_client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            
            for obj in objects:
                files.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": obj.content_type
                })
        
        elif s3_client:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            "name": obj['Key'],
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'],
                            "etag": obj['ETag']
                        })
        
        else:
            logger.error("No storage client available")
        
    except Exception as e:
        logger.error(f"Failed to list files in {bucket_name}: {e}")
    
    return files


def copy_file(
    source_bucket: str,
    source_object: str,
    dest_bucket: str,
    dest_object: str
) -> bool:
    """
    Copy a file within storage
    """
    try:
        if minio_client:
            minio_client.copy_object(
                dest_bucket,
                dest_object,
                f"/{source_bucket}/{source_object}"
            )
        elif s3_client:
            s3_client.copy_object(
                Bucket=dest_bucket,
                Key=dest_object,
                CopySource=f"{source_bucket}/{source_object}"
            )
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Copied {source_object} to {dest_object}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy {source_object}: {e}")
        return False


def create_bucket(bucket_name: str) -> bool:
    """
    Create a new bucket
    """
    try:
        if minio_client:
            minio_client.make_bucket(bucket_name)
        elif s3_client:
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Created bucket: {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create bucket {bucket_name}: {e}")
        return False


def delete_bucket(bucket_name: str) -> bool:
    """
    Delete a bucket (must be empty)
    """
    try:
        if minio_client:
            minio_client.remove_bucket(bucket_name)
        elif s3_client:
            s3_client.delete_bucket(Bucket=bucket_name)
        else:
            logger.error("No storage client available")
            return False
        
        logger.info(f"Deleted bucket: {bucket_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete bucket {bucket_name}: {e}")
        return False


def get_file_metadata(
    bucket_name: str,
    object_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get file metadata
    """
    try:
        if minio_client:
            stat = minio_client.stat_object(bucket_name, object_name)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        elif s3_client:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_name)
            return {
                "size": response['ContentLength'],
                "last_modified": response['LastModified'],
                "etag": response['ETag'],
                "content_type": response.get('ContentType'),
                "metadata": response.get('Metadata', {})
            }
        else:
            logger.error("No storage client available")
            return None
        
    except Exception as e:
        logger.error(f"Failed to get metadata for {object_name}: {e}")
        return None


def get_download_url(
    bucket_name: str,
    object_name: str,
    filename: Optional[str] = None,
    expires: int = 3600
) -> Optional[str]:
    """
    Get a download URL with optional filename
    """
    try:
        # First get the presigned URL
        url = generate_presigned_url(
            bucket_name=bucket_name,
            object_name=object_name,
            expiration=timedelta(seconds=expires)
        )
        
        if not url:
            return None
        
        # Add filename parameter if provided
        if filename:
            if '?' in url:
                url += f"&response-content-disposition=attachment%3Bfilename%3D{filename}"
            else:
                url += f"?response-content-disposition=attachment%3Bfilename%3D{filename}"
        
        return url
        
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        return None


def cleanup_temp_files(pattern: str = "tmp_*") -> int:
    """
    Clean up temporary files in the temp directory
    Returns number of files deleted
    """
    deleted = 0
    temp_dir = tempfile.gettempdir()
    
    try:
        for filename in os.listdir(temp_dir):
            if filename.startswith(pattern.replace("*", "")):
                filepath = os.path.join(temp_dir, filename)
                try:
                    os.remove(filepath)
                    deleted += 1
                    logger.debug(f"Deleted temp file: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {filename}: {e}")
        
        logger.info(f"Cleaned up {deleted} temporary files")
        return deleted
        
    except Exception as e:
        logger.error(f"Failed to cleanup temp files: {e}")
        return deleted