"""Hunyuan3D worker 单元测试

覆盖目标：worker.py 之前 0% 测试覆盖，导致 `from app.core.db import ...`
这种潜伏导入 bug 直到 2026-06-24 才被发现；并且 3D 文件落 MinIO 的链路
长期处于 TODO 状态。本套测试锁定关键行为：

1. 远程 GLB 成功 → 真的上传到 MinIO，返回 MinIO URL（不是远程 URL）
2. 远程下载 HTTP 错误 → 异常向上冒泡
3. MinIO 上传失败 → 异常向上冒泡，被 process_hunyuan3d_task 标 failed

所有外部依赖（httpx / minio）都被 mock，测试不需要真实网络或 MinIO 实例。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.hunyuan3d import worker as worker_module


# ---- download_and_store_3d_file ---------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_and_store_returns_minio_url():
    """成功路径：下载完成后必须上传到 MinIO 并返回 MinIO 的 URL。"""
    fake_glb = b"\x67\x6c\x54\x46" + b"\x00" * 1024  # glTF magic + padding

    # mock httpx.AsyncClient.get
    mock_response = MagicMock()
    mock_response.content = fake_glb
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(worker_module.httpx, "AsyncClient", return_value=mock_client), \
         patch.object(worker_module, "__name__", worker_module.__name__):
        # mock MinIO put + get_public_url
        with patch("app.core.storage.minio_client") as mock_minio:
            mock_minio.put_object_bytes = MagicMock(return_value="hunyuan3d/task-xyz.glb")
            mock_minio.get_public_url = MagicMock(
                return_value="http://minio:9000/claywords/hunyuan3d/task-xyz.glb"
            )

            result = await worker_module.download_and_store_3d_file(
                result_url="https://cdn.hunyuan3d.example/job-1.glb",
                task_id="task-xyz",
            )

    # 必须返回 MinIO 的 URL，而不是远程 URL（否则远程过期就失效，是修复前的旧行为）
    assert result == "http://minio:9000/claywords/hunyuan3d/task-xyz.glb"
    assert "hunyuan3d.example" not in result

    # 验证 put_object_bytes 收到正确参数
    mock_minio.put_object_bytes.assert_called_once()
    call = mock_minio.put_object_bytes.call_args
    assert call.kwargs["object_key"] == "hunyuan3d/task-xyz.glb"
    assert call.kwargs["data"] == fake_glb
    assert call.kwargs["content_type"] == "model/gltf-binary"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_propagates_http_error():
    """远程下载失败时，异常应向上冒泡（由调用方决定标记任务 failed）。"""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(worker_module.httpx, "AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await worker_module.download_and_store_3d_file(
                result_url="https://cdn.example/missing.glb",
                task_id="task-404",
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minio_upload_failure_propagates():
    """MinIO 上传失败时异常应冒泡，便于 process_hunyuan3d_task 捕获并标 failed。"""
    mock_response = MagicMock()
    mock_response.content = b"glb-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(worker_module.httpx, "AsyncClient", return_value=mock_client):
        with patch("app.core.storage.minio_client") as mock_minio:
            mock_minio.put_object_bytes = MagicMock(
                side_effect=RuntimeError("MinIO unreachable")
            )

            with pytest.raises(RuntimeError, match="MinIO unreachable"):
                await worker_module.download_and_store_3d_file(
                    result_url="https://cdn.example/ok.glb",
                    task_id="task-minio-down",
                )


# ---- 模块结构 ---------------------------------------------------------------


@pytest.mark.unit
def test_worker_exposes_polling_entrypoint():
    """worker 必须导出主要入口（防止 refactor 误删导致独立进程启动失败）。"""
    assert callable(worker_module.poll_hunyuan3d_tasks)
    assert callable(worker_module.process_hunyuan3d_task)
    assert callable(worker_module.download_and_store_3d_file)
    assert callable(worker_module.start_hunyuan3d_polling_loop)
