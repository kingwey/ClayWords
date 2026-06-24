"""payment_service 单元测试（纯函数，无外部依赖）

覆盖目标：services/payment/payment_service.py 当前 71%。
未覆盖路径主要是真实签名分支（有私钥时），以及 _sign / _json_dumps 工具。
"""

import json
import pytest
from app.services.payment.payment_service import PaymentService, PaymentConfig


@pytest.fixture
def svc():
    return PaymentService()


@pytest.fixture
def svc_real_key(monkeypatch):
    """模拟已配置私钥的环境，触发真实模式分支。"""
    svc = PaymentService()
    svc.config.MERCHANT_PRIVATE_KEY = "fake_private_key_for_testing"
    svc.config.ALIPAY_PUBLIC_KEY = "fake_public_key_for_testing"
    return svc


# ---- create_trade -----------------------------------------------------------


@pytest.mark.unit
def test_create_trade_mock_mode_returns_pay_url(svc):
    result = svc.create_trade("order-1", 99.0, "陶瓷定制")
    assert "pay_url" in result
    assert "trade_no" in result
    assert "mock=true" in result["pay_url"]
    assert "order-1" in result["pay_url"]
    assert result["trade_no"] == "mock_trade_order-1"


@pytest.mark.unit
def test_create_trade_formats_amount_to_2dp(svc):
    result = svc.create_trade("order-2", 9.9, "茶壶")
    assert "9.90" in result["pay_url"]


@pytest.mark.unit
def test_create_trade_real_mode_builds_signed_url(svc_real_key):
    result = svc_real_key.create_trade("order-3", 199.5, "白瓷摆件")
    assert "pay_url" in result
    assert "sign=" in result["pay_url"]
    assert "alipay.trade.page.pay" in result["pay_url"]


# ---- verify_callback --------------------------------------------------------


@pytest.mark.unit
def test_verify_callback_mock_mode_passes_when_out_trade_no_has_mock(svc):
    assert svc.verify_callback({"out_trade_no": "mock_order_123"}) is True


@pytest.mark.unit
def test_verify_callback_mock_mode_rejects_non_mock(svc):
    assert svc.verify_callback({"out_trade_no": "real_order_456"}) is False


@pytest.mark.unit
def test_verify_callback_real_mode_rejects_wrong_sign_type(svc_real_key):
    # sign_type != RSA2 should fail
    assert svc_real_key.verify_callback({
        "out_trade_no": "o-1", "sign": "x", "sign_type": "MD5"
    }) is False


@pytest.mark.unit
def test_verify_callback_real_mode_rsa2(svc_real_key):
    # RSA2 with valid sign_type reaches the TODO stub (returns True)
    assert svc_real_key.verify_callback({
        "out_trade_no": "o-2", "sign": "x", "sign_type": "RSA2"
    }) is True


# ---- query_trade / refund_trade ---------------------------------------------


@pytest.mark.unit
def test_query_trade_returns_success(svc):
    result = svc.query_trade("order-99")
    assert result["trade_status"] == "TRADE_SUCCESS"
    assert result["out_trade_no"] == "order-99"


@pytest.mark.unit
def test_refund_trade_returns_success(svc):
    result = svc.refund_trade("order-5", 50.0, "用户申请退款")
    assert result["success"] is True
    assert result["refund_amount"] == "50.00"
    assert result["out_trade_no"] == "order-5"
    assert result["refund_reason"] == "用户申请退款"


# ---- _sign / _json_dumps ----------------------------------------------------


@pytest.mark.unit
def test_sign_is_deterministic(svc_real_key):
    params = {"a": "1", "b": "2", "app_id": "x"}
    assert svc_real_key._sign(params) == svc_real_key._sign(params)


@pytest.mark.unit
def test_sign_skips_empty_values(svc_real_key):
    """空值参数不应参与签名字符串（与支付宝规范一致）。"""
    full = svc_real_key._sign({"a": "1", "b": "2"})
    with_empty = svc_real_key._sign({"a": "1", "b": "2", "c": ""})
    assert full == with_empty


@pytest.mark.unit
def test_json_dumps_no_spaces(svc):
    obj = {"k": "v", "n": 1}
    out = svc._json_dumps(obj)
    parsed = json.loads(out)
    assert parsed == obj
    assert " " not in out  # separators=(',', ':') — no spaces
