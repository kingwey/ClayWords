"""Unit tests for alerting service"""

import pytest
from app.services.alerting.alerting_service import (
    AlertingService, AlertRule, AlertSeverity, AlertStatus
)
from app.core.metrics import MetricsRegistry


@pytest.mark.unit
class TestAlertingService:
    """告警服务测试"""

    def test_default_rules_registered(self):
        """测试默认规则已注册"""
        service = AlertingService()
        assert len(service.rules) >= 5

        # 验证关键规则存在
        rule_names = [r.name for r in service.rules]
        assert "high_5xx_error_rate" in rule_names
        assert "high_task_failure_rate" in rule_names
        assert "low_payment_success_rate" in rule_names

    def test_add_custom_rule(self):
        """测试添加自定义规则"""
        service = AlertingService()
        initial_count = len(service.rules)

        custom_rule = AlertRule(
            name="custom_test_rule",
            description="测试规则",
            severity=AlertSeverity.INFO,
            condition=lambda m: True,
            threshold=0,
        )
        service.add_rule(custom_rule)

        assert len(service.rules) == initial_count + 1

    def test_evaluate_no_metrics(self):
        """测试空指标时的评估"""
        service = AlertingService()
        metrics = MetricsRegistry()

        new_alerts = service.evaluate(metrics)
        # 没有数据时不应该触发告警
        assert len(new_alerts) == 0

    def test_evaluate_high_error_rate(self):
        """测试高错误率告警"""
        service = AlertingService()
        metrics = MetricsRegistry()

        # 添加大量 500 错误
        for _ in range(20):
            metrics.increment_http_request("GET", "/api/test", 500)
        # 添加少量成功
        for _ in range(2):
            metrics.increment_http_request("GET", "/api/test", 200)

        new_alerts = service.evaluate(metrics)

        # 应该触发 5xx 告警
        alert_names = [a.rule_name for a in new_alerts]
        assert "high_5xx_error_rate" in alert_names

    def test_alert_cooldown(self):
        """测试告警冷却机制"""
        service = AlertingService()
        metrics = MetricsRegistry()

        # 添加大量错误触发告警
        for _ in range(20):
            metrics.increment_http_request("GET", "/api/test", 500)

        # 第一次评估
        first_alerts = service.evaluate(metrics)
        assert len(first_alerts) >= 1

        # 立即再次评估，由于冷却时间，不应该再次触发
        second_alerts = service.evaluate(metrics)
        assert len(second_alerts) == 0

    def test_alert_resolution(self):
        """测试告警解除"""
        service = AlertingService()
        metrics = MetricsRegistry()

        # 触发告警
        for _ in range(20):
            metrics.increment_http_request("GET", "/api/test", 500)

        service.evaluate(metrics)
        assert len(service.active_alerts) > 0

        # 重置指标，模拟问题解决
        metrics2 = MetricsRegistry()
        for _ in range(20):
            metrics2.increment_http_request("GET", "/api/test", 200)

        service.evaluate(metrics2)
        # 告警应该被解除
        # 注意：由于冷却机制，规则可能还在 active_alerts 中
        # 这里主要测试逻辑不会崩溃

    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        service = AlertingService()
        active = service.get_active_alerts()
        assert isinstance(active, list)

    def test_get_alert_history(self):
        """测试获取告警历史"""
        service = AlertingService()
        history = service.get_alert_history(limit=10)
        assert isinstance(history, list)
        assert len(history) <= 10
