"""Order Service - Order management and state transitions"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.entities import Order as OrderModel, OrderLog as OrderLogModel
from app.core.time import utcnow
from .state_machine import (
    OrderStatus, validate_transition, transition,
    TransitionResult, is_terminal_status, STATUS_INFO
)


async def create_order_log(
    db: AsyncSession,
    order_id: str,
    from_status: Optional[OrderStatus],
    to_status: OrderStatus,
    operator: str,
    reason: str = "",
    extra_data: dict = None,
) -> OrderLogModel:
    """Create an order log entry.

    NOTE: 历史代码中曾使用 `metadata` 形参，但 SQLAlchemy 的 DeclarativeBase 已占用
    该属性，且 OrderLog 模型的字段名是 `extra_data`。此处统一更名以避免运行时
    `TypeError: 'metadata' is an invalid keyword argument for OrderLog`。
    """
    log = OrderLogModel(
        id=str(uuid.uuid4()),
        order_id=order_id,
        from_status=from_status.value if from_status else None,
        to_status=to_status.value,
        operator=operator,
        reason=reason,
        extra_data=extra_data or {},
    )
    db.add(log)
    await db.flush()
    return log


async def update_order_status(
    db: AsyncSession,
    order_id: str,
    new_status: OrderStatus,
    operator: str = "system",
    reason: str = "",
    extra_data: dict = None,
) -> TransitionResult:
    """
    Update order status with validation.
    
    Returns TransitionResult with success status.
    """
    # Get current order
    result = await db.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        return TransitionResult(
            success=False,
            from_status=None,
            to_status=new_status,
            message=f"Order {order_id} not found"
        )
    
    current_status = OrderStatus(order.status)
    
    # Validate transition
    trans_result = transition(current_status, new_status)
    
    if not trans_result.success:
        return trans_result
    
    # Update order status
    order.status = new_status.value
    order.updated_at = utcnow()
    
    # Add log entry
    await create_order_log(
        db, order_id, current_status, new_status, operator, reason, extra_data
    )
    
    await db.flush()
    
    return trans_result


async def get_order_logs(db: AsyncSession, order_id: str) -> list[OrderLogModel]:
    """Get all logs for an order."""
    result = await db.execute(
        select(OrderLogModel)
        .where(OrderLogModel.order_id == order_id)
        .order_by(OrderLogModel.created_at)
    )
    return list(result.scalars().all())


async def cancel_order(
    db: AsyncSession,
    order_id: str,
    operator: str = "user",
    reason: str = ""
) -> TransitionResult:
    """
    Cancel an order.
    
    Validates current status allows cancellation.
    """
    from app.services.dispatch import release_studio_capacity
    
    result = await db.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        return TransitionResult(
            success=False,
            from_status=None,
            to_status=None,
            message=f"Order {order_id} not found"
        )
    
    current_status = OrderStatus(order.status)
    
    # Check if cancellable
    from .state_machine import is_cancellable
    if not is_cancellable(current_status):
        return TransitionResult(
            success=False,
            from_status=current_status,
            to_status=OrderStatus.CANCELLED,
            message=f"Order in {current_status.value} cannot be cancelled"
        )
    
    # Attempt transition
    trans_result = transition(current_status, OrderStatus.CANCELLED)
    
    if not trans_result.success:
        return trans_result
    
    # Update status
    order.status = OrderStatus.CANCELLED.value
    order.updated_at = utcnow()
    
    # Create log
    await create_order_log(
        db, order_id, current_status, OrderStatus.CANCELLED,
        operator, reason or "User cancelled order"
    )
    
    # Release studio capacity if was dispatched
    if order.studio_id:
        await release_studio_capacity(db, order.studio_id)

    await db.flush()

    # Metrics: 记录订单取消
    from app.core.metrics import metrics
    metrics.increment_order("cancelled")

    return trans_result


async def pay_order(
    db: AsyncSession,
    order_id: str,
    payment_method: str = "mock"
) -> TransitionResult:
    """
    Mock payment for an order.
    
    In production, would integrate with payment gateway.
    """
    result = await db.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        return TransitionResult(
            success=False,
            from_status=None,
            to_status=None,
            message=f"Order {order_id} not found"
        )
    
    current_status = OrderStatus(order.status)
    
    # For mock, transition directly from pending to confirmed (payment complete)
    if current_status == OrderStatus.PENDING:
        return await update_order_status(
            db, order_id, OrderStatus.CONFIRMED,
            "payment_mock",
            f"Payment received via {payment_method}"
        )
    
    return TransitionResult(
        success=False,
        from_status=current_status,
        to_status=None,
        message=f"Cannot pay order in {current_status.value} status"
    )


def get_status_display_info(status: OrderStatus) -> dict:
    """Get display info for a status."""
    return STATUS_INFO.get(status, {"label": status.value, "color": "#909399", "icon": "info"})


async def advance_production_status(
    db: AsyncSession,
    order_id: str,
    operator: str = "system"
) -> TransitionResult:
    """
    Advance order to next production status.
    
    Used by worker to progress orders through production pipeline.
    """
    result = await db.execute(
        select(OrderModel).where(OrderModel.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        return TransitionResult(
            success=False,
            from_status=None,
            to_status=None,
            message=f"Order {order_id} not found"
        )
    
    current_status = OrderStatus(order.status)
    
    # Define production flow
    production_flow = {
        OrderStatus.DISPATCHED: OrderStatus.PRODUCING,
        OrderStatus.PRODUCING: OrderStatus.GLAZING,
        OrderStatus.GLAZING: OrderStatus.FIRING,
        OrderStatus.FIRING: OrderStatus.COOLING,
        OrderStatus.COOLING: OrderStatus.QC,
        OrderStatus.QC: OrderStatus.COMPLETED,
        OrderStatus.COMPLETED: OrderStatus.SHIPPING_PENDING,
    }
    
    next_status = production_flow.get(current_status)
    
    if not next_status:
        return TransitionResult(
            success=False,
            from_status=current_status,
            to_status=None,
            message=f"No next status after {current_status.value}"
        )
    
    return await update_order_status(
        db, order_id, next_status, operator,
        f"Production advanced: {current_status.value} -> {next_status.value}"
    )
