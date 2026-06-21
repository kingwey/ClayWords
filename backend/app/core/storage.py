"""MinIO Storage Client"""

import uuid
from datetime import timedelta
from typing import Optional
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinIOClient:
    """MinIO storage client for file uploads"""

    def __init__(self):
        self._client: Optional[Minio] = None

    def connect(self):
        """Initialize MinIO client"""
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # Ensure bucket exists
        try:
            if not self._client.bucket_exists(settings.MINIO_BUCKET):
                self._client.make_bucket(settings.MINIO_BUCKET)
        except S3Error as e:
            raise RuntimeError(f"Failed to initialize MinIO: {e}")

    def generate_object_key(self, prefix: str, extension: str) -> str:
        """Generate unique object key"""
        unique_id = uuid.uuid4().hex
        return f"{prefix}/{unique_id}.{extension}"

    def presigned_put_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """Generate presigned PUT URL for direct upload"""
        return self._client.presigned_put_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=expires,
        )

    def presigned_get_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=24),
    ) -> str:
        """Generate presigned GET URL for download"""
        return self._client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=expires,
        )

    def get_public_url(self, object_key: str) -> str:
        """Get public URL (for public buckets)"""
        protocol = "https" if settings.MINIO_SECURE else "http"
        return f"{protocol}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_key}"

    def delete_object(self, object_key: str):
        """Delete object from storage"""
        self._client.remove_object(settings.MINIO_BUCKET, object_key)

    def object_exists(self, object_key: str) -> bool:
        """Check if object exists"""
        try:
            self._client.stat_object(settings.MINIO_BUCKET, object_key)
            return True
        except S3Error:
            return False


# Global instance
minio_client = MinIOClient()


def get_minio() -> MinIOClient:
    """Get MinIO client instance"""
    return minio_client
