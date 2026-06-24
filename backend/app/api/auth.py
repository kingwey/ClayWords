"""Authentication API with Real Implementation"""

import uuid

from fastapi import APIRouter, HTTPException, Depends, status, Cookie, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.models.entities import User, Studio
from app.db.session import get_session
from app.core.config import settings
from app.core.crypto import get_crypto
from app.core.time import utcnow
from app.services.auth import create_access_token, create_refresh_token, verify_token, revoke_token, is_token_revoked


router = APIRouter()


class LoginRequest(BaseModel):
    phone: str
    code: str


class LoginResponse(BaseModel):
    """登录响应 - token 通过 HttpOnly cookie 传输"""
    role: str = "user"


class UserInfo(BaseModel):
    user_id: str
    phone: str
    role: str
    studio_id: str | None = None
    nickname: str | None = None
    social_bindings: dict = {}


class UpdateProfileRequest(BaseModel):
    """用户资料更新 (昵称 / 手机号)。两者都可选, 只更新提供的字段。"""
    nickname: str | None = None
    phone: str | None = None


class BindSocialRequest(BaseModel):
    """绑定第三方账号 (演示: 直接记录; 生产: 走 OAuth 回调换 code)。"""
    provider: str  # wechat / feishu / qq / dingtalk / douyin
    # 演示模式下可选传入一个外部标识; 不传则生成 mock openid
    external_id: str | None = None


# 支持绑定的第三方平台
SUPPORTED_SOCIAL_PROVIDERS = {
    "wechat": "微信",
    "feishu": "飞书",
    "qq": "QQ",
    "dingtalk": "钉钉",
    "douyin": "抖音",
}


# 仅在非生产环境启用的演示账号；生产环境应接入真实短信验证码
DEMO_ACCOUNTS = {
    "13800000001": "user",
    "13800000002": "studio",
    "13800000003": "admin",
}


async def get_current_user(
    access_token: str = Cookie(None),
    session: AsyncSession = Depends(get_session)
) -> UserInfo:
    """从 Cookie 中的 JWT 提取用户身份。

    HttpOnly cookie 传输，JavaScript 无法读取，防御 XSS 窃取 token。
    登录/刷新时已把 role 编进 claim，多数请求无需查库。
    旧 token（无 role claim）回退查库一次。
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication cookie"
        )

    payload = verify_token(access_token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # 黑名单检查：token 签名合法但已被主动撤销（logout / 权限变更）
    if await is_token_revoked(payload.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
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
    response: Response,
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

    # 写入 HttpOnly cookie，防止 XSS 窃取
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,  # 生产强制 HTTPS
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return LoginResponse(role=user_role)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_token: str = Cookie(None),
    response: Response = None,
    session: AsyncSession = Depends(get_session),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie"
        )

    payload = verify_token(refresh_token, "refresh")
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

    # 更新 cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return LoginResponse(role=user_role)


@router.post("/logout")
async def logout(
    response: Response,
    access_token: str = Cookie(None),
    refresh_token: str = Cookie(None),
):
    """登出 - 撤销 token（加入黑名单）+ 清除 cookie"""
    if access_token:
        await revoke_token(access_token)
    if refresh_token:
        await revoke_token(refresh_token)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


def _mask_phone(crypto, phone_encrypted: str) -> str:
    """解密并脱敏手机号; 失败返回空串。"""
    try:
        phone_decrypted = crypto.decrypt(phone_encrypted)
        return phone_decrypted[:3] + "****" + phone_decrypted[-4:]
    except Exception:
        return ""


def _to_user_info(user: User, crypto) -> UserInfo:
    """User ORM → UserInfo (脱敏手机号 + 绑定状态)。"""
    return UserInfo(
        user_id=user.user_id,
        phone=_mask_phone(crypto, user.phone_encrypted),
        role=user.role or "user",
        studio_id=user.studio_id,
        nickname=user.nickname,
        social_bindings=user.social_bindings or {},
    )


@router.get("/user", response_model=UserInfo)
async def get_user(
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """返回脱敏后的用户资料 (含昵称 + 第三方绑定状态)。

    /auth/user 不是热路径 (前端每会话拉一次), 所以这里统一查库,
    保证 nickname 等可变字段能被立即看到 (避免 fast-path 缓存陈旧)。
    """
    result = await session.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return _to_user_info(user, get_crypto())


@router.patch("/profile", response_model=UserInfo)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新当前用户资料 (昵称 / 手机号)。

    校验:
    - nickname: 长度 0-50; 空字符串 → 清空昵称
    - phone: 11 位中国大陆手机号; 重新 hash + 加密; 不可与他人重复
    """
    result = await session.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    crypto = get_crypto()

    # ---- 昵称 ----
    if request.nickname is not None:
        nickname = request.nickname.strip()
        if nickname == "":
            user.nickname = None
        elif len(nickname) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="昵称长度不能超过 50",
            )
        else:
            user.nickname = nickname

    # ---- 手机号 ----
    if request.phone is not None:
        phone = request.phone.strip()
        if not (phone.isdigit() and len(phone) == 11 and phone.startswith("1")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号格式不正确 (需 11 位中国大陆号码)",
            )
        new_hash = crypto.hash_phone(phone)
        if new_hash != user.phone_hash:
            # 唯一性检查: 不能撞到别人的手机号
            dup = await session.execute(
                select(User).where(
                    User.phone_hash == new_hash,
                    User.user_id != user.user_id,
                )
            )
            if dup.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="该手机号已被其他账号绑定",
                )
            user.phone_hash = new_hash
            user.phone_encrypted = crypto.encrypt(phone)

    await session.commit()
    await session.refresh(user)
    return _to_user_info(user, crypto)


@router.post("/social/bind", response_model=UserInfo)
async def bind_social(
    request: BindSocialRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """绑定第三方账号。

    演示实现: 直接写入一条绑定记录 (mock openid + 时间)。
    生产环境应改为: 前端跳 OAuth 授权 → 回调带 code → 后端换 openid 再绑定。
    """
    provider = request.provider.strip().lower()
    if provider not in SUPPORTED_SOCIAL_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的平台: {request.provider}",
        )

    result = await session.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    bindings = dict(user.social_bindings or {})
    if provider in bindings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"已绑定{SUPPORTED_SOCIAL_PROVIDERS[provider]}, 请先解绑",
        )

    external_id = request.external_id or f"demo_{provider}_{uuid.uuid4().hex[:12]}"
    bindings[provider] = {
        "openid": external_id,
        "bound_at": utcnow().isoformat(),
    }
    user.social_bindings = bindings
    # JSONB 原地改 dict 不一定触发脏检测, 显式标记
    flag_modified(user, "social_bindings")

    await session.commit()
    await session.refresh(user)
    return _to_user_info(user, get_crypto())


@router.post("/social/unbind", response_model=UserInfo)
async def unbind_social(
    request: BindSocialRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """解绑第三方账号。"""
    provider = request.provider.strip().lower()
    if provider not in SUPPORTED_SOCIAL_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的平台: {request.provider}",
        )

    result = await session.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    bindings = dict(user.social_bindings or {})
    if provider not in bindings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"尚未绑定{SUPPORTED_SOCIAL_PROVIDERS[provider]}",
        )

    del bindings[provider]
    user.social_bindings = bindings
    flag_modified(user, "social_bindings")

    await session.commit()
    await session.refresh(user)
    return _to_user_info(user, get_crypto())
