"""Studio Order Management API - Accept/Reject orders"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Order, OrderLog, Studio


router = APIRouter(prefix="/studio/orders", tags=["studio-orders"])


class OrderSummary(BaseModel):
    """订单摘要"""
    order_id: str
    design_id: str
    status: str
    total_price: float
    estimated_days: int
    created_at: datetime
    design_params: dict


class AcceptOrderRequest(BaseModel):
    """接单请求"""
    estimated_completion_date: Optional[str] = Field(None, description="预计完成日期 YYYY-MM-DD")
    notes: Optional[str] = Field(None, max_length=500, description="备注")


class RejectOrderRequest(BaseModel):
    """拒单请求"""
    reason: str = Field(..., min_length=5, max_length=200, description="拒绝原因（必填）")
    reason_category: str = Field(..., description="原因分类：capacity/craft/price/other")


class OrderDetailResponse(BaseModel):
    """订单详情响应"""
    order_id: str
    design_id: str
    status: str
    total_price: float
    estimated_days: int
    user_id: str
    studio_id: Optional[str]
    studio_name: Optional[str]
    design_params: dict
    craft_check: dict
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[OrderSummary])
async def list_studio_orders(
    status_filter: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取工作室的订单列表

    Phase Q5.2: 工作室端订单列表

    TODO: 添加工作室身份验证，确保只能看到分配给自己的订单
    """
    # For now, get all orders (TODO: filter by studio_id from user authentication)
    stmt = select(Order).order_by(Order.created_at.desc())
    result = await session.execute(stmt)
    orders = result.scalars().all()

    # Filter by status if specified
    if status_filter:
        orders = [o for o in orders if o.status == status_filter]

    return [
        OrderSummary(
            order_id=o.order_id,
            design_id=o.design_id,
            status=o.status,
            total_price=o.total_price,
            estimated_days=o.estimated_days,
            created_at=o.created_at,
            design_params=o.design_params or {},
        )
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取订单详情

    TODO: 验证订单属于当前工作室
    """
    stmt = select(Order).where(Order.order_id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # Get studio name if assigned
    studio_name = None
    if order.studio_id:
        studio_stmt = select(Studio).where(Studio.studio_id == order.studio_id)
        studio_result = await session.execute(studio_stmt)
        studio = studio_result.scalar_one_or_none()
        if studio:
            studio_name = studio.name

    return OrderDetailResponse(
        order_id=order.order_id,
        design_id=order.design_id,
        status=order.status,
        total_price=order.total_price,
        estimated_days=order.estimated_days,
        user_id=order.user_id,
        studio_id=order.studio_id,
        studio_name=studio_name,
        design_params=order.design_params or {},
        craft_check=order.craft_check or {},
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/{order_id}/accept")
async def accept_order(
    order_id: str,
    request: AcceptOrderRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """工作室接单

    Phase Q5.2.1: 状态机迁移 已派单 → 制作中，current_load +1

    状态机规则：
    - 只能从 "已派单" 状态接单
    - 接单后状态变为 "制作中"
    - 工作室 current_load +1
    """
    # 查找订单
    stmt = select(Order).where(Order.order_id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # TODO: 验证订单分配给当前工作室

    # 状态机校验
    if order.status != "已派单":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单当前状态为「{order.status}」，无法接单。只能接收「已派单」状态的订单。"
        )

    # 状态迁移
    old_status = order.status
    order.status = "制作中"
    order.updated_at = datetime.utcnow()

    # 记录状态变更日志
    log = OrderLog(
        order_id=order_id,
        event_type="status_change",
        metadata={
            "from": old_status,
            "to": "制作中",
            "action": "accept",
            "accepted_by": current_user.user_id,
            "estimated_completion_date": request.estimated_completion_date,
            "notes": request.notes,
        }
    )
    session.add(log)

    # 更新工作室 current_load
    if order.studio_id:
        studio_stmt = select(Studio).where(Studio.studio_id == order.studio_id)
        studio_result = await session.execute(studio_stmt)
        studio = studio_result.scalar_one_or_none()

        if studio:
            studio.current_load = (studio.current_load or 0) + 1
            studio.updated_at = datetime.utcnow()

    await session.commit()

    return {
        "status": "success",
        "order_id": order_id,
        "new_status": "制作中",
        "message": "订单已接收，开始制作"
    }


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: str,
    request: RejectOrderRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """工作室拒单

    Phase Q5.2.2: 必填 reason，写 order_logs.metadata，自动重派

    状态机规则：
    - 只能从 "已派单" 状态拒单
    - 拒单后触发重新派单逻辑
    - current_load 不变（因为还没接单）
    """
    # 验证拒绝原因分类
    valid_categories = ["capacity", "craft", "price", "other"]
    if request.reason_category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的原因分类。有效值: {valid_categories}"
        )

    # 查找订单
    stmt = select(Order).where(Order.order_id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # TODO: 验证订单分配给当前工作室

    # 状态机校验
    if order.status != "已派单":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单当前状态为「{order.status}」，无法拒单。只能拒绝「已派单」状态的订单。"
        )

    # 记录拒单日志
    log = OrderLog(
        order_id=order_id,
        event_type="reject",
        metadata={
            "reason": request.reason,
            "reason_category": request.reason_category,
            "rejected_by": current_user.user_id,
            "previous_studio_id": order.studio_id,
        }
    )
    session.add(log)

    # 清除当前工作室分配
    old_studio_id = order.studio_id
    order.studio_id = None
    order.status = "待派单"  # 回到待派单状态，等待重新分配
    order.updated_at = datetime.utcnow()

    await session.commit()

    return {
        "status": "success",
        "order_id": order_id,
        "new_status": "待派单",
        "message": "订单已拒绝，将重新派单",
        "rejection_reason": request.reason,
        "previous_studio": old_studio_id,
    }


@router.post("/{order_id}/complete")
async def complete_order(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """工作室标记订单完成

    Phase Q5.2+: 制作中 → 已完成，current_load -1
    """
    stmt = select(Order).where(Order.order_id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 状态机校验
    if order.status != "制作中":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单当前状态为「{order.status}」，无法标记完成。只能完成「制作中」状态的订单。"
        )

    # 状态迁移
    old_status = order.status
    order.status = "已完成"
    order.updated_at = datetime.utcnow()

    # 记录日志
    log = OrderLog(
        order_id=order_id,
        event_type="status_change",
        metadata={
            "from": old_status,
            "to": "已完成",
            "action": "complete",
            "completed_by": current_user.user_id,
        }
    )
    session.add(log)

    # 释放工作室产能
    if order.studio_id:
        studio_stmt = select(Studio).where(Studio.studio_id == order.studio_id)
        studio_result = await session.execute(studio_stmt)
        studio = studio_result.scalar_one_or_none()

        if studio and studio.current_load > 0:
            studio.current_load -= 1
            studio.updated_at = datetime.utcnow()

    await session.commit()

    return {
        "status": "success",
        "order_id": order_id,
        "new_status": "已完成",
        "message": "订单已完成"
    }
