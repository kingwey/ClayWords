"""Unit tests for metrics module"""

import pytest
from app.core.metrics import MetricsRegistry


@pytest.mark.unit
class TestMetricsRegistry:
    """指标注册表测试"""

    def test_increment_http_request(self):
        """测试 HTTP 请求计数"""
        metrics = MetricsRegistry()

        metrics.increment_http_request("GET", "/api/test", 200)
        metrics.increment_http_request("GET", "/api/test", 200)
        metrics.increment_http_request("POST", "/api/test", 201)

        key_get = ("GET", "/api/test", 200)
        key_post = ("POST", "/api/test", 201)

        assert metrics.http_requests_total[key_get] == 2
        assert metrics.http_requests_total[key_post] == 1

    def test_record_http_duration(self):
        """测试 HTTP 耗时记录"""
        metrics = MetricsRegistry()

        metrics.record_http_duration("GET", "/api/test", 50.5)
        metrics.record_http_duration("GET", "/api/test", 75.2)

        assert len(metrics.http_request_duration) == 2
        assert metrics.http_request_duration[0]["duration_ms"] == 50.5

    def test_duration_history_capped_at_1000(self):
        """测试耗时历史限制 1000 条"""
        metrics = MetricsRegistry()

        # 添加 1500 条
        for i in range(1500):
            metrics.record_http_duration("GET", "/api/test", float(i))

        # 应该只保留最近 1000 条
        assert len(metrics.http_request_duration) == 1000
        # 最新的应该是 1499
        assert metrics.http_request_duration[-1]["duration_ms"] == 1499.0

    def test_increment_business_metrics(self):
        """测试业务指标"""
        metrics = MetricsRegistry()

        metrics.increment_task("completed")
        metrics.increment_task("failed")
        metrics.increment_payment("success")
        metrics.increment_order("dispatched")
        metrics.increment_studio("approved")

        assert metrics.tasks_total["completed"] == 1
        assert metrics.tasks_total["failed"] == 1
        assert metrics.payments_total["success"] == 1
        assert metrics.orders_total["dispatched"] == 1
        assert metrics.studios_total["approved"] == 1

    def test_export_prometheus_format(self):
        """测试 Prometheus 格式导出"""
        metrics = MetricsRegistry()

        metrics.increment_http_request("GET", "/api/test", 200)
        metrics.record_http_duration("GET", "/api/test", 50.0)

        output = metrics.export_prometheus()

        # 验证格式
        assert "# HELP http_requests_total" in output
        assert "# TYPE http_requests_total counter" in output
        assert 'http_requests_total{method="GET",path="/api/test",status="200"} 1' in output

    def test_p95_calculation(self):
        """测试 P95 计算"""
        metrics = MetricsRegistry()

        # 添加 100 个数据点：1, 2, 3, ..., 100
        for i in range(1, 101):
            metrics.record_http_duration("GET", "/api/test", float(i))

        output = metrics.export_prometheus()

        # P95 应该约为 95
        assert 'http_request_duration_ms{quantile="0.95"}' in output
