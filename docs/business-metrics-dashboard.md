# 业务监控仪表盘配置指南

## 背景

当前 Prometheus 指标偏重基础设施（HTTP 请求、数据库连接），缺少业务维度的可观测性。本次补强在关键业务流程中埋点，暴露业务指标供监控和告警。

---

## 一、新增业务指标埋点

### 1.1 订单指标 (`orders_total`)

**指标类型**: Counter（累计计数）

**标签**: `status` — 订单状态

**埋点位置**:

| 状态 | 埋点位置 | 说明 |
|------|---------|------|
| `pending` | `app/api/options.py:258` | 用户确认设计，创建订单 |
| `dispatched` | `app/api/payments.py:201` | 支付成功，进入派单流程 |
| `dispatched_to_studio` | `app/services/dispatch/dispatcher.py:150` | 派单成功，分配工作室 |
| `cancelled` | `app/services/order/order_service.py:165` | 订单取消 |

**查询示例**:

```promql
# 每小时新增订单数
rate(orders_total{status="pending"}[1h]) * 3600

# 派单成功率（最近 24h）
sum(rate(orders_total{status="dispatched_to_studio"}[24h]))
/
sum(rate(orders_total{status="dispatched"}[24h]))

# 订单取消率
sum(rate(orders_total{status="cancelled"}[24h]))
/
sum(rate(orders_total[24h]))
```

### 1.2 支付指标 (`payments_total`)

**指标类型**: Counter

**标签**: `status` — 支付状态

**埋点位置**:

| 状态 | 埋点位置 | 说明 |
|------|---------|------|
| `success` | `app/api/payments.py:201` | 支付宝回调成功 |

**查询示例**:

```promql
# 每小时支付成功数
rate(payments_total{status="success"}[1h]) * 3600

# 支付成功金额（需补充 amount 标签或独立指标）
# 当前未收集，建议后续添加 payments_amount_total
```

### 1.3 任务指标 (`tasks_total`)

**指标类型**: Counter

**标签**: `state` — 任务状态

**埋点位置**:

| 状态 | 埋点位置 | 说明 |
|------|---------|------|
| `pending` / `running` / `completed` / `failed` | `app/services/tasks/task_service.py:177` | 任务状态更新（AI 生图、工艺匹配等） |

**查询示例**:

```promql
# 任务完成率
sum(rate(tasks_total{state="completed"}[1h]))
/
sum(rate(tasks_total[1h]))

# 任务失败数（告警阈值）
rate(tasks_total{state="failed"}[5m]) > 10
```

---

## 二、Prometheus 指标导出端点

### 端点

```
GET /metrics
```

返回 Prometheus 标准文本格式：

```
# HELP orders_total Total orders by status
# TYPE orders_total counter
orders_total{status="pending"} 42
orders_total{status="dispatched"} 35
orders_total{status="dispatched_to_studio"} 30
orders_total{status="cancelled"} 7

# HELP payments_total Total payments by status
# TYPE payments_total counter
payments_total{status="success"} 35

# HELP tasks_total Total tasks by state
# TYPE tasks_total counter
tasks_total{state="completed"} 128
tasks_total{state="failed"} 3
```

### Prometheus 采集配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'claywords-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

---

## 三、Grafana 仪表盘配置

### 3.1 核心业务面板

#### 面板 1: 订单漏斗（Funnel）

```promql
# 创单数（每小时）
sum(increase(orders_total{status="pending"}[1h]))

# 支付数（每小时）
sum(increase(orders_total{status="dispatched"}[1h]))

# 派单成功数（每小时）
sum(increase(orders_total{status="dispatched_to_studio"}[1h]))

# 取消数（每小时）
sum(increase(orders_total{status="cancelled"}[1h]))
```

**可视化**: Bar gauge（横向条形图），显示各阶段转化

#### 面板 2: 派单成功率（时间序列）

```promql
# 派单成功率（滚动 1h）
sum(rate(orders_total{status="dispatched_to_studio"}[1h]))
/
sum(rate(orders_total{status="dispatched"}[1h]))
```

**可视化**: Graph（折线图），Y 轴范围 0-1，添加 0.7 告警线

#### 面板 3: 支付成功数（时间序列）

```promql
sum(rate(payments_total{status="success"}[5m])) * 300
```

**可视化**: Graph，单位 "payments / 5min"

#### 面板 4: 任务状态分布（饼图）

```promql
sum by (state) (rate(tasks_total[1h]))
```

**可视化**: Pie chart，按 `state` 分组

#### 面板 5: 订单取消率（单值）

```promql
sum(rate(orders_total{status="cancelled"}[24h]))
/
sum(rate(orders_total[24h]))
```

**可视化**: Stat（单值面板），阈值：>5% 橙色，>10% 红色

### 3.2 告警规则

```yaml
# alerting_rules.yml
groups:
  - name: business_alerts
    interval: 1m
    rules:
      - alert: HighOrderCancellationRate
        expr: |
          sum(rate(orders_total{status="cancelled"}[1h]))
          /
          sum(rate(orders_total[1h]))
          > 0.15
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "订单取消率过高 ({{ $value | humanizePercentage }})"
          description: "最近 1h 订单取消率超过 15%，可能存在用户体验问题"

      - alert: LowDispatchSuccessRate
        expr: |
          sum(rate(orders_total{status="dispatched_to_studio"}[1h]))
          /
          sum(rate(orders_total{status="dispatched"}[1h]))
          < 0.7
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "派单成功率过低 ({{ $value | humanizePercentage }})"
          description: "最近 1h 派单成功率低于 70%，工作室容量不足或匹配算法异常"

      - alert: HighTaskFailureRate
        expr: |
          sum(rate(tasks_total{state="failed"}[5m]))
          /
          sum(rate(tasks_total[5m]))
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "任务失败率过高 ({{ $value | humanizePercentage }})"
          description: "最近 5min 任务失败率超过 10%，检查 AI 服务或工艺匹配服务"
```

---

## 四、缺失指标与后续改进

### 4.1 当前未覆盖的业务维度

| 指标 | 用途 | 实现建议 |
|------|------|---------|
| **订单金额** | GMV、客单价 | 新增 `orders_amount_total{status}` (Counter)，埋点位置同 `orders_total` |
| **工作室容量利用率** | 派单优化 | 新增 `studio_capacity_utilization{studio_id}` (Gauge)，定时采集 `current_load / capacity` |
| **设计生成耗时** | 性能优化 | 复用 `tasks_duration`，按 `task_type` 标签区分 |
| **支付回调延迟** | 支付体验 | 新增 `payment_callback_delay_seconds` (Histogram)，记录 `支付成功时间 - 订单创建时间` |
| **用户留存** | 产品迭代 | 需日志聚合（Prometheus 不适合存储高基数用户 ID），建议用 Clickhouse |

### 4.2 升级到 `prometheus_client` 库

**当前实现**: 简化版自定义指标（`app/core/metrics.py`），内存字典存储，无持久化。

**问题**:
- 重启服务后指标清零（Counter 应单调递增）
- 不支持 Histogram / Summary（无法计算百分位数）
- 并发写入无锁保护

**迁移方案**:

```python
# requirements.txt 添加
prometheus-client>=0.19.0

# app/core/metrics.py 重构
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

registry = CollectorRegistry()

orders_total = Counter(
    'orders_total',
    'Total orders by status',
    ['status'],
    registry=registry
)

payments_total = Counter(
    'payments_total',
    'Total payments by status',
    ['status'],
    registry=registry
)

tasks_total = Counter(
    'tasks_total',
    'Total tasks by state',
    ['state'],
    registry=registry
)

# 导出端点
from prometheus_client import generate_latest

@router.get("/metrics")
async def metrics_endpoint():
    return Response(
        content=generate_latest(registry),
        media_type="text/plain; version=0.0.4"
    )
```

**优势**:
- 原子操作保证并发安全
- 支持 Histogram（如 `tasks_duration_seconds`）
- 社区标准，集成生态完善（如 `prometheus_fastapi_instrumentator`）

---

## 五、验证清单

### 本地验证

```bash
# 1. 启动后端
cd backend
uvicorn app.main:app --reload

# 2. 访问 metrics 端点
curl http://localhost:8000/metrics | grep -E "orders_total|payments_total|tasks_total"

# 预期输出（初始值）
# orders_total{status="pending"} 0
# orders_total{status="dispatched"} 0
# payments_total{status="success"} 0
# tasks_total{state="completed"} 0

# 3. 触发业务操作
# - 创建订单：POST /api/v1/options/sessions/{session_id}/confirm
# - 模拟支付回调：POST /api/v1/payments/callback
# - 取消订单：POST /api/v1/orders/{order_id}/cancel

# 4. 再次查看 metrics，计数应增加
curl http://localhost:8000/metrics | grep orders_total
# orders_total{status="pending"} 1
# orders_total{status="cancelled"} 1
```

### Prometheus 集成验证

```bash
# 1. 配置 Prometheus 采集目标（见上文 prometheus.yml）

# 2. 访问 Prometheus UI
http://localhost:9090/targets
# 确认 claywords-backend 状态为 UP

# 3. 查询指标
# Expression: orders_total
# 应看到多个 series（按 status 标签分组）

# 4. 验证告警规则
http://localhost:9090/alerts
# 确认 HighOrderCancellationRate 等规则已加载
```

### Grafana 仪表盘验证

```bash
# 1. 导入仪表盘 JSON（见附录或 Grafana 官方库）
# 2. 配置 Prometheus 数据源
# 3. 检查各面板是否有数据
```

---

## 六、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/api/options.py` | 新增埋点 | 订单创建后 `metrics.increment_order("pending")` |
| `app/api/payments.py` | 新增埋点 | 支付成功后 `metrics.increment_payment("success")` + `metrics.increment_order("dispatched")` |
| `app/services/order/order_service.py` | 新增埋点 | 订单取消后 `metrics.increment_order("cancelled")` |
| `app/services/dispatch/dispatcher.py` | 新增埋点 | 派单成功后 `metrics.increment_order("dispatched_to_studio")` |
| `app/services/tasks/task_service.py` | 新增埋点 | 任务状态更新后 `metrics.increment_task(state)` |

---

## 七、后续迭代

### Phase 1（当前完成）
- ✅ 订单/支付/任务核心指标埋点
- ✅ `/metrics` 端点已存在，新增指标自动导出
- ✅ 文档化 Grafana 仪表盘配置与告警规则

### Phase 2（短期）
- 补充 `orders_amount_total` 收集订单金额
- 补充 `studio_capacity_utilization` 工作室利用率
- 迁移到 `prometheus_client` 库（原子操作 + Histogram 支持）

### Phase 3（中期）
- 日志聚合（Loki）+ 指标关联（Tempo）实现 APM
- 用户行为分析（Clickhouse）+ 业务指标联动
- 自定义仪表盘模板（按角色：运营/技术/产品）

---

## 八、参考资源

- [Prometheus 最佳实践](https://prometheus.io/docs/practices/naming/)
- [Grafana 仪表盘示例](https://grafana.com/grafana/dashboards/)
- [FastAPI Prometheus Instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)
- [Alertmanager 配置指南](https://prometheus.io/docs/alerting/latest/configuration/)
