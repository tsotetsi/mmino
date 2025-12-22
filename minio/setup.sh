#!/bin/bash
# Wait for MinIO to be ready
until mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null; do
  echo 'Waiting for MinIO...'
  sleep 1
done

# Create buckets
mc mb myminio/uploads
mc mb myminio/processed
mc mb myminio/archived

# Set bucket policies
mc policy set download myminio/processed
mc policy set public myminio/downloads

echo "MinIO setup complete!"