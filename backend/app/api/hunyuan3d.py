"""Hunyuan3D API 端点"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.core.auth import get_current_user, UserInfo
from app.core.config import settings
from app.services.hunyuan3d.client import hunyuan3d_client
from app.services.hunyuan3d.schemas import SubmitRequest
from app.services.tasks.task_service import TaskService, get_task_service
import uuid
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/hunyuan3d", tags=["Hunyuan3D"])


@router.post("/submit")
async def submit_3d_generation(
    request: SubmitRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service)
):
    """
    提交 3D 生成任务

    - 支持文本 Prompt 或图片输入
    - 返回 task_id，前端可通过 /tasks/{task_id} 查询状态
    - 支持 SSE 实时推送进度

    **输入方式**:
    1. 文本: `{"Prompt": "一只可爱的小狗"}`
    2. 图片 URL: `{"ImageUrl": {"Url": "https://..."}}`
    3. 图片 base64: `{"ImageUrl": {"Url": "data:image/jpeg;base64,xxx"}}`

    **模型版本**:
    - 3.0: 支持 LowPoly / Sketch 参数
    - 3.1: 最新版本（不支持 LowPoly / Sketch）
    """
    # 功能开关检查
    if not settings.ENABLE_HUNYUAN3D:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="3D 生成服务暂时不可用"
        )

    # 校验输入
    if not request.Prompt and not request.ImageUrl:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt 或 ImageUrl 至少提供一个"
        )

    # Model 3.1 不支持 LowPoly / Sketch
    if request.Model == "3.1" and (request.LowPoly or request.Sketch):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model 3.1 不支持 LowPoly 和 Sketch 参数，请使用 Model 3.0"
        )

    # 调用 Hunyuan3D submit 接口
    try:
        submit_response = await hunyuan3d_client.submit(request)
    except ValueError as e:
        # 配置错误
        logger.error("hunyuan3d_config_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="3D 生成服务配置错误"
        )
    except Exception as e:
        logger.error("hunyuan3d_submit_exception", error=str(e), user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"调用 Hunyuan3D API 失败: {str(e)}"
        )

    # 创建 Task 记录
    task_id = str(uuid.uuid4())
    payload = {
        "task_type": "hunyuan3d",
        "job_id": submit_response.JobId,
        "prompt": request.Prompt,
        "image_url": request.ImageUrl.Url if request.ImageUrl else None,
        "model": request.Model,
        "low_poly": request.LowPoly,
        "sketch": request.Sketch,
        "user_id": current_user.user_id
    }

    try:
        task_info = await task_service.create_task(
            task_id=task_id,
            state="pending",
            payload=payload
        )
    except Exception as e:
        logger.error("task_create_failed", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建任务记录失败"
        )

    logger.info(
        "hunyuan3d_task_created",
        task_id=task_id,
        job_id=submit_response.JobId,
        user_id=current_user.user_id
    )

    return {
        "task_id": task_id,
        "job_id": submit_response.JobId,
        "status": "pending",
        "message": "3D 生成任务已提交，请通过 task_id 查询进度或使用 SSE 接收实时通知"
    }
