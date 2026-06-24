"""File Upload API with Security Scanning"""

import mimetypes
from typing import List

import structlog
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user, UserInfo
from app.core.clamav import ClamAVError, get_clamav
from app.core.config import settings
from app.db.session import get_session
from app.models.entities import Upload
from app.core.storage import MinIOClient, get_minio


router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = structlog.get_logger()


# 允许的文件类型和大小限制
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_MODEL_TYPES = {"model/gltf-binary", "application/octet-stream"}  # .glb
ALLOWED_DOCUMENT_TYPES = {"application/pdf"}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_MODEL_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB


class UploadInitRequest(BaseModel):
    file_name: str
    file_size: int
    mime_type: str
    upload_type: str  # "image" | "model" | "document" | "avatar"


class UploadInitResponse(BaseModel):
    upload_id: str
    object_key: str
    presigned_url: str
    expires_in: int = 3600


class UploadStatusResponse(BaseModel):
    upload_id: str
    state: str  # pending, scanning, clean, quarantined
    scan_result: dict = None
    public_url: str = None


@router.post("/init", response_model=UploadInitResponse)
async def init_upload(
    request: UploadInitRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio: MinIOClient = Depends(get_minio),
):
    """Initialize file upload and get presigned URL.

    Phase Q4: Size + MIME validation, anti-hotlink protection.

    Workflow:
    1. Validate file type and size
    2. Generate unique object key
    3. Create upload record (state=pending)
    4. Return presigned PUT URL
    """
    # Validate file type and size
    mime_type = request.mime_type.lower()

    if request.upload_type == "image":
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image type. Allowed: {ALLOWED_IMAGE_TYPES}"
            )
        if request.file_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image too large. Max: {MAX_IMAGE_SIZE} bytes"
            )
        prefix = "images"

    elif request.upload_type == "model":
        if mime_type not in ALLOWED_MODEL_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model type. Allowed: {ALLOWED_MODEL_TYPES}"
            )
        if request.file_size > MAX_MODEL_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Model too large. Max: {MAX_MODEL_SIZE} bytes"
            )
        prefix = "models"

    elif request.upload_type == "document":
        if mime_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Allowed: {ALLOWED_DOCUMENT_TYPES}"
            )
        if request.file_size > MAX_DOCUMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Document too large. Max: {MAX_DOCUMENT_SIZE} bytes"
            )
        prefix = "documents"

    elif request.upload_type == "avatar":
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid avatar type. Allowed: {ALLOWED_IMAGE_TYPES}"
            )
        if request.file_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Avatar too large. Max: {MAX_IMAGE_SIZE} bytes"
            )
        prefix = "avatars"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload_type"
        )

    # Infer extension from filename
    ext = request.file_name.rsplit('.', 1)[-1] if '.' in request.file_name else 'bin'

    # Generate object key
    object_key = minio.generate_object_key(prefix, ext)

    # Create upload record
    upload = Upload(
        object_key=object_key,
        file_name=request.file_name,
        file_size=request.file_size,
        mime_type=mime_type,
        state="pending",
        uploader_id=current_user.user_id,
    )
    session.add(upload)
    await session.commit()
    await session.refresh(upload)

    # Generate presigned PUT URL
    presigned_url = minio.presigned_put_url(object_key)

    return UploadInitResponse(
        upload_id=upload.upload_id,
        object_key=object_key,
        presigned_url=presigned_url,
        expires_in=3600,
    )


@router.get("/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio: MinIOClient = Depends(get_minio),
):
    """Get upload status and scan result.

    Phase Q4: Return scan status. Phase Q5: integrate ClamAV.
    """
    stmt = select(Upload).where(
        Upload.upload_id == upload_id,
        Upload.uploader_id == current_user.user_id,
    )
    result = await session.execute(stmt)
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )

    # Generate public URL if clean
    public_url = None
    if upload.state == "clean":
        public_url = minio.get_public_url(upload.object_key)

    return UploadStatusResponse(
        upload_id=upload.upload_id,
        state=upload.state,
        scan_result=upload.scan_result or {},
        public_url=public_url,
    )


@router.post("/{upload_id}/confirm")
async def confirm_upload(
    upload_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio: MinIOClient = Depends(get_minio),
):
    """Confirm upload complete and trigger scanning.

    Client calls this after PUT completes successfully.
    流程:
      1. 校验对象在 MinIO 中存在
      2. 若 CLAMAV_ENABLED: 拉回对象 → ClamAV INSTREAM 扫描
         - 干净  → state=clean
         - 染毒  → state=quarantined（同时尝试删除 MinIO 中的恶意文件）
         - 扫描错误 → 保留 pending 状态（不放过，等下次重试）
      3. 否则（开发环境）: 标 clean 并附带 warning 标记，方便事后回溯哪些文件未真正扫描

    生产环境 CLAMAV_ENABLED 为 False 时会被 Settings 启动校验拒启
    （app/core/config.py:_check_production_secrets），所以走到这里的非扫描分支
    只可能在 development/staging。
    """
    stmt = select(Upload).where(
        Upload.upload_id == upload_id,
        Upload.uploader_id == current_user.user_id,
    )
    result = await session.execute(stmt)
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )

    if upload.state != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload already in state: {upload.state}"
        )

    # Verify object exists in MinIO
    if not minio.object_exists(upload.object_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in storage. Upload may have failed."
        )

    if not settings.CLAMAV_ENABLED:
        # 开发环境降级路径：明确标记未扫描，便于事后审计
        upload.state = "clean"
        upload.scan_result = {
            "scanned": False,
            "clean": True,
            "skip_reason": "CLAMAV_ENABLED=False",
        }
        await session.commit()
        logger.warning(
            "upload_skipped_scan",
            upload_id=upload.upload_id,
            object_key=upload.object_key,
            uploader=current_user.user_id,
        )
        return {"status": "ok", "state": upload.state, "scanned": False}

    # 生产路径：拉回字节流送 ClamAV
    try:
        file_data = minio.get_object_bytes(upload.object_key)
    except Exception as exc:  # noqa: BLE001 - 网络/存储层异常都不应放过文件
        logger.error(
            "upload_fetch_failed",
            upload_id=upload.upload_id,
            object_key=upload.object_key,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch file for scanning",
        ) from exc

    clamav = get_clamav()
    upload.state = "scanning"  # 透明状态，方便客户端轮询
    await session.commit()

    try:
        scan_result = await clamav.scan_bytes(file_data)
    except ClamAVError as exc:
        # 扫描失败保留 pending 让客户端/Worker 后续重试，不要静默放过
        logger.error(
            "upload_scan_error",
            upload_id=upload.upload_id,
            object_key=upload.object_key,
            error=str(exc),
        )
        upload.state = "pending"
        upload.scan_result = {"scanned": False, "error": str(exc)}
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Virus scanner unavailable, please retry",
        ) from exc

    if scan_result.is_infected:
        # 命中病毒：隔离状态 + 尝试从 MinIO 删除（best-effort，删除失败不阻塞响应）
        upload.state = "quarantined"
        upload.scan_result = {
            "scanned": True,
            "clean": False,
            "virus_name": scan_result.virus_name,
        }
        try:
            minio.delete_object(upload.object_key)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "upload_quarantine_delete_failed",
                upload_id=upload.upload_id,
                object_key=upload.object_key,
                error=str(exc),
            )
        await session.commit()
        logger.warning(
            "upload_infected",
            upload_id=upload.upload_id,
            object_key=upload.object_key,
            virus=scan_result.virus_name,
            uploader=current_user.user_id,
        )
        # 给客户端明确的拒绝信号，但不暴露过多扫描细节
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File rejected by security scan",
        )

    # 干净
    upload.state = "clean"
    upload.scan_result = {"scanned": True, "clean": True}
    await session.commit()
    return {"status": "ok", "state": upload.state, "scanned": True}


@router.get("", response_model=List[UploadStatusResponse])
async def list_uploads(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    minio: MinIOClient = Depends(get_minio),
    limit: int = 20,
):
    """List user's uploads"""
    stmt = (
        select(Upload)
        .where(Upload.uploader_id == current_user.user_id)
        .order_by(Upload.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    uploads = result.scalars().all()

    return [
        UploadStatusResponse(
            upload_id=u.upload_id,
            state=u.state,
            scan_result=u.scan_result or {},
            public_url=minio.get_public_url(u.object_key) if u.state == "clean" else None,
        )
        for u in uploads
    ]
