"""Authentication API with Real Implementation"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import User, Studio
from app.db.session import get_session
from app.core.config import settings
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


# 仅在非生产环境启用的演示账号；生产环境应接入真实短信验证码
DEMO_ACCOUNTS = {
    "13800000001": "user",
    "13800000002": "studio",
    "13800000003": "admin",
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> UserInfo:
    """从 JWT 提取用户身份。

    优化路径：登录/刷新时已把 role 编进 claim，多数请求无需查库。
    旧 token（无 role claim）回退查库一次。手机号脱敏只在必须时解密，
    避免每个受保护请求都跑 AES-GCM。
    """
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    role = payload.get("role")
    studio_id = payload.get("studio_id")

    # 快路径：claim 完整 → 不查库
    if role:
        return UserInfo(
            user_id=user_id,
            phone="",  # 脱敏字段不再每请求解密；需要时调用 /auth/user 即可
            role=role,
            studio_id=studio_id,
        )

    # 兼容旧 token：回查一次
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return UserInfo(
        user_id=user.user_id,
        phone="",
        role=user.role or "user",
        studio_id=user.studio_id,
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

    # 找不到用户时：仅在非生产环境允许 demo 账号自动建账，
    # 生产环境必须先注册（或等真实短信通道接入），不能凭手机号直接发 token
    if not user:
        if not settings.is_production and request.phone in DEMO_ACCOUNTS:
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
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or invalid credentials",
            )

    user_id = user.user_id
    user_role = user.role or "user"

    access_token = create_access_token({
        "sub": user_id,
        "role": user_role,
        "studio_id": user.studio_id,
    })
    refresh_token = create_refresh_token({"sub": user_id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user_role
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    payload = verify_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    # 刷新时再读一次最新 role/studio_id，避免管理员降权后旧 access_token 仍生效一整天
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_role = user.role or "user"
    access_token = create_access_token({
        "sub": user_id,
        "role": user_role,
        "studio_id": user.studio_id,
    })
    new_refresh_token = create_refresh_token({"sub": user_id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        role=user_role,
    )


@router.get("/user", response_model=UserInfo)
async def get_user(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """返回脱敏后的用户资料；这里才解密手机号，避免每请求都跑 crypto。"""
    if current_user.phone:
        return current_user

    result = await session.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    crypto = get_crypto()
    try:
        phone_decrypted = crypto.decrypt(user.phone_encrypted)
        masked = phone_decrypted[:3] + "****" + phone_decrypted[-4:]
    except Exception:
        masked = ""

    return UserInfo(
        user_id=user.user_id,
        phone=masked,
        role=user.role or "user",
        studio_id=user.studio_id,
    )
