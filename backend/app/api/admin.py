"""Admin API - 平台管理员订单干预

权限: 全部端点要求 role=admin (require_role 守卫)。
覆盖:
- GET  /admin/orders            列出全部订单 (跨用户/跨工作室)
- GET  /admin/orders/{id}       订单详情 (含日志, 不限 user_id)
- POST /admin/orders/{id}/cancel    强制取消 (释放工作室容量 + 退款链路)
- POST /admin/orders/{id}/refund    强制退款 (绕过 user_id 限制)
- POST /admin/orders/{id}/redispatch  重派: 释放当前工作室 + 重新跑派单器

设计要点:
- 所有动作写 OrderLog, operator=admin:<user_id>, 留下完整审计
- 业务埋点 orders_total{admin_*} 可观察管理员动作频次
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.api.auth import UserInfo, require_role
from app.db.session import get_session
from app.models.entities import Order as OrderModel, OrderLog as OrderLogModel
from app.services.order import (
    OrderStatus,
    cancel_order as service_cancel_order,
    get_status_display_info,
    is_cancellable,
    can_refund,
)
from app.services.dispatch import (
    dispatch_to_studio,
    release_studio_capacity,
)
from app.core.time import utcnow


router = APIRouter(prefix="/admin", tags=["admin"])

# admin 守卫: 所有端点共用
admin_required = Depends(require_role("admin"))


# ---------- DTO ----------

class AdminOrderItem(BaseModel):
    order_id: str
    user_id: str
    session_id: str
    option_id: str
    studio_id: Optional[str]
    status: str
    status_label: str
    status_color: str
    total_price: float
    shipping_address: str
    created_at: str
    updated_at: str
    can_cancel: bool
    can_refund: bool


class AdminOrderListResponse(BaseModel):
    orders: list[AdminOrderItem]
    total: int
    limit: int
    offset: int


class AdminOrderLog(BaseModel):
    from_status: Optional[str]
    to_status: str
    operator: str
    reason: str
    created_at: str
    extra_data: dict = {}


class AdminOrderDetailResponse(BaseModel):
    order: AdminOrderItem
    logs: list[AdminOrderLog]


class AdminCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="管理员取消原因")


class AdminRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="管理员退款原因")
    amount: Optional[float] = Field(None, gt=0, description="退款金额; 不填则全额")


class AdminRedispatchRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="重派原因")


# ---------- Helpers ----------

def _to_item(o: OrderModel) -> AdminOrderItem:
    info = get_status_display_info(OrderStatus(o.status))
    current = OrderStatus(o.status)
    return AdminOrderItem(
        order_id=o.order_id,
        user_id=o.user_id,
        session_id=o.session_id,
        option_id=o.option_id,
        studio_id=o.studio_id,
        status=o.status,
        status_label=info["label"],
        status_color=info["color"],
        total_price=o.total_price or 0,
        shipping_address=o.shipping_address or "",
        created_at=o.created_at.isoformat() if o.created_at else "",
        updated_at=o.updated_at.isoformat() if o.updated_at else "",
        can_cancel=is_cancellable(current),
        can_refund=can_refund(current),
    )


async def _audit_log(
    session: AsyncSession,
    order_id: str,
    from_status: Optional[str],
    to_status: str,
    admin_id: str,
    reason: str,
    extra_data: Optional[dict] = None,
) -> None:
    """统一管理员审计日志入口。operator 写成 admin:<user_id> 区分系统/工作室操作。"""
    session.add(OrderLogModel(
        order_id=order_id,
        from_status=from_status,
        to_status=to_status,
        operator=f"admin:{admin_id}",
        reason=reason,
        extra_data=extra_data or {},
    ))


# ---------- Endpoints ----------

@router.get("/orders", response_model=AdminOrderListResponse)
async def list_all_orders(
    current_user: UserInfo = admin_required,
    session: AsyncSession = Depends(get_session),
    status_filter: Optional[str] = Query(None, description="按状态过滤"),
    user_id: Optional[str] = Query(None, description="按用户 ID 过滤"),
    studio_id: Optional[str] = Query(None, description="按工作室 ID 过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索 (order_id / user_id 前缀)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """跨用户/跨工作室的订单列表。"""
    query = select(OrderModel)
    count_query = select(func.count(OrderModel.order_id))

    if status_filter:
        query = query.where(OrderModel.status == status_filter)
        count_query = count_query.where(OrderModel.status == status_filter)
    if user_id:
        query = query.where(OrderModel.user_id == user_id)
        count_query = count_query.where(OrderModel.user_id == user_id)
    if studio_id:
        query = query.where(OrderModel.studio_id == studio_id)
        count_query = count_query.where(OrderModel.studio_id == studio_id)
    if keyword:
        like = f"{keyword}%"
        cond = or_(
            OrderModel.order_id.like(like),
            OrderModel.user_id.like(like),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(OrderModel.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    orders = result.scalars().all()

    return AdminOrderListResponse(
        orders=[_to_item(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}", response_model=AdminOrderDetailResponse)
async def get_order_detail(
    order_id: str,
    current_user: UserInfo = admin_required,
    session: AsyncSession = Depends(get_session),
):
    """订单详情 + 完整状态日志 (不按 user_id 过滤)。"""
    result = await session.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="订单不存在")

    logs_result = await session.execute(
        select(OrderLogModel)
        .where(OrderLogModel.order_id == order_id)
        .order_by(OrderLogModel.created_at)
    )
    logs = logs_result.scalars().all()

    return AdminOrderDetailResponse(
        order=_to_item(order),
        logs=[
            AdminOrderLog(
                from_status=log.from_status,
                to_status=log.to_status,
                operator=log.operator,
                reason=log.reason or "",
                created_at=log.created_at.isoformat() if log.created_at else "",
                extra_data=log.extra_data or {},
            )
            for log in logs
        ],
    )


@router.post("/orders/{order_id}/cancel", response_model=AdminOrderItem)
async def admin_cancel_order(
    order_id: str,
    request: AdminCancelRequest,
    current_user: UserInfo = admin_required,
    session: AsyncSession = Depends(get_session),
):
    """管理员强制取消订单。

    走标准 service_cancel_order 路径, 自动释放工作室容量。
    审计日志在 service 内部已写, 这里再写一条 admin 标记便于检索。
    """
    result = await session.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="订单不存在")

    trans = await service_cancel_order(
        session,
        order_id,
        operator=f"admin:{current_user.user_id}",
        reason=f"[管理员] {request.reason}",
    )
    if not trans.success:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=trans.message)

    # 业务埋点
    from app.core.metrics import metrics
    metrics.increment_order("admin_cancelled")

    await session.commit()
    await session.refresh(order)
    return _to_item(order)


@router.post("/orders/{order_id}/refund", response_model=AdminOrderItem)
async def admin_refund_order(
    order_id: str,
    request: AdminRefundRequest,
    current_user: UserInfo = admin_required,
    session: AsyncSession = Depends(get_session),
):
    """管理员强制退款。

    流程:
    1. 状态机校验 (can_refund: cancelled / shipped / delivered)
    2. 状态迁移到 refunding (实际打款由对账线下处理 / payment_service 后续接入)
    3. 写审计日志 + 业务埋点
    """
    result = await session.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="订单不存在")

    current = OrderStatus(order.status)
    if not can_refund(current):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态 {current.value} 不允许退款",
        )

    refund_amount = request.amount or order.total_price
    if refund_amount > (order.total_price or 0):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="退款金额超过订单金额"
        )

    # 已签收订单需先经 cancelled 才能进 refunding (state machine 约束)
    # 这里直接迁 cancelled → refunding (允许 admin 跨步)
    if current == OrderStatus.DELIVERED or current == OrderStatus.SHIPPED:
        order.status = OrderStatus.CANCELLED.value
        await _audit_log(
            session,
            order_id,
            current.value,
            OrderStatus.CANCELLED.value,
            current_user.user_id,
            f"[管理员退款步骤1] {request.reason}",
            {"refund_amount": refund_amount},
        )
        current = OrderStatus.CANCELLED

    order.status = OrderStatus.REFUNDING.value
    order.updated_at = utcnow()
    await _audit_log(
        session,
        order_id,
        current.value,
        OrderStatus.REFUNDING.value,
        current_user.user_id,
        f"[管理员退款] {request.reason}",
        {"refund_amount": refund_amount, "admin_initiated": True},
    )

    from app.core.metrics import metrics
    metrics.increment_order("admin_refunding")
    metrics.increment_payment("admin_refund_initiated")

    await session.commit()
    await session.refresh(order)
    return _to_item(order)


@router.post("/orders/{order_id}/redispatch", response_model=AdminOrderItem)
async def admin_redispatch_order(
    order_id: str,
    request: AdminRedispatchRequest,
    current_user: UserInfo = admin_required,
    session: AsyncSession = Depends(get_session),
):
    """管理员重派订单。

    场景: 工作室长时间未接单 / 工作室关停 / 派单算法历史选错。
    流程:
    1. 必须是 dispatched 或更早 (producing 之后已开工, 重派会造成实物损失)
    2. 释放当前 studio_id 的容量
    3. 清空 studio_id, 重跑派单器
    4. 写审计日志
    """
    result = await session.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="订单不存在")

    current = OrderStatus(order.status)
    redispatchable = {
        OrderStatus.DISPATCHED,
        OrderStatus.CONFIRMED,
        OrderStatus.PENDING,
    }
    if current not in redispatchable:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态 {current.value} 不允许重派 (已开工/已发货/已完结)",
        )

    old_studio = order.studio_id

    # 释放当前工作室容量
    if old_studio:
        await release_studio_capacity(session, old_studio)
        order.studio_id = None
        await session.flush()

    # 重跑派单器
    dispatch_result = await dispatch_to_studio(
        session,
        order_id=order_id,
        option_id=order.option_id,
        session_id=order.session_id,
    )

    await _audit_log(
        session,
        order_id,
        current.value,
        current.value,  # 状态不变, 只是改 studio_id
        current_user.user_id,
        f"[管理员重派] {request.reason}",
        {
            "old_studio_id": old_studio,
            "new_studio_id": dispatch_result.studio_id,
            "dispatched": dispatch_result.dispatched,
            "score": dispatch_result.score,
            "reason_dispatch": dispatch_result.reason,
        },
    )

    from app.core.metrics import metrics
    metrics.increment_order("admin_redispatched")
    metrics.increment_dispatch("admin_redispatch")

    await session.commit()
    await session.refresh(order)
    return _to_item(order)
