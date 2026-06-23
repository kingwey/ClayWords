"""Hunyuan3D API 客户端"""

import httpx
from app.core.config import settings
from app.services.hunyuan3d.schemas import (
    SubmitRequest, SubmitResponse,
    QueryRequest, QueryResponse
)
import structlog

logger = structlog.get_logger()


class Hunyuan3DClient:
    """腾讯云混元 3D API 客户端"""

    def __init__(self):
        self.base_url = settings.HUNYUAN3D_BASE_URL
        self.api_key = settings.HUNYUAN3D_API_KEY
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    async def submit(self, request: SubmitRequest) -> SubmitResponse:
        """
        提交 3D 生成任务

        Args:
            request: 提交请求（Prompt 或 ImageUrl）

        Returns:
            SubmitResponse: 包含 JobId

        Raises:
            httpx.HTTPStatusError: API 请求失败
            ValueError: 配置错误
        """
        if not self.api_key:
            raise ValueError("HUNYUAN3D_API_KEY not configured")

        url = f"{self.base_url}/v1/ai3d/submit"

        # 过滤 None 值（Model 3.1 不支持 LowPoly/Sketch）
        payload = request.model_dump(exclude_none=True)

        logger.info("hunyuan3d_submit", payload=payload)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                data = response.json()

                # 腾讯云 API 返回格式: {"Response": {"JobId": "xxx", "RequestId": "xxx"}}
                if "Response" in data:
                    data = data["Response"]

                logger.info("hunyuan3d_submit_success", job_id=data.get("JobId"))

                return SubmitResponse(**data)
        except httpx.HTTPStatusError as e:
            logger.error(
                "hunyuan3d_submit_failed",
                status_code=e.response.status_code,
                response_body=e.response.text
            )
            raise
        except Exception as e:
            logger.error("hunyuan3d_submit_error", error=str(e))
            raise

    async def query(self, job_id: str) -> QueryResponse:
        """
        查询任务状态

        Args:
            job_id: Hunyuan3D 任务 ID

        Returns:
            QueryResponse: 包含状态和结果 URL

        Raises:
            httpx.HTTPStatusError: API 请求失败
        """
        if not self.api_key:
            raise ValueError("HUNYUAN3D_API_KEY not configured")

        url = f"{self.base_url}/v1/ai3d/query"
        payload = {"JobId": job_id}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                data = response.json()

                # 腾讯云 API 返回格式: {"Response": {...}}
                if "Response" in data:
                    data = data["Response"]

                logger.debug("hunyuan3d_query", job_id=job_id, status=data.get("Status"))

                return QueryResponse(**data)
        except httpx.HTTPStatusError as e:
            logger.error(
                "hunyuan3d_query_failed",
                job_id=job_id,
                status_code=e.response.status_code,
                response_body=e.response.text
            )
            raise
        except Exception as e:
            logger.error("hunyuan3d_query_error", job_id=job_id, error=str(e))
            raise


# 全局实例
hunyuan3d_client = Hunyuan3DClient()
