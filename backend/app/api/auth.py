"""Authentication API with Real Implementation"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import User, Studio
from app.db.session import get_session
from app.core.crypto import get_crypto
from app.services.auth import create_access_token, create_refresh_token, verify_token


router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    phone: str
    code: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str = "user"


class UserInfo(BaseModel):
    user_id: str
    phone: str
    role: str
    studio_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


DEMO_ACCOUNTS = {
    "13800000001": "user",
    "13800000002": "studio",
    "13800000003": "admin"
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> UserInfo:
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    crypto = get_crypto()
    phone_decrypted = crypto.decrypt(user.phone_encrypted)

    return UserInfo(
        user_id=user.user_id,
        phone=phone_decrypted[:3] + "****" + phone_decrypted[-4:],
        role=user.role or "user",
        studio_id=user.studio_id
    )


def require_role(*roles: str):
    async def check_role(current_user: UserInfo = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return check_role


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    if len(request.code) != 6 or not request.code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code format"
        )

    crypto = get_crypto()
    phone_hash = crypto.hash_phone(request.phone)

    result = await session.execute(select(User).where(User.phone_hash == phone_hash))
    user = result.scalar_one_or_none()

    if not user:
        if request.phone in DEMO_ACCOUNTS:
            demo_role = DEMO_ACCOUNTS[request.phone]
            studio_id = None

            # studio 角色：自动创建/复用一个 demo 工作室并绑定
            if demo_role == "studio":
                studio_id = "demo-studio-0001"
                existing_studio = await session.execute(
                    select(Studio).where(Studio.studio_id == studio_id)
                )
                if existing_studio.scalar_one_or_none() is None:
                    session.add(Studio(
                        studio_id=studio_id,
                        name="景德镇 · demo 工作室",
                        location="景德镇",
                        specialties=["白瓷", "青花"],
                        capacity=10,
                        current_load=0,
                        rating=4.8,
                        craft_overrides={"status": "approved"},
                    ))
                    await session.flush()

            user = User(
                phone_hash=phone_hash,
                phone_encrypted=crypto.encrypt(request.phone),
                role=demo_role,
                studio_id=studio_id,
            )
            session.add(user)
            await session.flush()

    if user:
        user_id = user.user_id
        user_role = user.role or "user"
    else:
        user_id = f"user_{request.phone[-4:]}"
        user_role = "user"

    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user_role
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: RefreshRequest):
    payload = verify_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.get("/user", response_model=UserInfo)
async def get_user(current_user: UserInfo = Depends(get_current_user)):
    return current_user
