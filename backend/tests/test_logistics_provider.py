"""logistics Provider 抽象 + 注册表测试"""

import pytest

from app.services.logistics import (
    LogisticsStatus,
    MockLogisticsProvider,
    TrackingResult,
    get_provider,
    list_providers,
    register_provider,
)
from app.services.logistics.base import BaseLogisticsProvider


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_empty_tracking_number_yields_unknown(self):
        provider = MockLogisticsProvider()
        result = await provider.query_tracking("")
        assert result.status == LogisticsStatus.UNKNOWN
        assert result.events == []

    @pytest.mark.asyncio
    async def test_tracking_number_yields_progress(self):
        provider = MockLogisticsProvider()
        result = await provider.query_tracking("SF1234567890")
        assert result.tracking_number == "SF1234567890"
        assert result.carrier == "mock"
        assert len(result.events) >= 2  # 至少 SHIPPED + IN_TRANSIT
        assert result.status in {
            LogisticsStatus.IN_TRANSIT,
            LogisticsStatus.OUT_FOR_DELIVERY,
            LogisticsStatus.DELIVERED,
        }

    @pytest.mark.asyncio
    async def test_same_input_deterministic(self):
        """同一单号查询两次应返回同样的状态(基于 hash 分桶)"""
        provider = MockLogisticsProvider()
        a = await provider.query_tracking("SF999")
        b = await provider.query_tracking("SF999")
        assert a.status == b.status
        assert len(a.events) == len(b.events)


class TestRegistry:
    def test_default_registry_has_mock(self):
        names = list_providers()
        assert "mock" in names

    def test_get_provider_unknown_falls_back_to_mock(self):
        provider = get_provider("not_a_real_carrier")
        assert provider.name == "mock"

    def test_get_provider_none_falls_back_to_mock(self):
        provider = get_provider(None)
        assert provider.name == "mock"

    def test_get_provider_chinese_alias(self):
        # 中文别名应映射(目前只有 mock 真实存在, 其他映射后回退到 mock)
        # 但 alias 解析本身要工作
        from app.services.logistics.registry import _CARRIER_ALIASES
        assert _CARRIER_ALIASES["顺丰"] == "sf"
        assert _CARRIER_ALIASES["中通"] == "zto"

    def test_register_custom_provider(self):
        class StubProvider(BaseLogisticsProvider):
            name = "stub_for_test"
            display_name = "Stub"

            async def query_tracking(self, tracking_number):
                return TrackingResult(
                    tracking_number=tracking_number,
                    carrier=self.name,
                    status=LogisticsStatus.SHIPPED,
                )

        register_provider(StubProvider())
        assert "stub_for_test" in list_providers()
        assert get_provider("stub_for_test").name == "stub_for_test"
