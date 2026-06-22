"""Alerting Service - Alert rules and notifications"""

import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict], bool]  # 触发条件
    threshold: float  # 阈值
    duration_seconds: int = 60  # 持续时间（秒）
    cooldown_seconds: int = 300  # 冷却时间（秒），避免重复告警


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


class AlertingService:
    """告警服务

    Phase Q7.4: 告警规则引擎
    """

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_fired: Dict[str, float] = {}  # rule_name -> timestamp

        # 注册默认告警规则
        self._register_default_rules()

    def _register_default_rules(self):
        """注册默认告警规则"""
        # 5xx 错误率告警
        self.add_rule(AlertRule(
            name="high_5xx_error_rate",
            description="5xx 错误率超过 5%",
            severity=AlertSeverity.ERROR,
            condition=lambda metrics: self._check_5xx_rate(metrics, 0.05),
            threshold=0.05,
            duration_seconds=60,
        ))

        # 任务失败率告警
        self.add_rule(AlertRule(
            name="high_task_failure_rate",
            description="任务失败率超过 10%",
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: self._check_task_failure_rate(metrics, 0.10),
            threshold=0.10,
            duration_seconds=120,
        ))

        # 支付成功率告警
        self.add_rule(AlertRule(
            name="low_payment_success_rate",
            description="支付成功率低于 95%",
            severity=AlertSeverity.ERROR,
            condition=lambda metrics: self._check_payment_success_rate(metrics, 0.95),
            threshold=0.95,
            duration_seconds=300,
        ))

        # 响应时间告警
        self.add_rule(AlertRule(
            name="high_response_time",
            description="P95 响应时间超过 1 秒",
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: self._check_p95_duration(metrics, 1000),
            threshold=1000,
            duration_seconds=180,
        ))

        # SSE 连接数告警
        self.add_rule(AlertRule(
            name="too_many_sse_connections",
            description="SSE 活跃连接超过 500",
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: metrics.active_sse_connections > 500,
            threshold=500,
            duration_seconds=60,
        ))

    def _check_5xx_rate(self, metrics, threshold: float) -> bool:
        """检查 5xx 错误率"""
        total = sum(metrics.http_requests_total.values())
        if total < 10:  # 至少10个请求才计算
            return False

        errors = sum(
            count for (method, path, status), count in metrics.http_requests_total.items()
            if status >= 500
        )
        rate = errors / total if total > 0 else 0
        return rate > threshold

    def _check_task_failure_rate(self, metrics, threshold: float) -> bool:
        """检查任务失败率"""
        total = sum(metrics.tasks_total.values())
        if total < 10:
            return False

        failed = metrics.tasks_total.get("failed", 0)
        rate = failed / total if total > 0 else 0
        return rate > threshold

    def _check_payment_success_rate(self, metrics, threshold: float) -> bool:
        """检查支付成功率"""
        total = sum(metrics.payments_total.values())
        if total < 5:
            return False

        success = metrics.payments_total.get("success", 0)
        rate = success / total if total > 0 else 1.0
        return rate < threshold

    def _check_p95_duration(self, metrics, threshold_ms: float) -> bool:
        """检查 P95 响应时间"""
        if not metrics.http_request_duration:
            return False

        durations = sorted([r["duration_ms"] for r in metrics.http_request_duration])
        n = len(durations)
        if n < 10:
            return False

        p95 = durations[int(n * 0.95)]
        return p95 > threshold_ms

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)

    def evaluate(self, metrics) -> List[Alert]:
        """评估所有规则，返回新触发的告警"""
        new_alerts = []
        now = time.time()

        for rule in self.rules:
            # 检查冷却时间
            last_fired = self.last_fired.get(rule.name, 0)
            if now - last_fired < rule.cooldown_seconds:
                continue

            try:
                if rule.condition(metrics):
                    # 触发告警
                    if rule.name not in self.active_alerts:
                        alert = Alert(
                            rule_name=rule.name,
                            severity=rule.severity,
                            status=AlertStatus.FIRING,
                            message=rule.description,
                            triggered_at=datetime.utcnow(),
                            metadata={
                                "threshold": rule.threshold,
                                "duration_seconds": rule.duration_seconds,
                            }
                        )
                        self.active_alerts[rule.name] = alert
                        self.alert_history.append(alert)
                        self.last_fired[rule.name] = now
                        new_alerts.append(alert)
                else:
                    # 解除告警
                    if rule.name in self.active_alerts:
                        alert = self.active_alerts[rule.name]
                        alert.status = AlertStatus.RESOLVED
                        alert.resolved_at = datetime.utcnow()
                        del self.active_alerts[rule.name]

            except Exception:
                # 规则评估失败，忽略
                continue

        return new_alerts

    def get_active_alerts(self) -> List[Alert]:
        """获取当前活跃的告警"""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]


# 全局告警服务实例
alerting_service = AlertingService()


def get_alerting_service() -> AlertingService:
    """获取告警服务实例"""
    return alerting_service
