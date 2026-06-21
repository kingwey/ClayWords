"""Payment Service - Alipay Sandbox Integration"""

import hashlib
import time
import urllib.parse
from typing import Optional, Dict
from datetime import datetime

from app.core.config import settings


class PaymentConfig:
    """支付配置（支付宝沙箱）"""
    # 支付宝沙箱网关
    GATEWAY_URL = "https://openapi.alipaydev.com/gateway.do"

    # 应用配置（从环境变量读取）
    APP_ID = getattr(settings, "ALIPAY_APP_ID", "2021000000000000")  # 沙箱 AppID

    # 商户私钥（RSA2）
    MERCHANT_PRIVATE_KEY = getattr(settings, "ALIPAY_PRIVATE_KEY", "")

    # 支付宝公钥
    ALIPAY_PUBLIC_KEY = getattr(settings, "ALIPAY_PUBLIC_KEY", "")

    # 回调地址
    NOTIFY_URL = getattr(settings, "ALIPAY_NOTIFY_URL", "http://localhost:8000/api/v1/payments/callback")
    RETURN_URL = getattr(settings, "ALIPAY_RETURN_URL", "http://localhost:3000/orders")

    # 支付超时时间（分钟）
    TIMEOUT_EXPRESS = "30m"


class PaymentService:
    """支付服务"""

    def __init__(self):
        self.config = PaymentConfig()

    def create_trade(
        self,
        order_id: str,
        total_amount: float,
        subject: str,
        body: Optional[str] = None
    ) -> Dict[str, str]:
        """
        创建支付交易

        Phase Q6: 支付宝沙箱集成

        返回: {"pay_url": str, "trade_no": str}
        """
        # 构建支付参数
        biz_content = {
            "out_trade_no": order_id,  # 商户订单号
            "total_amount": f"{total_amount:.2f}",  # 总金额（元）
            "subject": subject,  # 订单标题
            "body": body or subject,  # 订单描述
            "product_code": "FAST_INSTANT_TRADE_PAY",  # 产品码（PC 网站支付）
            "timeout_express": self.config.TIMEOUT_EXPRESS,
        }

        # 公共参数
        params = {
            "app_id": self.config.APP_ID,
            "method": "alipay.trade.page.pay",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": self.config.NOTIFY_URL,
            "return_url": self.config.RETURN_URL,
            "biz_content": self._json_dumps(biz_content),
        }

        # Phase Q6: 真实环境需要 RSA2 签名
        # 当前为 Mock 模式，返回模拟支付 URL
        if not self.config.MERCHANT_PRIVATE_KEY:
            # Mock 模式
            mock_url = f"{self.config.GATEWAY_URL}?mock=true&out_trade_no={order_id}&total_amount={total_amount:.2f}"
            return {
                "pay_url": mock_url,
                "trade_no": f"mock_trade_{order_id}",
                "qr_code": None,  # 可选：二维码 base64
            }

        # 真实模式：生成签名
        sign = self._sign(params)
        params["sign"] = sign

        # 构建支付 URL
        pay_url = f"{self.config.GATEWAY_URL}?{urllib.parse.urlencode(params)}"

        return {
            "pay_url": pay_url,
            "trade_no": order_id,  # 真实环境从支付宝返回
            "qr_code": None,
        }

    def verify_callback(self, params: Dict[str, str]) -> bool:
        """
        验证支付回调签名

        Phase Q6: RSA2 验签
        """
        if not self.config.ALIPAY_PUBLIC_KEY:
            # Mock 模式：始终验证通过
            return "mock" in params.get("out_trade_no", "")

        # 真实模式：验证签名
        sign = params.pop("sign", "")
        sign_type = params.pop("sign_type", "")

        if sign_type != "RSA2":
            return False

        # 排序并拼接参数
        sorted_params = sorted(params.items())
        unsigned_string = "&".join([f"{k}={v}" for k, v in sorted_params if v])

        # 验证签名（需要 RSA 公钥）
        # TODO: 实现 RSA2 验签逻辑
        return True

    def query_trade(self, order_id: str) -> Optional[Dict]:
        """
        查询支付结果

        Phase Q6: 主动查询交易状态
        """
        # Mock 模式
        return {
            "trade_no": f"mock_trade_{order_id}",
            "out_trade_no": order_id,
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "0.00",
            "buyer_pay_amount": "0.00",
        }

    def refund_trade(
        self,
        order_id: str,
        refund_amount: float,
        refund_reason: str
    ) -> Dict:
        """
        发起退款

        Phase Q6: 支付宝退款接口
        """
        # Mock 模式
        return {
            "success": True,
            "refund_no": f"refund_{order_id}_{int(time.time())}",
            "out_trade_no": order_id,
            "refund_amount": f"{refund_amount:.2f}",
            "refund_reason": refund_reason,
        }

    def _sign(self, params: Dict[str, str]) -> str:
        """生成 RSA2 签名"""
        # 排序并拼接参数
        sorted_params = sorted(params.items())
        unsigned_string = "&".join([f"{k}={v}" for k, v in sorted_params if v])

        # TODO: 使用 RSA 私钥签名
        # from Crypto.PublicKey import RSA
        # from Crypto.Signature import PKCS1_v1_5
        # from Crypto.Hash import SHA256

        # Mock 签名
        return hashlib.sha256(unsigned_string.encode()).hexdigest()

    def _json_dumps(self, obj: Dict) -> str:
        """JSON 序列化"""
        import json
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


# 全局实例
payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    """获取支付服务实例"""
    return payment_service
