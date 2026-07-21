"""Unit tests for payment service"""

import pytest
from app.services.payment.payment_service import PaymentService


@pytest.mark.unit
class TestPaymentService:
    """支付服务测试"""

    def test_create_trade_returns_pay_url(self):
        """测试创建交易返回支付链接"""
        service = PaymentService()

        result = service.create_trade(
            order_id="test_order_123",
            total_amount=100.00,
            subject="测试订单"
        )

        assert "pay_url" in result
        assert "trade_no" in result
        assert result["pay_url"]  # 非空

    def test_create_trade_with_body(self):
        """测试带描述的交易"""
        service = PaymentService()

        result = service.create_trade(
            order_id="order_with_body",
            total_amount=200.00,
            subject="主题",
            body="详细描述"
        )

        assert result["pay_url"]
        assert "test_order" not in result["trade_no"] or "mock_trade" in result["trade_no"]

    def test_verify_callback_mock_mode(self):
        """测试回调验证（Mock 模式）"""
        service = PaymentService()

        # Mock 模式下，包含 "mock" 的交易应该通过
        params = {
            "out_trade_no": "mock_order_123",
            "trade_no": "mock_trade_456",
            "trade_status": "TRADE_SUCCESS",
        }

        is_valid = service.verify_callback(params)
        assert is_valid

    def test_query_trade(self):
        """测试查询交易"""
        service = PaymentService()

        result = service.query_trade("test_order")
        assert result is not None
        assert "trade_status" in result

    def test_refund_trade(self):
        """测试退款"""
        service = PaymentService()

        result = service.refund_trade(
            order_id="test_order",
            refund_amount=50.00,
            refund_reason="用户取消"
        )

        assert result["success"]
        assert "refund_no" in result
        assert result["refund_amount"] == "50.00"
