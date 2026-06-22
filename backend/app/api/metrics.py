"""Metrics API - Prometheus metrics endpoint"""

from fastapi import APIRouter, Response
from app.core.metrics import get_metrics


router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus 指标端点

    Phase Q7.2.1: 暴露 /metrics 接口供 Prometheus 抓取

    返回格式: text/plain（Prometheus 格式）
    """
    metrics_text = get_metrics().export_prometheus()
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/metrics/json")
async def metrics_json():
    """
    JSON 格式的指标（用于自定义仪表板）

    Phase Q7.2.2: 业务指标 JSON API
    """
    metrics = get_metrics()

    # 计算汇总数据
    total_requests = sum(metrics.http_requests_total.values())
    total_tasks = sum(metrics.tasks_total.values())
    total_orders = sum(metrics.orders_total.values())
    total_payments = sum(metrics.payments_total.values())

    # HTTP 状态码分布
    status_distribution = {}
    for (method, path, status), count in metrics.http_requests_total.items():
        status_class = f"{status // 100}xx"
        status_distribution[status_class] = status_distribution.get(status_class, 0) + count

    # 计算成功率
    total_2xx = status_distribution.get("2xx", 0)
    success_rate = (total_2xx / total_requests * 100) if total_requests > 0 else 0

    # 计算请求耗时统计
    duration_stats = {}
    if metrics.http_request_duration:
        durations = sorted([r["duration_ms"] for r in metrics.http_request_duration])
        n = len(durations)
        duration_stats = {
            "count": n,
            "avg_ms": round(sum(durations) / n, 2),
            "p50_ms": round(durations[int(n * 0.5)], 2),
            "p95_ms": round(durations[int(n * 0.95)], 2),
            "p99_ms": round(durations[int(n * 0.99)], 2),
            "max_ms": round(durations[-1], 2),
        }

    return {
        "summary": {
            "total_requests": total_requests,
            "total_tasks": total_tasks,
            "total_orders": total_orders,
            "total_payments": total_payments,
            "success_rate": round(success_rate, 2),
        },
        "http": {
            "status_distribution": status_distribution,
            "duration": duration_stats,
        },
        "tasks": {
            "by_state": metrics.tasks_total,
        },
        "orders": {
            "by_status": metrics.orders_total,
        },
        "payments": {
            "by_status": metrics.payments_total,
        },
        "studios": {
            "by_status": metrics.studios_total,
        },
        "active_connections": {
            "sse": metrics.active_sse_connections,
            "workers": metrics.active_workers,
        },
    }
