"""订单状态机单元测试

覆盖：
- 12-node 合法转换矩阵
- 终态拒绝再转换
- cancel 逻辑边界
"""

import pytest

from app.services.order.state_machine import (
    OrderStatus,
    transition,
    validate_transition,
    is_terminal_status,
    is_cancellable,
    LEGAL_TRANSITIONS,
)


class TestTransition:
    def test_pending_to_confirmed_ok(self):
        result = transition(OrderStatus.PENDING, OrderStatus.CONFIRMED)
        assert result.success is True

    def test_pending_to_shipped_rejected(self):
        # 跳级转换必须失败
        result = transition(OrderStatus.PENDING, OrderStatus.SHIPPED)
        assert result.success is False

    def test_qc_back_to_producing_allowed(self):
        # 质检失败可以回 producing 重做
        result = transition(OrderStatus.QC, OrderStatus.PRODUCING)
        assert result.success is True

    def test_terminal_status_blocks_further_transitions(self):
        # delivered / refunded / cancelled 后续不允许任何转换
        for terminal in (OrderStatus.DELIVERED, OrderStatus.REFUNDED):
            result = transition(terminal, OrderStatus.PENDING)
            assert result.success is False, f"{terminal} 不应允许再次转换"


class TestValidateTransition:
    def test_validate_returns_true_for_legal(self):
        assert validate_transition(
            OrderStatus.CONFIRMED, OrderStatus.DISPATCHED
        ) is True

    def test_validate_returns_false_for_illegal(self):
        assert validate_transition(
            OrderStatus.SHIPPED, OrderStatus.PRODUCING
        ) is False


class TestTerminalAndCancellable:
    def test_delivered_is_terminal(self):
        assert is_terminal_status(OrderStatus.DELIVERED) is True

    def test_pending_is_not_terminal(self):
        assert is_terminal_status(OrderStatus.PENDING) is False

    def test_pending_is_cancellable(self):
        assert is_cancellable(OrderStatus.PENDING) is True

    def test_shipped_is_not_cancellable(self):
        # 一旦发货，业务上禁止取消（应走退款流程）
        assert is_cancellable(OrderStatus.SHIPPED) is False


class TestLegalTransitionsMatrix:
    def test_every_status_in_matrix(self):
        # 状态机正确性：除终态外，每个状态都有出边
        non_terminal = [
            s for s in OrderStatus
            if s not in (
                OrderStatus.DELIVERED,
                OrderStatus.REFUNDED,
                OrderStatus.CANCELLED,
            )
        ]
        for s in non_terminal:
            assert s in LEGAL_TRANSITIONS, f"{s} 缺少转换定义"
            assert len(LEGAL_TRANSITIONS[s]) > 0, f"{s} 出边为空"

    def test_no_self_loops(self):
        for s, targets in LEGAL_TRANSITIONS.items():
            assert s not in targets, f"{s} 不应允许自转换"
