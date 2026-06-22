"""Alerts API - View active alerts and history"""

from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.services.alerting.alerting_service import (
    get_alerting_service, AlertingService, AlertSeverity, AlertStatus
)
from app.core.metrics import get_metrics


router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    """告警响应"""
    rule_name: str
    severity: str
    status: str
    message: str
    triggered_at: str
    resolved_at: Optional[str] = None
    metadata: dict


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    alerting: AlertingService = Depends(get_alerting_service),
):
    """
    获取当前活跃的告警

    Phase Q7.4: 告警查询
    """
    # 触发评估
    metrics = get_metrics()
    alerting.evaluate(metrics)

    alerts = alerting.get_active_alerts()
    return [
        AlertResponse(
            rule_name=a.rule_name,
            severity=a.severity.value,
            status=a.status.value,
            message=a.message,
            triggered_at=a.triggered_at.isoformat(),
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            metadata=a.metadata,
        )
        for a in alerts
    ]


@router.get("/history", response_model=List[AlertResponse])
async def get_alert_history(
    limit: int = 50,
    alerting: AlertingService = Depends(get_alerting_service),
):
    """
    获取告警历史

    Phase Q7.4: 告警历史查询
    """
    alerts = alerting.get_alert_history(limit=limit)
    return [
        AlertResponse(
            rule_name=a.rule_name,
            severity=a.severity.value,
            status=a.status.value,
            message=a.message,
            triggered_at=a.triggered_at.isoformat(),
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            metadata=a.metadata,
        )
        for a in alerts
    ]


@router.get("/rules")
async def get_alert_rules(
    alerting: AlertingService = Depends(get_alerting_service),
):
    """
    获取告警规则配置

    Phase Q7.4: 告警规则查询
    """
    return [
        {
            "name": rule.name,
            "description": rule.description,
            "severity": rule.severity.value,
            "threshold": rule.threshold,
            "duration_seconds": rule.duration_seconds,
            "cooldown_seconds": rule.cooldown_seconds,
        }
        for rule in alerting.rules
    ]


@router.post("/evaluate")
async def trigger_evaluation(
    alerting: AlertingService = Depends(get_alerting_service),
):
    """
    手动触发告警评估

    Phase Q7.4: 测试告警规则
    """
    metrics = get_metrics()
    new_alerts = alerting.evaluate(metrics)

    return {
        "evaluated_at": datetime.utcnow().isoformat(),
        "rules_count": len(alerting.rules),
        "active_alerts": len(alerting.active_alerts),
        "new_alerts": len(new_alerts),
        "new_alert_details": [
            {
                "rule_name": a.rule_name,
                "severity": a.severity.value,
                "message": a.message,
            }
            for a in new_alerts
        ]
    }
