"""Logistics API - Shipping tracking and delivery confirmation"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.time import utcnow

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Order, OrderLog
from app.services.logistics import (
    get_provider,
    LogisticsStatus,
    TrackingEvent as ProviderEvent,
)


router = APIRouter(prefix="/logistics", tags=["logistics"])


class ShippingInfo(BaseModel):
    """物流信息"""
    tracking_number: str = Field(..., description="快递单号")
    carrier: str = Field(..., description="快递公司（如：顺丰、圆通）")
    estimated_delivery_date: Optional[str] = Field(None, description="预计送达日期 YYYY-MM-DD")
    notes: Optional[str] = Field(None, max_length=500, description="发货备注")


class TrackingEvent(BaseModel):
    """物流轨迹事件"""
    time: str
    status: str
    description: str
    location: Optional[str] = None


class TrackingResponse(BaseModel):
    """物流追踪响应"""
    order_id: str
    tracking_number: str
    carrier: str
    status: str  # shipped / in_transit / out_for_delivery / delivered
    events: List[TrackingEvent]
    estimated_delivery_date: Optional[str]


class ConfirmDeliveryRequest(BaseModel):
    """确认收货请求"""
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分 1-5 星")
    comment: Optional[str] = Field(None, max_length=500, description="评价")


@router.post("/orders/{order_id}/ship")
async def create_shipping(
    order_id: str,
    shipping_info: ShippingInfo,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    工作室录入物流信息

    Phase Q6.2.1: 物流单号录入

    权限: 工作室（TODO: 添加工作室身份验证）
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

    # 验证操作者：必须是工作室账号，且订单派发给该工作室
    if current_user.role != "studio" or not current_user.studio_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅工作室账号可发货"
        )
    if order.studio_id != current_user.studio_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订单"
        )

    # 验证订单状态（只能从已完成状态发货）
    if order.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态为 {order.status}，无法发货。只能从 completed 状态发货。"
        )

    # 更新订单状态
    order.status = "shipped"
    order.updated_at = utcnow()

    # 物流信息记录到 OrderLog.extra_data
    shipping_log = OrderLog(
        order_id=order_id,
        from_status="completed",
        to_status="shipped",
        operator=current_user.user_id,
        reason="工作室发货",
        extra_data={
            "type": "shipping",
            "tracking_number": shipping_info.tracking_number,
            "carrier": shipping_info.carrier,
            "estimated_delivery_date": shipping_info.estimated_delivery_date,
            "notes": shipping_info.notes,
            "shipped_at": utcnow().isoformat(),
        }
    )
    session.add(shipping_log)

    await session.commit()

    return {
        "status": "success",
        "order_id": order_id,
        "tracking_number": shipping_info.tracking_number,
        "carrier": shipping_info.carrier,
        "message": "物流信息已录入，订单已发货"
    }


@router.get("/orders/{order_id}/tracking", response_model=TrackingResponse)
async def get_tracking_info(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    查询物流追踪信息

    Phase Q6.2.2: 物流追踪查询

    TODO: 集成第三方物流 API（如快递100、菜鸟）
    """
    # 查找订单
    stmt = select(Order).where(
        Order.order_id == order_id,
        Order.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 查找物流信息（从 OrderLog 中读取发货记录）
    stmt = select(OrderLog).where(
        OrderLog.order_id == order_id,
        OrderLog.to_status == "shipped"
    ).order_by(OrderLog.created_at.desc())

    result = await session.execute(stmt)
    shipping_log = result.scalar_one_or_none()

    if not shipping_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单尚未发货"
        )

    tracking_number = shipping_log.extra_data.get("tracking_number")
    carrier = shipping_log.extra_data.get("carrier")

    # 通过 Provider 抽象查询真实/Mock 轨迹
    # 真实快递接入时只需在 services/logistics 增加 Provider, 此处零改动
    provider = get_provider(carrier)
    try:
        result = await provider.query_tracking(tracking_number or "")
    except Exception as e:
        # 第三方查询失败 → 502 给前端, 但保留 carrier/tracking_number 信息
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"物流查询服务暂时不可用: {type(e).__name__}",
        )

    # Provider 标准化状态 → 旧 API 字符串状态 (向后兼容前端)
    logistics_status = result.status.value

    # 若订单已确认收货, 用订单实际状态覆盖 (Provider 可能滞后)
    if order.status == "delivered" and result.status != LogisticsStatus.DELIVERED:
        logistics_status = "delivered"
        result.events.append(
            ProviderEvent(
                time=utcnow(),
                status=LogisticsStatus.DELIVERED,
                description="快件已签收",
                location="用户地址",
            )
        )

    return TrackingResponse(
        order_id=order_id,
        tracking_number=tracking_number,
        carrier=carrier,
        status=logistics_status,
        events=[
            TrackingEvent(
                time=ev.time.isoformat(),
                status=ev.status.value,
                description=ev.description,
                location=ev.location,
            )
            for ev in result.events
        ],
        estimated_delivery_date=result.estimated_delivery_date
            or shipping_log.extra_data.get("estimated_delivery_date"),
    )


@router.post("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(
    order_id: str,
    request: ConfirmDeliveryRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    用户确认收货

    Phase Q6.2.3: 签收确认

    流程:
    1. 验证订单属于当前用户
    2. 验证订单状态（shipped）
    3. 更新订单状态为 delivered
    4. 可选：记录评价
    """
    # 查找订单
    stmt = select(Order).where(
        Order.order_id == order_id,
        Order.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 验证订单状态
    if order.status != "shipped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态为 {order.status}，无法确认收货。只能从 shipped 状态确认收货。"
        )

    # 更新订单状态
    order.status = "delivered"
    order.updated_at = utcnow()

    # 记录确认收货日志
    delivery_log = OrderLog(
        order_id=order_id,
        from_status="shipped",
        to_status="delivered",
        operator=current_user.user_id,
        reason="用户确认收货",
        extra_data={
            "rating": request.rating,
            "comment": request.comment,
            "confirmed_at": utcnow().isoformat(),
        }
    )
    session.add(delivery_log)

    await session.commit()

    return {
        "status": "success",
        "order_id": order_id,
        "new_status": "delivered",
        "message": "已确认收货"
    }


@router.get("/orders/{order_id}/delivery-info")
async def get_delivery_info(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    获取收货信息（收货地址、联系人）

    用于工作室查看配送地址
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

    # TODO: 验证权限（工作室或用户本人）

    return {
        "order_id": order_id,
        "shipping_name": order.shipping_name,
        "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address,
    }
