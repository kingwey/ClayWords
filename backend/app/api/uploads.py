"""File Upload API with Security Scanning"""

import mimetypes
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Upload
from app.core.storage import MinIOClient, get_minio


router = APIRouter(prefix="/uploads", tags=["uploads"])


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
    Phase Q4: Auto-mark as clean (no real scan yet).
    Phase Q5: Enqueue ClamAV scan task.
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

    # Phase Q4: Auto-mark as clean (Phase Q5 will add real scan)
    upload.state = "clean"
    upload.scan_result = {
        "scanned": False,
        "clean": True,
        "note": "Phase Q4: Auto-approved, real scan in Q5"
    }

    await session.commit()

    return {"status": "ok", "state": upload.state}


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
