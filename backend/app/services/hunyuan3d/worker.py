"""Hunyuan3D 后台轮询 Worker

定期查询 Hunyuan3D 任务状态，下载完成的 3D 文件到 MinIO
"""

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Task
from app.db.session import async_session_maker
from app.services.hunyuan3d.client import hunyuan3d_client
from app.core.config import settings
from app.core.time import utcnow
import httpx
import structlog

logger = structlog.get_logger()


async def poll_hunyuan3d_tasks():
    """
    轮询 Hunyuan3D 任务状态

    - 查询所有 pending/running 的 Hunyuan3D 任务
    - 调用 Hunyuan3D query 接口获取状态
    - 任务完成 → 下载 3D 文件到 MinIO
    - 更新 Task 状态
    - 超时任务标记为失败

    执行频率: 由外部调度器决定（推荐 5-10 秒）
    """
    if not settings.ENABLE_HUNYUAN3D:
        logger.debug("hunyuan3d_disabled_skip_poll")
        return

    async with async_session_maker() as session:
        # 查询所有 pending/running 的 Hunyuan3D 任务
        stmt = select(Task).where(
            Task.state.in_(["pending", "running"]),
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        # 过滤出 Hunyuan3D 任务
        hunyuan3d_tasks = [
            task for task in tasks
            if task.payload and task.payload.get("task_type") == "hunyuan3d"
        ]

        if not hunyuan3d_tasks:
            logger.debug("no_hunyuan3d_tasks_to_poll")
            return

        logger.info("polling_hunyuan3d_tasks", count=len(hunyuan3d_tasks))

        for task in hunyuan3d_tasks:
            try:
                await process_hunyuan3d_task(session, task)
            except Exception as e:
                logger.error(
                    "poll_hunyuan3d_task_error",
                    task_id=task.task_id,
                    error=str(e)
                )
                continue


async def process_hunyuan3d_task(session: AsyncSession, task: Task):
    """
    处理单个 Hunyuan3D 任务

    Args:
        session: 数据库会话
        task: Task 实例
    """
    job_id = task.payload.get("job_id")
    if not job_id:
        logger.warning("hunyuan3d_task_missing_job_id", task_id=task.task_id)
        task.state = "failed"
        task.error_message = "缺少 job_id"
        await session.commit()
        return

    # 超时检查（15 分钟）
    timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
    if task.created_at < timeout_threshold:
        logger.warning(
            "hunyuan3d_task_timeout",
            task_id=task.task_id,
            job_id=job_id,
            created_at=task.created_at
        )
        task.state = "failed"
        task.error_message = "任务超时（15 分钟）"
        task.updated_at = utcnow()
        await session.commit()
        return

    # 查询任务状态
    try:
        query_response = await hunyuan3d_client.query(job_id)
    except Exception as e:
        logger.error(
            "hunyuan3d_query_failed",
            task_id=task.task_id,
            job_id=job_id,
            error=str(e)
        )
        # 查询失败不更新任务状态，等待下次轮询重试
        return

    # 更新任务状态
    if query_response.is_running:
        if task.state != "running":
            task.state = "running"
            logger.info("hunyuan3d_task_running", task_id=task.task_id, job_id=job_id)

        # Hunyuan3D 不返回 Progress，设置为 50
        task.progress = 50
        task.updated_at = utcnow()
        await session.commit()

    elif query_response.is_completed:
        logger.info("hunyuan3d_task_completed", task_id=task.task_id, job_id=job_id)

        # 获取 GLB 文件 URL（优先）或 OBJ
        result_url = query_response.get_glb_url() or query_response.get_obj_url()

        if result_url:
            try:
                result_uri = await download_and_store_3d_file(
                    result_url,
                    task.task_id
                )
                task.result_uri = result_uri
                logger.info(
                    "hunyuan3d_file_stored",
                    task_id=task.task_id,
                    result_uri=result_uri
                )
            except Exception as e:
                logger.error(
                    "hunyuan3d_download_failed",
                    task_id=task.task_id,
                    url=result_url,
                    error=str(e)
                )
                task.state = "failed"
                task.error_message = f"下载 3D 文件失败: {str(e)}"
                task.updated_at = utcnow()
                await session.commit()
                return
        else:
            logger.warning(
                "hunyuan3d_no_result_file",
                task_id=task.task_id,
                job_id=job_id
            )

        task.state = "completed"
        task.progress = 100
        task.updated_at = utcnow()
        await session.commit()

    elif query_response.is_failed:
        logger.error(
            "hunyuan3d_task_failed",
            task_id=task.task_id,
            job_id=job_id,
            error=query_response.ErrorMessage
        )
        task.state = "failed"
        task.error_message = query_response.ErrorMessage or "Hunyuan3D 任务失败"
        task.updated_at = utcnow()
        await session.commit()


async def download_and_store_3d_file(result_url: str, task_id: str) -> str:
    """下载 3D 文件并存储到 MinIO，返回平台内可访问的 URL。

    Hunyuan3D 返回的远程 URL 是有有效期的（通常 24 小时），过期后已生成的模型
    会失效。落到平台自己的 MinIO 才能保证模型长期可用。

    Args:
        result_url: Hunyuan3D 返回的 3D 文件远程 URL
        task_id: 任务 ID（用作 object_key 后缀，便于追溯）

    Returns:
        str: MinIO 中文件的可访问 URL

    Raises:
        httpx.HTTPError: 下载失败
        Exception: 上传 MinIO 失败
    """
    from app.core.storage import minio_client

    logger.info("downloading_3d_file", url=result_url, task_id=task_id)

    # 下载远程 GLB（120s 超时容忍 Hunyuan3D CDN 慢节点）
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(result_url)
        response.raise_for_status()
        file_data = response.content

    file_size_mb = len(file_data) / (1024 * 1024)
    logger.info("3d_file_downloaded", task_id=task_id, size_mb=round(file_size_mb, 2))

    # 上传到 MinIO（hunyuan3d/<task_id>.glb，便于按任务回溯）
    object_key = f"hunyuan3d/{task_id}.glb"
    try:
        minio_client.put_object_bytes(
            object_key=object_key,
            data=file_data,
            content_type="model/gltf-binary",
        )
    except Exception as exc:
        logger.error(
            "3d_file_minio_upload_failed",
            task_id=task_id,
            object_key=object_key,
            error=str(exc),
        )
        raise

    minio_url = minio_client.get_public_url(object_key)
    logger.info(
        "3d_file_stored_minio",
        task_id=task_id,
        object_key=object_key,
        url=minio_url,
    )
    return minio_url


# 定时任务调度（供外部调度器调用）
async def start_hunyuan3d_polling_loop():
    """
    启动持续轮询循环

    独立进程运行，每 5 秒轮询一次

    Usage:
        asyncio.run(start_hunyuan3d_polling_loop())
    """
    logger.info("hunyuan3d_polling_loop_started", interval=settings.HUNYUAN3D_POLL_INTERVAL)

    while True:
        try:
            await poll_hunyuan3d_tasks()
        except Exception as e:
            logger.error("hunyuan3d_polling_loop_error", error=str(e))

        await asyncio.sleep(settings.HUNYUAN3D_POLL_INTERVAL)


if __name__ == "__main__":
    # 独立运行轮询 worker
    asyncio.run(start_hunyuan3d_polling_loop())
