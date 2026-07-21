"""Orders API Router"""

from typing import Annotated, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.entities import Order as OrderModel, OrderLog as OrderLogModel
from app.services.order import (
    OrderStatus, get_status_display_info,
    update_order_status, cancel_order, pay_order, get_order_logs
)
from app.services.order.state_machine import is_terminal_status, get_status_timeline
from app.services.workorder import generate_workorder_html, render_workorder_pdf
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
    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)


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
    
    # Get total count（PK 字段名是 order_id，不是 id）
    count_result = await session.execute(
        select(OrderModel.order_id).where(OrderModel.user_id == current_user.user_id)
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


@router.get("/statuses")
async def list_statuses():
    """List all available order statuses.

    路由顺序：必须在 `/{order_id}` 之前，否则会被参数化路由抢先匹配为 order_id="statuses"。
    """
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


def _build_workorder_dict(order: OrderModel, current_user: UserInfo) -> dict:
    """组装工单 dict（PDF/HTML 通用）。"""
    return {
        "order_id": order.order_id,
        "design_name": getattr(order, "design_name", None) or order.option_id[:8],
        "studio_name": getattr(order, "studio_id", None) or "中央工作室",
        "studio_master": "陶语 · 派单师傅",
        "deadline": "约 7 - 10 天",
        "glb_url": f"designs/{order.option_id}.glb",
        "thumbnail_url": f"thumbnails/{order.option_id}.png",
        "craft_check": {"passed": True, "auto_fixed": False, "issues": []},
        "design_params": {
            "shape": "vase",
            "glaze_color": "celadon",
            "size": "medium",
            "material": "porcelain_white",
        },
        "price": order.total_price or 0,
        "estimated_days": 9,
        "material": "porcelain_white",
        "dimensions_mm": {"height": 180, "width": 100, "depth": 100},
        "ship_to": {
            "name": (current_user.phone if current_user else "—"),
            "phone": current_user.phone if current_user else "—",
            "address": order.shipping_address or "—",
        },
    }


@router.get("/{order_id}/workorder.html")
async def get_workorder_html(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """渲染工单 HTML（浏览器可直接打开打印）。"""
    result = await session.execute(
        select(OrderModel).where(
            OrderModel.order_id == order_id,
            OrderModel.user_id == current_user.user_id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    html = generate_workorder_html(_build_workorder_dict(order, current_user))
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/{order_id}/workorder.pdf")
async def get_workorder_pdf(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """渲染工单 PDF；环境无 weasyprint 时退化为 HTML。"""
    result = await session.execute(
        select(OrderModel).where(
            OrderModel.order_id == order_id,
            OrderModel.user_id == current_user.user_id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    payload = render_workorder_pdf(_build_workorder_dict(order, current_user))
    # 简单嗅探：PDF 以 %PDF- 开头
    if payload.startswith(b"%PDF"):
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="workorder_{order_id}.pdf"'
            },
        )
    # weasyprint 不可用，返回 HTML
    return Response(content=payload, media_type="text/html; charset=utf-8")
