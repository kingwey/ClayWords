"""Studio Onboarding API - Studio registration and approval"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.time import utcnow

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Studio


router = APIRouter(prefix="/studios", tags=["studios"])


class StudioOnboardingRequest(BaseModel):
    """工作室入驻申请"""
    name: str = Field(..., min_length=2, max_length=100, description="工作室名称")
    location: str = Field(..., description="所在地（如：景德镇、德化、宜兴）")
    specialties: List[str] = Field(..., min_items=1, description="专长工艺（如：白瓷、青瓷、紫砂）")
    capacity: int = Field(..., ge=1, le=100, description="日产能（件/天）")
    price_range_min: float = Field(..., ge=0, description="最低价格")
    price_range_max: float = Field(..., ge=0, description="最高价格")
    estimated_days: int = Field(7, ge=1, le=60, description="预计制作周期（天）")
    contact_person: str = Field(..., description="联系人")
    contact_phone: str = Field(..., description="联系电话")
    business_license: Optional[str] = Field(None, description="营业执照照片 URL")
    portfolio_urls: List[str] = Field(default_factory=list, description="作品集 URL")
    description: Optional[str] = Field(None, max_length=500, description="工作室简介")


class StudioOnboardingResponse(BaseModel):
    studio_id: str
    name: str
    status: str  # pending_review, approved, rejected
    submitted_at: datetime
    message: str


class StudioListItem(BaseModel):
    studio_id: str
    name: str
    location: str
    specialties: List[str]
    capacity: int
    current_load: int
    rating: float
    status: str
    created_at: datetime


class StudioApprovalRequest(BaseModel):
    """管理员审核请求"""
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: Optional[str] = Field(None, description="拒绝原因（reject 时必填）")
    adjusted_capacity: Optional[int] = Field(None, ge=1, le=100, description="调整后的产能")


@router.post("/onboarding", response_model=StudioOnboardingResponse)
async def submit_onboarding(
    request: StudioOnboardingRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """工作室入驻申请提交

    Phase Q5.1.3: 工作室端入驻页
    """
    # 验证价格区间
    if request.price_range_min > request.price_range_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="最低价格不能高于最高价格"
        )

    # 检查是否已提交过申请（同名工作室）
    stmt = select(Studio).where(Studio.name == request.name)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工作室「{request.name}」已存在"
        )

    # 创建工作室记录（pending_review 状态）
    studio = Studio(
        name=request.name,
        location=request.location,
        specialties=request.specialties,
        capacity=request.capacity,
        current_load=0,
        rating=4.5,  # 初始评分
        price_range_min=request.price_range_min,
        price_range_max=request.price_range_max,
        estimated_days=request.estimated_days,
        craft_overrides={
            "contact_person": request.contact_person,
            "contact_phone": request.contact_phone,
            "business_license": request.business_license,
            "portfolio_urls": request.portfolio_urls,
            "description": request.description,
            "status": "pending_review",
            "submitted_by": current_user.user_id,
        }
    )

    session.add(studio)
    await session.commit()
    await session.refresh(studio)

    return StudioOnboardingResponse(
        studio_id=studio.studio_id,
        name=studio.name,
        status="pending_review",
        submitted_at=studio.created_at,
        message="入驻申请已提交，等待平台审核"
    )


@router.get("/pending", response_model=List[StudioListItem])
async def list_pending_studios(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取待审核工作室列表

    Phase Q5.1.1: 管理员查看待审核列表

    TODO: 添加管理员权限检查
    """
    stmt = select(Studio).order_by(Studio.created_at.desc())
    result = await session.execute(stmt)
    studios = result.scalars().all()

    # Filter pending studios
    pending = [
        s for s in studios
        if s.craft_overrides.get("status") == "pending_review"
    ]

    return [
        StudioListItem(
            studio_id=s.studio_id,
            name=s.name,
            location=s.location,
            specialties=s.specialties or [],
            capacity=s.capacity,
            current_load=s.current_load,
            rating=s.rating,
            status=s.craft_overrides.get("status", "unknown"),
            created_at=s.created_at,
        )
        for s in pending
    ]


@router.post("/{studio_id}/approve", response_model=dict)
async def approve_or_reject_studio(
    studio_id: str,
    request: StudioApprovalRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """管理员审核工作室入驻申请

    Phase Q5.1.2: 平台管理员审核接口

    TODO: 添加管理员权限检查
    """
    # 查找工作室
    stmt = select(Studio).where(Studio.studio_id == studio_id)
    result = await session.execute(stmt)
    studio = result.scalar_one_or_none()

    if not studio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作室不存在"
        )

    current_status = studio.craft_overrides.get("status")
    if current_status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"工作室当前状态为 {current_status}，无法审核"
        )

    # 执行审核
    if request.action == "approve":
        # 批准通过（重新赋值整个 dict，确保 SQLAlchemy 追踪 JSONB 变更）
        overrides = dict(studio.craft_overrides or {})
        overrides["status"] = "approved"
        overrides["approved_by"] = current_user.user_id
        overrides["approved_at"] = utcnow().isoformat()

        # 调整产能（如果管理员指定）
        if request.adjusted_capacity is not None:
            studio.capacity = request.adjusted_capacity
            overrides["capacity_adjusted"] = True

        studio.craft_overrides = overrides
        await session.commit()

        return {
            "status": "success",
            "studio_id": studio_id,
            "action": "approved",
            "message": f"工作室「{studio.name}」已批准入驻"
        }

    elif request.action == "reject":
        # 拒绝
        if not request.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="拒绝时必须提供原因"
            )

        overrides = dict(studio.craft_overrides or {})
        overrides["status"] = "rejected"
        overrides["rejected_by"] = current_user.user_id
        overrides["rejected_at"] = utcnow().isoformat()
        overrides["rejection_reason"] = request.reason
        studio.craft_overrides = overrides

        await session.commit()

        return {
            "status": "success",
            "studio_id": studio_id,
            "action": "rejected",
            "message": f"工作室「{studio.name}」入驻申请已拒绝",
            "reason": request.reason
        }


@router.get("", response_model=List[StudioListItem])
async def list_studios(
    status_filter: Optional[str] = None,
    location: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """获取工作室列表（公开接口）

    支持按状态和地区筛选
    """
    stmt = select(Studio).order_by(Studio.rating.desc(), Studio.created_at.desc())
    result = await session.execute(stmt)
    studios = result.scalars().all()

    # 过滤
    filtered = studios
    if status_filter:
        filtered = [
            s for s in filtered
            if s.craft_overrides.get("status") == status_filter
        ]
    if location:
        filtered = [
            s for s in filtered
            if location.lower() in s.location.lower()
        ]

    return [
        StudioListItem(
            studio_id=s.studio_id,
            name=s.name,
            location=s.location,
            specialties=s.specialties or [],
            capacity=s.capacity,
            current_load=s.current_load,
            rating=s.rating,
            status=s.craft_overrides.get("status", "approved"),
            created_at=s.created_at,
        )
        for s in filtered
    ]


@router.get("/{studio_id}", response_model=dict)
async def get_studio_detail(
    studio_id: str,
    session: AsyncSession = Depends(get_session),
):
    """获取工作室详情"""
    stmt = select(Studio).where(Studio.studio_id == studio_id)
    result = await session.execute(stmt)
    studio = result.scalar_one_or_none()

    if not studio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作室不存在"
        )

    return {
        "studio_id": studio.studio_id,
        "name": studio.name,
        "location": studio.location,
        "specialties": studio.specialties or [],
        "capacity": studio.capacity,
        "current_load": studio.current_load,
        "rating": studio.rating,
        "price_range": {
            "min": studio.price_range_min,
            "max": studio.price_range_max,
        },
        "estimated_days": studio.estimated_days,
        "status": studio.craft_overrides.get("status", "approved"),
        "description": studio.craft_overrides.get("description"),
        "portfolio_urls": studio.craft_overrides.get("portfolio_urls", []),
        "created_at": studio.created_at.isoformat(),
    }
