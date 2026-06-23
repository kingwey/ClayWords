"""Provider 注册表

用法:
    >>> from app.services.logistics import get_provider
    >>> provider = get_provider("mock")  # 或 "sf" / "zto" / 等
    >>> result = await provider.query_tracking("SF1234567890")

切换默认 Provider 通过 LOGISTICS_PROVIDER 环境变量 (config.py 读取)。
"""

from __future__ import annotations

from typing import Optional

from .base import BaseLogisticsProvider
from .mock_provider import MockLogisticsProvider


# Provider 实例缓存 — 避免每次请求新建对象 (httpx Client 池等)
_PROVIDERS: dict[str, BaseLogisticsProvider] = {
    "mock": MockLogisticsProvider(),
}

# 中文承运商名 → Provider name 的映射
# 工作室录入 carrier 时可能写 "顺丰" / "顺丰速运" / "SF", 都收口到 "sf"
_CARRIER_ALIASES: dict[str, str] = {
    "mock": "mock",
    "sf": "sf",
    "顺丰": "sf",
    "顺丰速运": "sf",
    "zto": "zto",
    "中通": "zto",
    "中通快递": "zto",
    "yto": "yto",
    "圆通": "yto",
    "圆通速递": "yto",
    "kd100": "kd100",
    "快递100": "kd100",
}


def register_provider(provider: BaseLogisticsProvider) -> None:
    """注册新的 Provider (主进程启动时调用; 单测可注入 stub)"""
    _PROVIDERS[provider.name] = provider


def list_providers() -> list[str]:
    """已注册 Provider name 列表"""
    return sorted(_PROVIDERS.keys())


def get_provider(carrier: Optional[str] = None) -> BaseLogisticsProvider:
    """按 carrier 字段返回 Provider; 找不到时回退到 mock。

    回退策略 (而不是抛错): 工作室录入了奇怪的 carrier 时, 让物流查询
    至少能返回一条 mock 轨迹给用户看, 比 500 体验好。运维通过
    /metrics 中的 logistics_total{provider=mock} 监控误用率。
    """
    if not carrier:
        return _PROVIDERS["mock"]

    key = _CARRIER_ALIASES.get(carrier.strip().lower(), carrier.strip().lower())
    return _PROVIDERS.get(key, _PROVIDERS["mock"])
