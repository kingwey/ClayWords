"""uploads.confirm 单元测试（ClamAV 接入分支）

直接调用 async 视图函数 confirm_upload(...)，把 minio/db/扫描客户端全部 mock。
比起搭 FastAPI TestClient 更聚焦：本套只关心扫描接入后的状态转换正确性。

覆盖分支：
- CLAMAV_ENABLED=False（开发降级）→ 标 clean + scanned=False
- CLAMAV_ENABLED=True + 干净 → 标 clean + scanned=True
- CLAMAV_ENABLED=True + 染毒 → quarantined + 尝试删 MinIO + 422
- CLAMAV_ENABLED=True + 扫描器不可用 → 状态回退 pending + 503
- upload 不存在 / 不属于当前用户 → 404
- 状态不是 pending → 400
- MinIO 中对象缺失 → 400
"""

from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import UserInfo
from app.api.uploads import confirm_upload
from app.core.clamav import ClamAVError, ScanResult
from app.models.entities import Base, Upload


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _user() -> UserInfo:
    return UserInfo(user_id="user-1", phone="", role="user")


async def _make_upload(
    session: AsyncSession,
    *,
    uploader_id: str = "user-1",
    state: str = "pending",
    object_key: str = "images/abc.jpg",
) -> Upload:
    upload = Upload(
        object_key=object_key,
        file_name="test.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        state=state,
        uploader_id=uploader_id,
    )
    session.add(upload)
    await session.commit()
    await session.refresh(upload)
    return upload


def _fake_minio(*, exists: bool = True, content: bytes = b"clean-bytes"):
    m = MagicMock()
    m.object_exists = MagicMock(return_value=exists)
    m.get_object_bytes = MagicMock(return_value=content)
    m.delete_object = MagicMock()
    m.get_public_url = MagicMock(return_value="http://minio/x")
    return m


# ---- 降级路径：CLAMAV_ENABLED=False -----------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skip_scan_when_disabled(session: AsyncSession):
    upload = await _make_upload(session)
    minio = _fake_minio()

    with patch("app.api.uploads.settings") as mock_settings:
        mock_settings.CLAMAV_ENABLED = False

        result = await confirm_upload(
            upload_id=upload.upload_id,
            current_user=_user(),
            session=session,
            minio=minio,
        )

    assert result == {"status": "ok", "state": "clean", "scanned": False}
    refreshed = (
        await session.execute(select(Upload).where(Upload.upload_id == upload.upload_id))
    ).scalar_one()
    assert refreshed.state == "clean"
    assert refreshed.scan_result["scanned"] is False
    assert refreshed.scan_result["skip_reason"] == "CLAMAV_ENABLED=False"
    # 降级路径不应碰 ClamAV，也不应拉文件
    minio.get_object_bytes.assert_not_called()


# ---- 扫描启用：干净 ---------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_enabled_clean(session: AsyncSession):
    upload = await _make_upload(session)
    minio = _fake_minio(content=b"clean")

    fake_clamav = MagicMock()
    fake_clamav.scan_bytes = AsyncMock(return_value=ScanResult(clean=True))

    with patch("app.api.uploads.settings") as mock_settings, \
         patch("app.api.uploads.get_clamav", return_value=fake_clamav):
        mock_settings.CLAMAV_ENABLED = True

        result = await confirm_upload(
            upload_id=upload.upload_id,
            current_user=_user(),
            session=session,
            minio=minio,
        )

    assert result == {"status": "ok", "state": "clean", "scanned": True}
    refreshed = (
        await session.execute(select(Upload).where(Upload.upload_id == upload.upload_id))
    ).scalar_one()
    assert refreshed.state == "clean"
    assert refreshed.scan_result == {"scanned": True, "clean": True}

    # 实际调用了扫描，且传了我们从 minio 拿到的字节
    fake_clamav.scan_bytes.assert_awaited_once_with(b"clean")
    minio.delete_object.assert_not_called()


# ---- 扫描启用：染毒 ---------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_enabled_infected_quarantines_and_deletes(session: AsyncSession):
    upload = await _make_upload(session, object_key="images/evil.exe")
    minio = _fake_minio(content=b"EICAR")

    fake_clamav = MagicMock()
    fake_clamav.scan_bytes = AsyncMock(
        return_value=ScanResult(clean=False, virus_name="Eicar-Test-Signature")
    )

    with patch("app.api.uploads.settings") as mock_settings, \
         patch("app.api.uploads.get_clamav", return_value=fake_clamav):
        mock_settings.CLAMAV_ENABLED = True

        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )

    assert exc_info.value.status_code == 422
    # 状态应为 quarantined，且尝试删 MinIO 中的恶意文件
    refreshed = (
        await session.execute(select(Upload).where(Upload.upload_id == upload.upload_id))
    ).scalar_one()
    assert refreshed.state == "quarantined"
    assert refreshed.scan_result["virus_name"] == "Eicar-Test-Signature"
    minio.delete_object.assert_called_once_with("images/evil.exe")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quarantine_survives_minio_delete_failure(session: AsyncSession):
    """删 MinIO 失败不能让响应崩，状态仍要落 quarantined。"""
    upload = await _make_upload(session)
    minio = _fake_minio()
    minio.delete_object.side_effect = RuntimeError("MinIO down")

    fake_clamav = MagicMock()
    fake_clamav.scan_bytes = AsyncMock(
        return_value=ScanResult(clean=False, virus_name="X")
    )

    with patch("app.api.uploads.settings") as mock_settings, \
         patch("app.api.uploads.get_clamav", return_value=fake_clamav):
        mock_settings.CLAMAV_ENABLED = True

        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )

    assert exc_info.value.status_code == 422
    refreshed = (
        await session.execute(select(Upload).where(Upload.upload_id == upload.upload_id))
    ).scalar_one()
    assert refreshed.state == "quarantined"


# ---- 扫描器不可用 -----------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scanner_unavailable_keeps_pending(session: AsyncSession):
    """ClamAV 连不上时返回 503，状态回退 pending（让客户端/外部重试，不能静默放过）。"""
    upload = await _make_upload(session)
    minio = _fake_minio()

    fake_clamav = MagicMock()
    fake_clamav.scan_bytes = AsyncMock(
        side_effect=ClamAVError("connection failed")
    )

    with patch("app.api.uploads.settings") as mock_settings, \
         patch("app.api.uploads.get_clamav", return_value=fake_clamav):
        mock_settings.CLAMAV_ENABLED = True

        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )

    assert exc_info.value.status_code == 503
    refreshed = (
        await session.execute(select(Upload).where(Upload.upload_id == upload.upload_id))
    ).scalar_one()
    # 关键：不是 clean，不是 quarantined —— 留 pending 等重试
    assert refreshed.state == "pending"
    assert refreshed.scan_result["scanned"] is False


# ---- 前置校验 ---------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_missing_upload_404(session: AsyncSession):
    minio = _fake_minio()
    with patch("app.api.uploads.settings") as mock_settings:
        mock_settings.CLAMAV_ENABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id="no-such-id",
                current_user=_user(),
                session=session,
                minio=minio,
            )
    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_other_users_upload_is_404(session: AsyncSession):
    """另一个用户的 upload 应当返回 404（不暴露存在性）。"""
    upload = await _make_upload(session, uploader_id="user-other")
    minio = _fake_minio()

    with patch("app.api.uploads.settings") as mock_settings:
        mock_settings.CLAMAV_ENABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_already_scanned_400(session: AsyncSession):
    upload = await _make_upload(session, state="clean")
    minio = _fake_minio()
    with patch("app.api.uploads.settings") as mock_settings:
        mock_settings.CLAMAV_ENABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )
    assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_object_missing_in_minio_400(session: AsyncSession):
    upload = await _make_upload(session)
    minio = _fake_minio(exists=False)
    with patch("app.api.uploads.settings") as mock_settings:
        mock_settings.CLAMAV_ENABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await confirm_upload(
                upload_id=upload.upload_id,
                current_user=_user(),
                session=session,
                minio=minio,
            )
    assert exc_info.value.status_code == 400
