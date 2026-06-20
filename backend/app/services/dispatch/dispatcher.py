"""Dispatch Service - Studio selection and order dispatching"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.entities import Studio, Order, Design, DesignVersion
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
    """Get all studios with available capacity."""
    result = await db.execute(select(Studio))
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
    """
    # Get design info
    version_result = await db.execute(
        select(DesignVersion).where(DesignVersion.id == option_id)
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
        design.price if design else 0
    )
    
    # Get available studios
    studios = await get_all_available_studios(db)
    
    # Dispatch
    result = dispatch_order(studios, params)
    
    if result.dispatched and result.studio_id:
        # Update order with assigned studio
        order_result = await db.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if order:
            order.studio_id = result.studio_id
        
        # Update studio current_load
        studio_result = await db.execute(
            select(Studio).where(Studio.studio_id == result.studio_id)
        )
        studio = studio_result.scalar_one_or_none()
        if studio:
            studio.current_load = (studio.current_load or 0) + 1
        
        await db.flush()
    
    return result


async def release_studio_capacity(db: AsyncSession, studio_id: str):
    """Release capacity when order reaches terminal state."""
    result = await db.execute(
        select(Studio).where(Studio.studio_id == studio_id)
    )
    studio = result.scalar_one_or_none()
    if studio and studio.current_load > 0:
        studio.current_load -= 1
        await db.flush()
