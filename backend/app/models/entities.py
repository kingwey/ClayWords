"""Database Models - Postgres Primary with SQLite Fallback"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Float, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid

from app.models.types import Vector, EncryptedStr, JSONB


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    phone_encrypted: Mapped[str] = mapped_column(EncryptedStr(500), nullable=False)
    email_encrypted: Mapped[Optional[str]] = mapped_column(EncryptedStr(500), nullable=True)
    address_encrypted: Mapped[Optional[str]] = mapped_column(EncryptedStr(1000), nullable=True)
    # 角色：user 普通用户 / studio 工作室 / admin 平台管理员
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    # 工作室用户关联的工作室 ID（role=studio 时使用）
    studio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("studios.studio_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Studio(Base):
    __tablename__ = "studios"

    studio_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    specialties: Mapped[list] = mapped_column(JSONB(), default=list)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    price_range_min: Mapped[float] = mapped_column(Float, default=0)
    price_range_max: Mapped[float] = mapped_column(Float, default=1000)
    estimated_days: Mapped[int] = mapped_column(Integer, default=7)
    craft_overrides: Mapped[dict] = mapped_column(JSONB(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="studio")


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["SessionMessage"]] = relationship(back_populates="session", order_by="SessionMessage.created_at")


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    design_params: Mapped[Optional[dict]] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="messages")


class DesignTemplate(Base):
    __tablename__ = "design_templates"

    template_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    glb_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    default_params: Mapped[dict] = mapped_column(JSONB(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Design(Base):
    __tablename__ = "designs"

    design_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    design_params: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions: Mapped[list["DesignVersion"]] = relationship(back_populates="design",
                                                             order_by="DesignVersion.version_no.desc()")


class DesignVersion(Base):
    __tablename__ = "design_versions"

    version_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id: Mapped[str] = mapped_column(String(36), ForeignKey("designs.design_id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    option_no: Mapped[int] = mapped_column(Integer, nullable=False)
    pipeline: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    glb_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    craft_check_result: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    estimated_volume: Mapped[float] = mapped_column(Float, default=0)
    estimated_weight: Mapped[float] = mapped_column(Float, default=0)
    price: Mapped[float] = mapped_column(Float, default=0)
    estimated_days: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    design: Mapped["Design"] = relationship(back_populates="versions")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    option_id: Mapped[str] = mapped_column(String(36), ForeignKey("design_versions.version_id"), nullable=False)
    studio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("studios.studio_id"), nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    shipping_name: Mapped[str] = mapped_column(String(100), default="")
    shipping_phone: Mapped[str] = mapped_column(String(20), default="")
    shipping_address: Mapped[str] = mapped_column(String(500), default="")

    total_price: Mapped[float] = mapped_column(Float, default=0)
    workorder_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    studio: Mapped[Optional["Studio"]] = relationship(back_populates="orders")
    logs: Mapped[list["OrderLog"]] = relationship(back_populates="order", order_by="OrderLog.created_at")


class OrderLog(Base):
    __tablename__ = "order_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.order_id"), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    operator: Mapped[str] = mapped_column(String(50), default="system")
    reason: Mapped[str] = mapped_column(Text, default="")
    extra_data: Mapped[dict] = mapped_column(JSONB(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="logs")


class StudioCraftOverride(Base):
    """工作室工艺校准覆盖配置"""
    __tablename__ = "studio_craft_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    studio_id: Mapped[str] = mapped_column(String(36), ForeignKey("studios.studio_id"), nullable=False)
    min_wall_thickness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_shrinkage_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_overhang_angle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calibration_data: Mapped[dict] = mapped_column(JSONB(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IdempotencyKey(Base):
    """幂等性键持久化表"""
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    response_body: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index('idx_idempotency_expires', 'expires_at'),
    )


class Task(Base):
    """任务持久化表（与 Redis 双写）"""
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB(), default=dict)
    result_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_tasks_state', 'state'),
        Index('idx_tasks_created', 'created_at'),
    )


class Upload(Base):
    """文件上传记录表（安全扫描状态机）"""
    __tablename__ = "uploads"

    upload_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    object_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="pending")  # pending, scanning, clean, quarantined
    scan_result: Mapped[Optional[dict]] = mapped_column(JSONB(), nullable=True)
    uploader_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_uploads_state', 'state'),
        Index('idx_uploads_uploader', 'uploader_id'),
        Index('idx_uploads_created', 'created_at'),
    )
