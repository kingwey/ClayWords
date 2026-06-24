"""Design Options API"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Session as SessionModel, Design as DesignModel, DesignVersion as DesignVersionModel


router = APIRouter(prefix="/options", tags=["options"])


class CraftCheckResult(BaseModel):
    wall_thickness: bool
    overhang: bool
    base_stability: bool
    shrinkage_compensated: bool


class DesignOption(BaseModel):
    option_id: str
    session_id: str
    design_id: str
    version_no: int
    route: str  # template, generative, hybrid
    craft_check: CraftCheckResult
    auto_fixed: bool = False
    thumbnail_url: Optional[str] = None
    glb_url: Optional[str] = None
    price: Optional[float] = None
    estimated_days: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConfirmRequest(BaseModel):
    option_id: str
    address: Optional[str] = None
    notes: Optional[str] = None


class ConfirmResponse(BaseModel):
    order_id: str
    idempotency_key: str


@router.get("/sessions/{session_id}/options", response_model=List[DesignOption])
async def list_session_options(
    session_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List all design options for a session"""
    # Verify session belongs to user
    result = await session.execute(
        select(SessionModel)
        .where(
            SessionModel.session_id == session_id,
            SessionModel.user_id == current_user.user_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get designs with latest versions
    result = await session.execute(
        select(DesignModel)
        .where(DesignModel.session_id == session_id)
        .order_by(DesignModel.created_at.desc())
    )
    designs = result.scalars().all()

    options = []
    for design in designs:
        # Get latest version
        version_result = await session.execute(
            select(DesignVersionModel)
            .where(DesignVersionModel.design_id == design.design_id)
            .order_by(DesignVersionModel.version_no.desc())
            .limit(1)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            continue

        option = DesignOption(
            option_id=version.id,
            session_id=session_id,
            design_id=design.design_id,
            version_no=version.version_no,
            route=design.route or "template",
            craft_check=CraftCheckResult(
                wall_thickness=True,
                overhang=True,
                base_stability=True,
                shrinkage_compensated=True
            ),
            auto_fixed=version.auto_fixed or False,
            thumbnail_url=version.thumbnail_url,
            glb_url=version.glb_url,
            price=design.price,
            estimated_days=design.estimated_days,
            created_at=version.created_at
        )
        options.append(option)

    return options


@router.get("/{option_id}", response_model=DesignOption)
async def get_option(
    option_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed design option"""
    result = await session.execute(
        select(DesignVersionModel)
        .where(DesignVersionModel.id == option_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")

    # Get design
    design_result = await session.execute(
        select(DesignModel)
        .where(DesignModel.design_id == version.design_id)
    )
    design = design_result.scalar_one_or_none()
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design not found")

    # Verify session ownership
    session_result = await session.execute(
        select(SessionModel)
        .where(
            SessionModel.session_id == design.session_id,
            SessionModel.user_id == current_user.user_id
        )
    )
    s = session_result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return DesignOption(
        option_id=version.id,
        session_id=design.session_id,
        design_id=design.design_id,
        version_no=version.version_no,
        route=design.route or "template",
        craft_check=CraftCheckResult(
            wall_thickness=True,
            overhang=True,
            base_stability=True,
            shrinkage_compensated=True
        ),
        auto_fixed=version.auto_fixed or False,
        thumbnail_url=version.thumbnail_url,
        glb_url=version.glb_url,
        price=design.price,
        estimated_days=design.estimated_days,
        created_at=version.created_at
    )


@router.post("/sessions/{session_id}/confirm", response_model=ConfirmResponse, status_code=status.HTTP_201_CREATED)
async def confirm_option(
    session_id: str,
    request: ConfirmRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Confirm a design option and create an order (idempotent)"""
    from app.models.entities import Order as OrderModel, OrderLog as OrderLogModel
    
    # Generate idempotency key if not provided
    idempotency_key = request.option_id  # Use option_id as part of idempotency
    
    # Check if order already exists with this idempotency key
    result = await session.execute(
        select(OrderModel)
        .where(OrderModel.idempotency_key == idempotency_key)
    )
    existing_order = result.scalar_one_or_none()
    if existing_order:
        return ConfirmResponse(
            order_id=existing_order.order_id,
            idempotency_key=existing_order.idempotency_key
        )
    
    # Verify session belongs to user
    session_result = await session.execute(
        select(SessionModel)
        .where(
            SessionModel.session_id == session_id,
            SessionModel.user_id == current_user.user_id
        )
    )
    s = session_result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Verify option exists
    version_result = await session.execute(
        select(DesignVersionModel)
        .where(DesignVersionModel.id == request.option_id)
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    
    # Get design to verify ownership
    design_result = await session.execute(
        select(DesignModel)
        .where(DesignModel.design_id == version.design_id)
    )
    design = design_result.scalar_one_or_none()
    if not design or design.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design not found")
    
    # Create order
    order = OrderModel(
        order_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        session_id=session_id,
        option_id=request.option_id,
        status="pending",
        idempotency_key=idempotency_key,
        shipping_address=request.address or "",
        total_price=design.price or 0
    )
    session.add(order)
    
    # Create order log
    order_log = OrderLogModel(
        id=str(uuid.uuid4()),
        order_id=order.order_id,
        from_status=None,
        to_status="pending",
        operator="user",
        reason="Order created from design confirmation"
    )
    session.add(order_log)

    await session.flush()

    # Metrics: 记录订单创建
    from app.core.metrics import metrics
    metrics.increment_order("pending")

    return ConfirmResponse(
        order_id=order.order_id,
        idempotency_key=order.idempotency_key
    )
