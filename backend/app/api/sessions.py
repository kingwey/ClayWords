"""Sessions API with Database Persistence"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user, UserInfo
from app.models.entities import Session as SessionModel, SessionMessage as MessageModel
from app.db.session import get_session


router = APIRouter()


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    design_params: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str


class SendMessageResponse(BaseModel):
    task_id: str


@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new session"""
    new_session = SessionModel(
        session_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        title=request.title or "新会话"
    )
    session.add(new_session)
    await session.flush()

    return SessionResponse(
        id=new_session.session_id,
        user_id=new_session.user_id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at
    )


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List all sessions for current user"""
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.user_id == current_user.user_id)
        .order_by(desc(SessionModel.updated_at))
    )
    sessions = result.scalars().all()

    return [
        SessionResponse(
            id=s.session_id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get a specific session"""
    result = await db.execute(
        select(SessionModel)
        .where(
            SessionModel.session_id == session_id,
            SessionModel.user_id == current_user.user_id
        )
    )
    s = result.scalar_one_or_none()

    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return SessionResponse(
        id=s.session_id,
        user_id=s.user_id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at
    )


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get messages for a session"""
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

    # Get messages
    result = await session.execute(
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            design_params=m.design_params,
            created_at=m.created_at
        )
        for m in messages
    ]


@router.post("/{session_id}/messages", response_model=SendMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Send a message and trigger design generation"""
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

    # Create user message
    user_message = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=request.content
    )
    session.add(user_message)

    # Update session
    s.updated_at = datetime.utcnow()
    if s.title == "新会话":
        s.title = request.content[:50]

    # Create assistant system message
    assistant_message = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content="好的，我来为您设计这个方案。"
    )
    session.add(assistant_message)

    # Generate task ID for 3D generation
    task_id = str(uuid.uuid4())

    await session.flush()

    return SendMessageResponse(task_id=task_id)
