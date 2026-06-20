"""Database Models - SQLite Compatible"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Float, Integer
from sqlalchemy import JSON as SQLAlchemyJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    phone_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Studio(Base):
    __tablename__ = "studios"

    studio_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    specialties: Mapped[list] = mapped_column(SQLAlchemyJSON, default=list)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    price_range_min: Mapped[float] = mapped_column(Float, default=0)
    price_range_max: Mapped[float] = mapped_column(Float, default=1000)
    estimated_days: Mapped[int] = mapped_column(Integer, default=7)
    craft_overrides: Mapped[dict] = mapped_column(SQLAlchemyJSON, default=dict)
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
    design_params: Mapped[Optional[dict]] = mapped_column(SQLAlchemyJSON, nullable=True)
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
    embedding: Mapped[Optional[list]] = mapped_column(SQLAlchemyJSON, nullable=True)
    default_params: Mapped[dict] = mapped_column(SQLAlchemyJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Design(Base):
    __tablename__ = "designs"

    design_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    design_params: Mapped[dict] = mapped_column(SQLAlchemyJSON, nullable=False)
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
    craft_check_result: Mapped[dict] = mapped_column(SQLAlchemyJSON, nullable=False)
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
    extra_data: Mapped[dict] = mapped_column(SQLAlchemyJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="logs")
