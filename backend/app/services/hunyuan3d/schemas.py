"""Hunyuan3D API 请求/响应数据模型"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ImageUrl(BaseModel):
    """图片 URL 或 base64"""
    Url: str = Field(..., description="图片链接或 base64 (data:image/jpeg;base64,xxx)")


class SubmitRequest(BaseModel):
    """提交 3D 生成任务请求"""
    Prompt: Optional[str] = None
    ImageUrl: Optional[ImageUrl] = None
    Model: str = "3.0"
    LowPoly: Optional[bool] = None
    Sketch: Optional[bool] = None


class SubmitResponse(BaseModel):
    """提交任务响应"""
    JobId: str


class QueryRequest(BaseModel):
    """查询任务状态请求"""
    JobId: str


class ResultFile3D(BaseModel):
    """3D 文件信息"""
    Type: str  # OBJ / GLB
    Url: str
    PreviewImageUrl: Optional[str] = None


class QueryResponse(BaseModel):
    """查询任务状态响应"""
    Status: str  # PENDING / PROCESSING / DONE / FAILED
    ResultFile3Ds: Optional[List[ResultFile3D]] = None
    ErrorCode: Optional[str] = None
    ErrorMessage: Optional[str] = None
    ResultCreditConsumed: Optional[int] = None

    @property
    def is_completed(self) -> bool:
        """任务是否完成"""
        return self.Status == "DONE"

    @property
    def is_failed(self) -> bool:
        """任务是否失败"""
        return self.Status == "FAILED"

    @property
    def is_running(self) -> bool:
        """任务是否运行中"""
        return self.Status in ["PENDING", "PROCESSING"]

    def get_glb_url(self) -> Optional[str]:
        """获取 GLB 文件 URL"""
        if not self.ResultFile3Ds:
            return None
        for file in self.ResultFile3Ds:
            if file.Type == "GLB":
                return file.Url
        return None

    def get_obj_url(self) -> Optional[str]:
        """获取 OBJ 文件 URL"""
        if not self.ResultFile3Ds:
            return None
        for file in self.ResultFile3Ds:
            if file.Type == "OBJ":
                return file.Url
        return None
