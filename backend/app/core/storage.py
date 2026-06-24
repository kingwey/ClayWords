"""MinIO Storage Client"""

import io
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

    def put_object_bytes(
        self,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """直接上传字节流到 MinIO 并返回对象键。

        服务端拉取的文件（如 Hunyuan3D 生成的 GLB）走这条路径——
        客户端预签名 PUT 适用于浏览器直传，服务端持有数据时直接 put 更省一次往返。
        """
        if self._client is None:
            raise RuntimeError("MinIO client not connected; call connect() first")
        self._client.put_object(
            settings.MINIO_BUCKET,
            object_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_key

    def delete_object(self, object_key: str):
        """Delete object from storage"""
        self._client.remove_object(settings.MINIO_BUCKET, object_key)

    def get_object_bytes(self, object_key: str) -> bytes:
        """从 MinIO 读回对象内容。给扫描器（ClamAV）/服务端二次校验用。

        小心: 大对象会一次性吃满内存。当前调用方是文件上传后扫描，
        已有 50MB 上限（uploads.py 的 MAX_MODEL_SIZE），可接受。
        如果未来要扫超大文件，应改为流式 + 分块送 ClamAV INSTREAM。
        """
        if self._client is None:
            raise RuntimeError("MinIO client not connected; call connect() first")
        response = self._client.get_object(settings.MINIO_BUCKET, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

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
