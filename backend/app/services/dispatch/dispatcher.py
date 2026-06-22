"""Dispatch Service - Studio selection and order dispatching"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.entities import Studio, Order, Design, DesignVersion
from .scoring import StudioInfo, DesignParams, score_studio, rank_studios
from .policy import dispatch_order, DispatchResult, DISPATCH_THRESHOLD


async def get_studio_info(db: AsyncSession, studio_id: str) -> Optional[StudioInfo]:
    """Get studio info by ID."""
    result = await db.execute(
        select(Studio).where(Studio.studio_id == studio_id)
    )
    studio = result.scalar_one_or_none()
    if not studio:
        return None

    return StudioInfo(
        studio_id=studio.studio_id,
        name=studio.name,
        specialties=studio.specialties or [],
        capacity=studio.capacity or 0,
        current_load=studio.current_load or 0,
        rating=studio.rating or 4.0,
        price_range_min=studio.price_range_min or 0,
        price_range_max=studio.price_range_max or 0,
        estimated_days=studio.estimated_days or 7,
        location=studio.location or ""
    )


async def get_all_available_studios(db: AsyncSession) -> list[StudioInfo]:
    """Get all studios with available capacity.

    优化：硬约束（容量、评分）下推到 SQL 层。100+ 工作室时避免全表 + Python 过滤。
    """
    stmt = (
        select(Studio)
        .where(Studio.current_load < Studio.capacity)
        .where(Studio.rating >= 4.0)
        .order_by(Studio.rating.desc(), Studio.current_load.asc())
        .limit(50)
    )
    result = await db.execute(stmt)
    studios = result.scalars().all()

    return [
        StudioInfo(
            studio_id=s.studio_id,
            name=s.name,
            specialties=s.specialties or [],
            capacity=s.capacity or 0,
            current_load=s.current_load or 0,
            rating=s.rating or 4.0,
            price_range_min=s.price_range_min or 0,
            price_range_max=s.price_range_max or 0,
            estimated_days=s.estimated_days or 7,
            location=s.location or ""
        )
        for s in studios
    ]


def build_design_params_from_option(option_id: str, design_price: float) -> DesignParams:
    """
    Build design params from order option.

    Simplified version - in production would parse actual design params.
    """
    return DesignParams(
        material="porcelain_white",
        category="vessel",
        price_range=(design_price * 0.8, design_price * 1.2)
    )


async def dispatch_to_studio(
    db: AsyncSession,
    order_id: str,
    option_id: str,
    session_id: str
) -> DispatchResult:
    """
    Dispatch order to best available studio.

    This is the main dispatch entry point called after order confirmation.

    并发安全：原子 UPDATE 锁定容量（current_load < capacity），避免多 worker 抢单
    超卖工作室容量。若占位失败，回退到下一候选；最坏情况标记需人工派单。
    """
    # Get design info
    version_result = await db.execute(
        select(DesignVersion).where(DesignVersion.version_id == option_id)
    )
    version = version_result.scalar_one_or_none()

    if not version:
        return DispatchResult(
            dispatched=False,
            studio_id=None,
            studio_name=None,
            score=0,
            reason="Design option not found",
            requires_manual=True
        )

    design_result = await db.execute(
        select(Design).where(Design.design_id == version.design_id)
    )
    design = design_result.scalar_one_or_none()

    # Build design params
    params = build_design_params_from_option(
        option_id,
        version.price or 0
    )

    # Get available studios（SQL 层硬约束 + 限 50 个候选）
    studios = await get_all_available_studios(db)

    # 评分排序，逐个尝试占位（防止并发抢同一个工作室容量）
    ranked = rank_studios(studios, params)

    for studio_info, score in ranked:
        if score.total <= 0:
            continue

        # 原子占位：current_load < capacity 才 +1
        result = await db.execute(
            update(Studio)
            .where(Studio.studio_id == studio_info.studio_id)
            .where(Studio.current_load < Studio.capacity)
            .values(current_load=Studio.current_load + 1)
        )
        if result.rowcount == 0:
            # 容量被别人抢走了，试下一个
            continue

        # 写订单（同一事务）
        await db.execute(
            update(Order)
            .where(Order.order_id == order_id)
            .values(studio_id=studio_info.studio_id)
        )
        await db.flush()

        return DispatchResult(
            dispatched=True,
            studio_id=studio_info.studio_id,
            studio_name=studio_info.name,
            score=score.total,
            reason=f"Atomic dispatch with score {score.total:.2f}",
        )

    # 所有候选都失败 → 走原 fallback 流程（中央工作室或人工）
    return dispatch_order(studios, params)


async def release_studio_capacity(db: AsyncSession, studio_id: str):
    """Release capacity when order reaches terminal state.

    使用原子 UPDATE，避免读改写竞态。
    """
    await db.execute(
        update(Studio)
        .where(Studio.studio_id == studio_id)
        .where(Studio.current_load > 0)
        .values(current_load=Studio.current_load - 1)
    )
    await db.flush()
