"""Logistics Provider 抽象基类与 DTO"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LogisticsStatus(str, Enum):
    """统一物流状态机 (各 Provider 自己映射到这套枚举)"""

    UNKNOWN = "unknown"          # 单号查不到
    SHIPPED = "shipped"          # 已揽收
    IN_TRANSIT = "in_transit"    # 运输中
    OUT_FOR_DELIVERY = "out_for_delivery"  # 派送中
    DELIVERED = "delivered"      # 已签收
    EXCEPTION = "exception"      # 异常 (退回/损毁/疑难)


@dataclass
class TrackingEvent:
    """单条物流轨迹"""

    time: datetime               # 事件发生时间 (UTC)
    status: LogisticsStatus      # 标准化状态
    description: str             # 文本描述 ("已到达【景德镇分拣中心】")
    location: Optional[str] = None


@dataclass
class TrackingResult:
    """一次物流查询的完整结果"""

    tracking_number: str
    carrier: str                 # Provider 自报的承运商编码 ("sf", "zto", "mock")
    status: LogisticsStatus
    events: list[TrackingEvent] = field(default_factory=list)
    estimated_delivery_date: Optional[str] = None  # YYYY-MM-DD
    raw: Optional[dict] = None   # 原始第三方响应, 便于排障 (慎对外暴露)


class BaseLogisticsProvider(ABC):
    """物流 Provider 抽象基类。

    每个具体快递公司一个 Provider 子类 (顺丰=SFProvider, 中通=ZTOProvider...)。
    """

    #: Provider 唯一标识, 也是 API 层 carrier 字段的值
    name: str = "base"

    #: 用户可读的中文名 ("顺丰速运")
    display_name: str = "Base Provider"

    @abstractmethod
    async def query_tracking(self, tracking_number: str) -> TrackingResult:
        """查询单号轨迹。

        约定:
        - 单号无效 → 返回 status=UNKNOWN, events=[], 不抛异常
        - 网络/鉴权错误 → 抛 LogisticsProviderError
        - 真实第三方响应放进 .raw, 标准化后填 .events / .status
        """
        raise NotImplementedError


class LogisticsProviderError(Exception):
    """Provider 调用失败 (网络/鉴权/超时), 由 API 层捕获返回 502"""
