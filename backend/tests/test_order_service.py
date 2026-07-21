"""order_service 单元测试

覆盖目标：services/order/order_service.py 之前覆盖率 22%，状态机本身（state_machine.py）
已有测试，但 service 层（写库 + 写日志 + 释放容量 + metrics）的关键路径未覆盖。
本套测试用 aiosqlite in-memory 隔离运行，不依赖外部 PG/Redis。

覆盖路径：
- update_order_status: 合法转换 → 写库 + 写 OrderLog
- update_order_status: 非法转换 → 拒绝、不写 log
- update_order_status: 订单不存在 → 返回失败
- cancel_order: 可取消状态 → 状态变 CANCELLED + 写 log + 释放容量
- cancel_order: 不可取消状态（如 SHIPPED）→ 拒绝
- cancel_order: 订单不存在 → 失败
- pay_order: PENDING → CONFIRMED + 创建 log
- pay_order: 非 PENDING → 失败
- advance_production_status: DISPATCHED → PRODUCING → GLAZING ... → COMPLETED
- advance_production_status: 终态后无下一步
"""

from __future__ import annotations

from typing import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import Base, Order, OrderLog, Studio
from app.services.order.order_service import (
    advance_production_status,
    cancel_order,
    create_order_log,
    pay_order,
    update_order_status,
)
from app.services.order.state_machine import OrderStatus


# ---- 共享 fixture：每个测试拿全新的 in-memory DB -----------------------------


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """每个测试独立的 SQLite in-memory 异步 session。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _make_order(
    session: AsyncSession,
    *,
    status: OrderStatus = OrderStatus.PENDING,
    studio_id: str | None = None,
) -> Order:
    """快速创建一条订单（必填字段都给默认值，方便不同测试组合）。"""
    order = Order(
        user_id="user-1",
        session_id="session-1",
        option_id="version-1",
        studio_id=studio_id,
        status=status.value,
        idempotency_key=f"idem-{status.value}-{studio_id or 'none'}",
    )
    session.add(order)
    await session.flush()
    return order


async def _make_studio(session: AsyncSession, studio_id: str, current_load: int = 1) -> Studio:
    studio = Studio(
        studio_id=studio_id,
        name="测试工作室",
        location="景德镇",
        current_load=current_load,
        capacity=10,
    )
    session.add(studio)
    await session.flush()
    return studio


# ---- update_order_status -----------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_order_status_legal_transition_writes_log(session: AsyncSession):
    """合法转换：状态更新 + 写一条 OrderLog。"""
    order = await _make_order(session, status=OrderStatus.PENDING)

    result = await update_order_status(
        session, order.order_id, OrderStatus.CONFIRMED, operator="user-1", reason="paid"
    )

    assert result.success is True
    # 重新查库验证状态确实写入
    refreshed = (
        await session.execute(select(Order).where(Order.order_id == order.order_id))
    ).scalar_one()
    assert refreshed.status == OrderStatus.CONFIRMED.value

    # 必须有一条 log 记录这次转换
    logs = (
        await session.execute(select(OrderLog).where(OrderLog.order_id == order.order_id))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].from_status == OrderStatus.PENDING.value
    assert logs[0].to_status == OrderStatus.CONFIRMED.value
    assert logs[0].operator == "user-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_order_status_illegal_transition_rejected(session: AsyncSession):
    """非法转换被拒，且不写 log（避免污染审计）。"""
    order = await _make_order(session, status=OrderStatus.PENDING)

    result = await update_order_status(
        session, order.order_id, OrderStatus.SHIPPED, operator="user-1"
    )

    assert result.success is False
    refreshed = (
        await session.execute(select(Order).where(Order.order_id == order.order_id))
    ).scalar_one()
    assert refreshed.status == OrderStatus.PENDING.value  # 状态未变

    logs = (
        await session.execute(select(OrderLog).where(OrderLog.order_id == order.order_id))
    ).scalars().all()
    assert logs == []  # 失败转换不应写 log


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_order_status_missing_order_returns_failure(session: AsyncSession):
    result = await update_order_status(
        session, "nonexistent-order-id", OrderStatus.CONFIRMED
    )
    assert result.success is False
    assert "not found" in result.message.lower()


# ---- cancel_order ------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_order_releases_studio_capacity(session: AsyncSession):
    """取消订单时：状态变 CANCELLED + 写 log + 工作室 current_load -1。"""
    studio = await _make_studio(session, "studio-1", current_load=3)
    order = await _make_order(
        session, status=OrderStatus.PRODUCING, studio_id=studio.studio_id
    )

    result = await cancel_order(session, order.order_id, operator="user-1", reason="改主意了")

    assert result.success is True
    refreshed_order = (
        await session.execute(select(Order).where(Order.order_id == order.order_id))
    ).scalar_one()
    assert refreshed_order.status == OrderStatus.CANCELLED.value

    refreshed_studio = (
        await session.execute(select(Studio).where(Studio.studio_id == studio.studio_id))
    ).scalar_one()
    assert refreshed_studio.current_load == 2  # 3 - 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_order_blocked_for_uncancellable_status(session: AsyncSession):
    """SHIPPED 状态不能取消（已发货必须走退款流程）。"""
    order = await _make_order(session, status=OrderStatus.SHIPPED)

    result = await cancel_order(session, order.order_id)

    assert result.success is False
    assert "cannot be cancelled" in result.message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_order_missing_returns_failure(session: AsyncSession):
    result = await cancel_order(session, "no-such-order")
    assert result.success is False


# ---- pay_order ---------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pay_order_pending_to_confirmed(session: AsyncSession):
    order = await _make_order(session, status=OrderStatus.PENDING)

    result = await pay_order(session, order.order_id, payment_method="alipay")

    assert result.success is True
    refreshed = (
        await session.execute(select(Order).where(Order.order_id == order.order_id))
    ).scalar_one()
    assert refreshed.status == OrderStatus.CONFIRMED.value

    # 应有一条 mock 支付的 log
    logs = (
        await session.execute(select(OrderLog).where(OrderLog.order_id == order.order_id))
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].operator == "payment_mock"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pay_order_rejects_non_pending(session: AsyncSession):
    """已发货订单再点支付应被拒绝（防重复扣款的最小后端守卫）。"""
    order = await _make_order(session, status=OrderStatus.SHIPPED)
    result = await pay_order(session, order.order_id)
    assert result.success is False


# ---- advance_production_status ----------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_advance_production_walks_through_pipeline(session: AsyncSession):
    """从 DISPATCHED 一路推进到 SHIPPING_PENDING，每步状态正确。"""
    order = await _make_order(session, status=OrderStatus.DISPATCHED)

    expected = [
        OrderStatus.PRODUCING,
        OrderStatus.GLAZING,
        OrderStatus.FIRING,
        OrderStatus.COOLING,
        OrderStatus.QC,
        OrderStatus.COMPLETED,
        OrderStatus.SHIPPING_PENDING,
    ]
    for next_status in expected:
        result = await advance_production_status(session, order.order_id)
        assert result.success is True, f"推进到 {next_status} 失败: {result.message}"
        refreshed = (
            await session.execute(select(Order).where(Order.order_id == order.order_id))
        ).scalar_one()
        assert refreshed.status == next_status.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_advance_production_no_next_after_terminal(session: AsyncSession):
    """SHIPPING_PENDING 之后由发货流程接管，advance 应返回失败。"""
    order = await _make_order(session, status=OrderStatus.SHIPPING_PENDING)
    result = await advance_production_status(session, order.order_id)
    assert result.success is False
    assert "no next status" in result.message.lower()


# ---- create_order_log 直接测试（兜底覆盖 from_status=None 分支）---------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_order_log_with_none_from_status(session: AsyncSession):
    """初始建单时 from_status=None 应被允许（标记初始状态写入）。"""
    order = await _make_order(session, status=OrderStatus.PENDING)

    log = await create_order_log(
        session,
        order.order_id,
        from_status=None,
        to_status=OrderStatus.PENDING,
        operator="system",
        reason="order created",
    )

    assert log.from_status is None
    assert log.to_status == OrderStatus.PENDING.value
