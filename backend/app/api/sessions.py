"""Sessions API with Database Persistence"""

import uuid
from datetime import datetime
from typing import Optional, List, Annotated

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user, UserInfo
from app.models.entities import Session as SessionModel, SessionMessage as MessageModel
from app.db.session import get_session


router = APIRouter()


# Type alias for dependency
DbSession = Annotated[AsyncSession, Depends(get_session)]


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
    session: DbSession,
    current_user: UserInfo = Depends(get_current_user),
    request: CreateSessionRequest = None
):
    """Create a new session"""
    if request is None:
        request = CreateSessionRequest()
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
    session: DbSession,
    current_user: UserInfo = Depends(get_current_user)
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
    session: DbSession,
    current_user: UserInfo = Depends(get_current_user)
):
    """Get a specific session"""
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
    session: DbSession,
    current_user: UserInfo = Depends(get_current_user)
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
    session: DbSession,
    current_user: UserInfo = Depends(get_current_user)
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

    # Generate task ID for tracking
    task_id = str(uuid.uuid4())

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

    # Parse design intent with LLM
    try:
        from app.services.llm.parser import parse_design_params, InputValidationError
        
        try:
            design_params = await parse_design_params(request.content)
            assistant_content = f"好的，我理解您想要一个{design_params.shape}，" \
                              f"使用{design_params.glaze_color}，风格{design_params.style}。"
            # Store design params in message
            user_message.design_params = {
                "shape": design_params.shape,
                "glaze_color": design_params.glaze_color,
                "size": design_params.size,
                "style": design_params.style,
                "emotion": design_params.emotion,
                "material": design_params.material,
                "usage": design_params.usage
            }
        except InputValidationError as e:
            assistant_content = f"抱歉，{str(e)}"
    except Exception:
        assistant_content = "好的，我来为您设计这个方案。"

    # Create assistant message
    assistant_message = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=assistant_content
    )
    session.add(assistant_message)

    await session.flush()

    return SendMessageResponse(task_id=task_id)
