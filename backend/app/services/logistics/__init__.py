"""物流追踪 Provider 抽象 + 注册表

接入第三方物流 (顺丰/中通/快递100) 时, 实现 BaseProvider 子类并在
PROVIDERS 字典中注册即可。API 层通过 carrier 字符串路由到对应 Provider。

设计目的:
- API 层不再硬编码 mock 轨迹; mock 仍然可用, 但只是其中一个 Provider
- 接入真实快递时只需替换/增加 Provider, API 层零改动
- 单测可注入 stub Provider
"""

from .base import BaseLogisticsProvider, TrackingEvent, TrackingResult, LogisticsStatus
from .mock_provider import MockLogisticsProvider
from .registry import get_provider, register_provider, list_providers

__all__ = [
    "BaseLogisticsProvider",
    "TrackingEvent",
    "TrackingResult",
    "LogisticsStatus",
    "MockLogisticsProvider",
    "get_provider",
    "register_provider",
    "list_providers",
]
