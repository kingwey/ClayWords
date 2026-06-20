"""Order State Machine - 12-node status management"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class OrderStatus(str, Enum):
    """Order status enum - 12 states"""
    # 待确认
    PENDING = "pending"
    # 已确认
    CONFIRMED = "confirmed"
    # 已派单
    DISPATCHED = "dispatched"
    # 制作中
    PRODUCING = "producing"
    # 待上釉
    GLAZING = "glazing"
    # 烧制中
    FIRING = "firing"
    # 冷却中
    COOLING = "cooling"
    # 待质检
    QC = "qc"
    # 已完成
    COMPLETED = "completed"
    # 待发货
    SHIPPING_PENDING = "shipping_pending"
    # 已发货
    SHIPPED = "shipped"
    # 已签收
    DELIVERED = "delivered"
    # 已取消
    CANCELLED = "cancelled"
    # 退款中
    REFUNDING = "refunding"
    # 已退款
    REFUNDED = "refunded"


# Legal transitions: from_status -> [to_statuses]
LEGAL_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED
    ],
    OrderStatus.CONFIRMED: [
        OrderStatus.DISPATCHED,
        OrderStatus.CANCELLED
    ],
    OrderStatus.DISPATCHED: [
        OrderStatus.PRODUCING,
        OrderStatus.CANCELLED
    ],
    OrderStatus.PRODUCING: [
        OrderStatus.GLAZING,
        OrderStatus.CANCELLED
    ],
    OrderStatus.GLAZING: [
        OrderStatus.FIRING,
        OrderStatus.CANCELLED
    ],
    OrderStatus.FIRING: [
        OrderStatus.COOLING,
        OrderStatus.CANCELLED
    ],
    OrderStatus.COOLING: [
        OrderStatus.QC,
        OrderStatus.CANCELLED
    ],
    OrderStatus.QC: [
        OrderStatus.COMPLETED,
        OrderStatus.PRODUCING  # Return to production if failed
    ],
    OrderStatus.COMPLETED: [
        OrderStatus.SHIPPING_PENDING
    ],
    OrderStatus.SHIPPING_PENDING: [
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED  # Before shipping, can still cancel
    ],
    OrderStatus.SHIPPED: [
        OrderStatus.DELIVERED
    ],
    OrderStatus.DELIVERED: [
        # Terminal state - no transitions out
    ],
    OrderStatus.CANCELLED: [
        OrderStatus.REFUNDING  # If was paid, go to refund
    ],
    OrderStatus.REFUNDING: [
        OrderStatus.REFUNDED
    ],
    OrderStatus.REFUNDED: [
        # Terminal state
    ]
}

# Status display info
STATUS_INFO: dict[OrderStatus, dict] = {
    OrderStatus.PENDING: {"label": "待确认", "color": "#909399", "icon": "clock"},
    OrderStatus.CONFIRMED: {"label": "已确认", "color": "#409EFF", "icon": "check"},
    OrderStatus.DISPATCHED: {"label": "已派单", "color": "#67C23A", "icon": "truck"},
    OrderStatus.PRODUCING: {"label": "制作中", "color": "#E6A23C", "icon": "tools"},
    OrderStatus.GLAZING: {"label": "待上釉", "color": "#E6A23C", "icon": "brush"},
    OrderStatus.FIRING: {"label": "烧制中", "color": "#F56C6C", "icon": "flame"},
    OrderStatus.COOLING: {"label": "冷却中", "color": "#909399", "icon": "snowflake"},
    OrderStatus.QC: {"label": "待质检", "color": "#E6A23C", "icon": "search"},
    OrderStatus.COMPLETED: {"label": "已完成", "color": "#67C23A", "icon": "check-circle"},
    OrderStatus.SHIPPING_PENDING: {"label": "待发货", "color": "#409EFF", "icon": "box"},
    OrderStatus.SHIPPED: {"label": "已发货", "color": "#409EFF", "icon": "truck"},
    OrderStatus.DELIVERED: {"label": "已签收", "color": "#67C23A", "icon": "check-circle"},
    OrderStatus.CANCELLED: {"label": "已取消", "color": "#909399", "icon": "close"},
    OrderStatus.REFUNDING: {"label": "退款中", "color": "#E6A23C", "icon": "wallet"},
    OrderStatus.REFUNDED: {"label": "已退款", "color": "#909399", "icon": "wallet"},
}


class IllegalTransition(Exception):
    """Raised when an illegal status transition is attempted"""
    def __init__(self, from_status: OrderStatus, to_status: OrderStatus):
        self.from_status = from_status
        self.to_status = to_status
        allowed = LEGAL_TRANSITIONS.get(from_status, [])
        super().__init__(
            f"Illegal transition: {from_status.value} -> {to_status.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )


def is_terminal_status(status: OrderStatus) -> bool:
    """Check if status is a terminal state."""
    return status in [OrderStatus.DELIVERED, OrderStatus.REFUNDED]


def is_cancellable(status: OrderStatus) -> bool:
    """Check if order can be cancelled from this status."""
    return status in [
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
        OrderStatus.DISPATCHED,
        OrderStatus.PRODUCING,
        OrderStatus.GLAZING,
        OrderStatus.FIRING,
        OrderStatus.COOLING,
        OrderStatus.SHIPPING_PENDING
    ]


def can_refund(status: OrderStatus) -> bool:
    """Check if order can go to refund flow."""
    return status in [
        OrderStatus.CANCELLED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED
    ]


def validate_transition(from_status: OrderStatus, to_status: OrderStatus) -> bool:
    """Validate if transition is legal."""
    allowed = LEGAL_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def get_next_statuses(current: OrderStatus) -> list[OrderStatus]:
    """Get list of possible next statuses."""
    return LEGAL_TRANSITIONS.get(current, [])


def get_status_timeline() -> list[OrderStatus]:
    """Get ordered list of statuses in production timeline."""
    return [
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
        OrderStatus.DISPATCHED,
        OrderStatus.PRODUCING,
        OrderStatus.GLAZING,
        OrderStatus.FIRING,
        OrderStatus.COOLING,
        OrderStatus.QC,
        OrderStatus.COMPLETED,
        OrderStatus.SHIPPING_PENDING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED
    ]


@dataclass
class TransitionResult:
    """Result of a transition attempt"""
    success: bool
    from_status: Optional[OrderStatus]
    to_status: Optional[OrderStatus]
    message: str


def transition(
    current: OrderStatus,
    target: OrderStatus,
    allow_refund_flow: bool = True
) -> TransitionResult:
    """
    Attempt to transition from current to target status.
    
    Returns TransitionResult with success status and details.
    """
    if current == target:
        return TransitionResult(
            success=True,
            from_status=current,
            to_status=target,
            message="Already in this status"
        )
    
    if not validate_transition(current, target):
        # Special handling for refund flow
        if (allow_refund_flow and 
            current == OrderStatus.CANCELLED and 
            target == OrderStatus.REFUNDING):
            return TransitionResult(
                success=True,
                from_status=current,
                to_status=target,
                message="Starting refund flow"
            )
        
        return TransitionResult(
            success=False,
            from_status=current,
            to_status=target,
            message=f"Illegal transition from {current.value} to {target.value}"
        )
    
    return TransitionResult(
        success=True,
        from_status=current,
        to_status=target,
        message=f"Transition {current.value} -> {target.value}"
    )
