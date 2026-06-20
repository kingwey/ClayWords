"""Orders API Router"""

from typing import Annotated, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.entities import Order as OrderModel, OrderLog as OrderLogModel
from app.services.order import (
    OrderStatus, get_status_display_info, 
    update_order_status, cancel_order, pay_order, get_order_logs
)
from app.services.order.state_machine import is_terminal_status, get_status_timeline
from app.api.auth import get_current_user, UserInfo

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    session_id: str
    option_id: str
    studio_id: Optional[str]
    status: str
    status_label: str
    total_price: float
    shipping_address: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class OrderDetailResponse(BaseModel):
    order: OrderResponse
    timeline: list[dict]
    can_cancel: bool
    can_refund: bool


class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = ""


class OrderLogResponse(BaseModel):
    id: str
    from_status: Optional[str]
    to_status: str
    operator: str
    reason: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=OrderListResponse)
async def list_orders(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    status_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List orders for current user."""
    query = select(OrderModel).where(OrderModel.user_id == current_user.user_id)
    
    if status_filter:
        query = query.where(OrderModel.status == status_filter)
    
    # Get total count
    count_result = await session.execute(
        select(OrderModel.id).where(OrderModel.user_id == current_user.user_id)
    )
    total = len(count_result.scalars().all())
    
    # Get paginated results
    query = query.order_by(OrderModel.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    orders = result.scalars().all()
    
    return OrderListResponse(
        orders=[
            OrderResponse(
                order_id=o.order_id,
                user_id=o.user_id,
                session_id=o.session_id,
                option_id=o.option_id,
                studio_id=o.studio_id,
                status=o.status,
                status_label=get_status_display_info(OrderStatus(o.status))["label"],
                total_price=o.total_price or 0,
                shipping_address=o.shipping_address or "",
                created_at=o.created_at.isoformat() if o.created_at else "",
                updated_at=o.updated_at.isoformat() if o.updated_at else ""
            )
            for o in orders
        ],
        total=total
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get order detail with timeline."""
    result = await session.execute(
        select(OrderModel).where(
            OrderModel.order_id == order_id,
            OrderModel.user_id == current_user.user_id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    # Get logs
    logs_result = await session.execute(
        select(OrderLogModel)
        .where(OrderLogModel.order_id == order_id)
        .order_by(OrderLogModel.created_at)
    )
    logs = logs_result.scalars().all()
    
    current_status = OrderStatus(order.status)
    
    return OrderDetailResponse(
        order=OrderResponse(
            order_id=order.order_id,
            user_id=order.user_id,
            session_id=order.session_id,
            option_id=order.option_id,
            studio_id=order.studio_id,
            status=order.status,
            status_label=get_status_display_info(current_status)["label"],
            total_price=order.total_price or 0,
            shipping_address=order.shipping_address or "",
            created_at=order.created_at.isoformat() if order.created_at else "",
            updated_at=order.updated_at.isoformat() if order.updated_at else ""
        ),
        timeline=[
            {
                "status": log.to_status,
                "label": get_status_display_info(OrderStatus(log.to_status))["label"],
                "color": get_status_display_info(OrderStatus(log.to_status))["color"],
                "reason": log.reason or "",
                "operator": log.operator,
                "created_at": log.created_at.isoformat() if log.created_at else ""
            }
            for log in logs
        ],
        can_cancel=current_status not in [OrderStatus.DELIVERED, OrderStatus.REFUNDED, OrderStatus.CANCELLED],
        can_refund=current_status in [OrderStatus.DELIVERED]
    )


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def pay_order_endpoint(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mock payment for an order."""
    result = await session.execute(
        select(OrderModel).where(
            OrderModel.order_id == order_id,
            OrderModel.user_id == current_user.user_id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    trans_result = await pay_order(session, order_id, "mock")
    
    if not trans_result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=trans_result.message)
    
    await session.refresh(order)
    current_status = OrderStatus(order.status)
    
    return OrderResponse(
        order_id=order.order_id,
        user_id=order.user_id,
        session_id=order.session_id,
        option_id=order.option_id,
        studio_id=order.studio_id,
        status=order.status,
        status_label=get_status_display_info(current_status)["label"],
        total_price=order.total_price or 0,
        shipping_address=order.shipping_address or "",
        created_at=order.created_at.isoformat() if order.created_at else "",
        updated_at=order.updated_at.isoformat() if order.updated_at else ""
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_endpoint(
    order_id: str,
    reason: str = "",
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel an order."""
    result = await session.execute(
        select(OrderModel).where(
            OrderModel.order_id == order_id,
            OrderModel.user_id == current_user.user_id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    trans_result = await cancel_order(session, order_id, "user", reason)
    
    if not trans_result.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=trans_result.message)
    
    await session.refresh(order)
    current_status = OrderStatus(order.status)
    
    return OrderResponse(
        order_id=order.order_id,
        user_id=order.user_id,
        session_id=order.session_id,
        option_id=order.option_id,
        studio_id=order.studio_id,
        status=order.status,
        status_label=get_status_display_info(current_status)["label"],
        total_price=order.total_price or 0,
        shipping_address=order.shipping_address or "",
        created_at=order.created_at.isoformat() if order.created_at else "",
        updated_at=order.updated_at.isoformat() if order.updated_at else ""
    )


@router.get("/statuses")
async def list_statuses():
    """List all available order statuses."""
    timeline = get_status_timeline()
    return {
        "statuses": [
            {
                "value": s.value,
                "label": get_status_display_info(s)["label"],
                "color": get_status_display_info(s)["color"],
                "is_terminal": is_terminal_status(s)
            }
            for s in timeline
        ]
    }
