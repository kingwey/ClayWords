"""Prometheus Metrics - HTTP and business metrics"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# 简化版 Prometheus 指标实现
# 真实环境应该使用 prometheus_client 库


class MetricsRegistry:
    """简化版指标注册表"""

    def __init__(self):
        # HTTP 指标
        self.http_requests_total = {}  # {(method, path, status): count}
        self.http_request_duration = []  # [(method, path, duration_ms)]

        # 业务指标
        self.tasks_total = {}  # {(state): count}
        self.tasks_duration = []  # [(task_type, duration_ms)]
        self.payments_total = {}  # {(status): count}
        self.orders_total = {}  # {(status): count}
        self.studios_total = {}  # {(status): count}
        self.dispatch_total = {}  # {(outcome): count} - 派单结果
        self.studio_load_gauge = {}  # {studio_id: current_load} - 工作室容量

        # 活跃连接
        self.active_sse_connections = 0
        self.active_workers = 0

    def increment_http_request(self, method: str, path: str, status: int):
        """增加 HTTP 请求计数"""
        key = (method, path, status)
        self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1

    def record_http_duration(self, method: str, path: str, duration_ms: float):
        """记录 HTTP 请求耗时"""
        self.http_request_duration.append({
            "method": method,
            "path": path,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })
        # 只保留最近 1000 条记录
        if len(self.http_request_duration) > 1000:
            self.http_request_duration = self.http_request_duration[-1000:]

    def increment_task(self, state: str):
        """增加任务计数"""
        self.tasks_total[state] = self.tasks_total.get(state, 0) + 1

    def increment_payment(self, status: str):
        """增加支付计数"""
        self.payments_total[status] = self.payments_total.get(status, 0) + 1

    def increment_order(self, status: str):
        """增加订单计数"""
        self.orders_total[status] = self.orders_total.get(status, 0) + 1

    def increment_studio(self, status: str):
        """增加工作室计数"""
        self.studios_total[status] = self.studios_total.get(status, 0) + 1

    def increment_dispatch(self, outcome: str):
        """增加派单计数

        outcome: success | cas_failed | no_capacity | fallback
        """
        self.dispatch_total[outcome] = self.dispatch_total.get(outcome, 0) + 1

    def set_studio_load(self, studio_id: str, current_load: int):
        """设置工作室容量 Gauge

        记录工作室当前负载，用于容量利用率监控
        """
        self.studio_load_gauge[studio_id] = current_load

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式的指标"""
        lines = []

        # HTTP 请求总数
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for (method, path, status), count in self.http_requests_total.items():
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        # HTTP 请求耗时（计算 p50, p95, p99）
        if self.http_request_duration:
            durations = sorted([r["duration_ms"] for r in self.http_request_duration])
            n = len(durations)
            p50 = durations[int(n * 0.5)]
            p95 = durations[int(n * 0.95)]
            p99 = durations[int(n * 0.99)]
            avg = sum(durations) / n

            lines.append("")
            lines.append("# HELP http_request_duration_ms HTTP request duration")
            lines.append("# TYPE http_request_duration_ms summary")
            lines.append(f'http_request_duration_ms{{quantile="0.5"}} {p50:.2f}')
            lines.append(f'http_request_duration_ms{{quantile="0.95"}} {p95:.2f}')
            lines.append(f'http_request_duration_ms{{quantile="0.99"}} {p99:.2f}')
            lines.append(f'http_request_duration_ms_sum {sum(durations):.2f}')
            lines.append(f'http_request_duration_ms_count {n}')
            lines.append(f'http_request_duration_ms_avg {avg:.2f}')

        # 任务指标
        lines.append("")
        lines.append("# HELP tasks_total Total tasks by state")
        lines.append("# TYPE tasks_total counter")
        for state, count in self.tasks_total.items():
            lines.append(f'tasks_total{{state="{state}"}} {count}')

        # 支付指标
        lines.append("")
        lines.append("# HELP payments_total Total payments by status")
        lines.append("# TYPE payments_total counter")
        for status, count in self.payments_total.items():
            lines.append(f'payments_total{{status="{status}"}} {count}')

        # 订单指标
        lines.append("")
        lines.append("# HELP orders_total Total orders by status")
        lines.append("# TYPE orders_total counter")
        for status, count in self.orders_total.items():
            lines.append(f'orders_total{{status="{status}"}} {count}')

        # 工作室指标
        lines.append("")
        lines.append("# HELP studios_total Total studios by status")
        lines.append("# TYPE studios_total counter")
        for status, count in self.studios_total.items():
            lines.append(f'studios_total{{status="{status}"}} {count}')

        # 派单指标
        lines.append("")
        lines.append("# HELP dispatch_total Total dispatch attempts by outcome")
        lines.append("# TYPE dispatch_total counter")
        for outcome, count in self.dispatch_total.items():
            lines.append(f'dispatch_total{{outcome="{outcome}"}} {count}')

        # 工作室容量 Gauge
        lines.append("")
        lines.append("# HELP studio_load_gauge Current load of each studio")
        lines.append("# TYPE studio_load_gauge gauge")
        for studio_id, load in self.studio_load_gauge.items():
            lines.append(f'studio_load_gauge{{studio_id="{studio_id}"}} {load}')

        # 活跃连接
        lines.append("")
        lines.append("# HELP active_sse_connections Active SSE connections")
        lines.append("# TYPE active_sse_connections gauge")
        lines.append(f'active_sse_connections {self.active_sse_connections}')

        lines.append("")
        lines.append("# HELP active_workers Active worker processes")
        lines.append("# TYPE active_workers gauge")
        lines.append(f'active_workers {self.active_workers}')

        return "\n".join(lines) + "\n"


# 全局指标实例
metrics = MetricsRegistry()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus 指标采集中间件

    Phase Q7.2.1: HTTP 请求指标采集
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过 metrics 端点本身（避免循环）
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        # 处理请求
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # 记录指标
            # 简化路径（移除参数化部分）
            path_template = self._normalize_path(request.url.path)

            metrics.increment_http_request(
                method=request.method,
                path=path_template,
                status=response.status_code,
            )
            metrics.record_http_duration(
                method=request.method,
                path=path_template,
                duration_ms=duration_ms,
            )

            return response

        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            path_template = self._normalize_path(request.url.path)

            metrics.increment_http_request(
                method=request.method,
                path=path_template,
                status=500,
            )
            metrics.record_http_duration(
                method=request.method,
                path=path_template,
                duration_ms=duration_ms,
            )
            raise

    def _normalize_path(self, path: str) -> str:
        """规范化路径，将 UUID 等参数替换为占位符"""
        import re
        # 替换 UUID
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path
        )
        # 替换数字 ID
        path = re.sub(r'/\d+', '/{id}', path)
        return path


def get_metrics() -> MetricsRegistry:
    """获取指标注册表实例"""
    return metrics
