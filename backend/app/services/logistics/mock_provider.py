"""Mock 物流 Provider - 替代原 logistics.py 中的内联 mock 数据。

无需真实第三方账号, 用于开发期 / staging 环境 / 单测。
真实流量上线后通过 LOGISTICS_PROVIDER 环境变量切换到 SFProvider/ZTOProvider。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import (
    BaseLogisticsProvider,
    LogisticsStatus,
    TrackingEvent,
    TrackingResult,
)


class MockLogisticsProvider(BaseLogisticsProvider):
    """根据 tracking_number 字符特征伪造一段合理轨迹。

    不依赖外部网络。轨迹时间从 "现在 - 2 天" 推到 "现在", 让前端看起来
    像真实物流流转。同一个单号每次查询返回同一张时间线 (基于 hash)。
    """

    name = "mock"
    display_name = "Mock 物流 (开发模式)"

    async def query_tracking(self, tracking_number: str) -> TrackingResult:
        if not tracking_number:
            return TrackingResult(
                tracking_number="",
                carrier=self.name,
                status=LogisticsStatus.UNKNOWN,
                events=[],
            )

        # 基于单号 hash 决定 "进度" — 让 demo 看起来确定且分布合理
        progress = sum(ord(c) for c in tracking_number) % 4
        now = datetime.now(timezone.utc)

        events: list[TrackingEvent] = [
            TrackingEvent(
                time=now - timedelta(days=2, hours=3),
                status=LogisticsStatus.SHIPPED,
                description="【景德镇】已揽收",
                location="江西省景德镇市",
            ),
            TrackingEvent(
                time=now - timedelta(days=1, hours=8),
                status=LogisticsStatus.IN_TRANSIT,
                description="快件离开【景德镇转运中心】",
                location="江西省景德镇市",
            ),
        ]

        status = LogisticsStatus.IN_TRANSIT

        if progress >= 2:
            events.append(
                TrackingEvent(
                    time=now - timedelta(hours=6),
                    status=LogisticsStatus.OUT_FOR_DELIVERY,
                    description="快件已到达派送网点, 派送中",
                    location="北京市朝阳区",
                )
            )
            status = LogisticsStatus.OUT_FOR_DELIVERY

        if progress >= 3:
            events.append(
                TrackingEvent(
                    time=now - timedelta(minutes=30),
                    status=LogisticsStatus.DELIVERED,
                    description="快件已签收, 感谢使用陶语",
                    location="用户地址",
                )
            )
            status = LogisticsStatus.DELIVERED

        return TrackingResult(
            tracking_number=tracking_number,
            carrier=self.name,
            status=status,
            events=events,
            estimated_delivery_date=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
            raw=None,
        )
