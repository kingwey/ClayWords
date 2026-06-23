# ClayWords SLO 定义与监控

> Service Level Objectives (服务等级目标) — 2026-06-23
>
> 本文档定义 ClayWords 的核心 SLO,对应的监控指标,以及告警阈值。

---

## 一、核心 SLO 指标

| SLO | 目标 | 监控指标 | 告警阈值 | 级别 |
|---|---|---|---|---|
| **可用性** | 99.5% | `http_requests_total` 5xx 占比 | > 0.5% 持续 2min | P0 |
| **API 延迟 p99** | < 800ms | `http_request_duration_ms` p99 | > 800ms 持续 5min | P1 |
| **支付成功率** | ≥ 99% | `payments_total{status="success"}` 占比 | < 99% 持续 5min | P1 |
| **派单成功率** | ≥ 90% | `dispatch_total{outcome="success"}` 占比 | < 90% 持续 5min | P1 |
| **数据库查询** | < 200ms 平均 | `db_query_duration_ms` 平均 | > 200ms 持续 5min | P1 |

---

## 二、告警分级策略

### P0 - Critical (关键)
**影响**: 核心服务不可用,用户无法完成关键流程(登录/下单/支付)

**响应时间**: 5 分钟内响应,15 分钟内缓解

**通知渠道**:
- 电话 (腾讯云/阿里云语音通知,自动拨打 oncall 手机)
- 短信 (多人并发,确保送达)
- 飞书群 @all

**触发条件**:
- HTTP 5xx 错误率 > 0.5% 持续 2min
- Backend 服务离线 > 1min
- 数据库连接池耗尽 (可用连接 < 2)

**示例告警**:
```
[P0] HighErrorRate
HTTP 5xx 错误率 1.2%,已持续 3 分钟
Runbook: https://docs.claywords.com/runbooks/high-error-rate
```

### P1 - High (重要)
**影响**: 服务可用但性能劣化,或业务指标异常

**响应时间**: 30 分钟内响应,2 小时内缓解

**通知渠道**:
- 飞书群 (普通消息,不 @all)

**触发条件**:
- API p99 延迟 > 800ms 持续 5min
- 支付成功率 < 99% 持续 5min
- 派单失败率 > 10% 持续 5min
- 数据库查询平均 > 200ms 持续 5min
- SSE 活跃连接 > 1000

**示例告警**:
```
[P1] LowPaymentSuccessRate
过去 10 分钟支付成功率 97.3% (SLO: ≥99%)
Runbook: https://docs.claywords.com/runbooks/payment-failure
```

### P2 - Medium (次要)
**影响**: 资源接近饱和或业务趋势异常,但未影响当前服务

**响应时间**: 工作时间内响应,1 工作日内处理

**通知渠道**:
- 邮件 (ops@claywords.com)

**触发条件**:
- 内存使用率 > 85% 持续 5min
- CPU 使用率 > 80% 持续 10min
- 磁盘剩余 < 15%
- 过去 30 分钟无新订单

**示例告警**:
```
[P2] HighMemoryUsage
backend-pod-1 内存使用 87%
建议: 检查内存泄漏或扩容
```

---

## 三、SLO 计算方法

### 可用性 (Availability)
```promql
# 成功请求占比
sum(rate(http_requests_total{status!~"5.."}[30d]))
/
sum(rate(http_requests_total[30d]))

# 目标: >= 0.995 (99.5%)
```

**错误预算 (Error Budget)**:
- 每月允许 0.5% 请求失败
- 按 1M 请求/月算,允许 5K 次失败
- 预算耗尽 → 冻结新功能发布,全力稳定性

### API 延迟 (Latency)
```promql
# p99 延迟
histogram_quantile(0.99,
  rate(http_request_duration_ms_bucket[5m])
)

# 目标: < 800ms
```

### 支付成功率 (Payment Success Rate)
```promql
# 支付成功占比
sum(rate(payments_total{status="success"}[10m]))
/
sum(rate(payments_total[10m]))

# 目标: >= 0.99 (99%)
```

### 派单成功率 (Dispatch Success Rate)
```promql
# 派单成功占比
sum(rate(dispatch_total{outcome="success"}[10m]))
/
sum(rate(dispatch_total[10m]))

# 目标: >= 0.90 (90%)
```

---

## 四、Runbook 链接

| 告警名称 | Runbook | 常见原因 | 快速修复 |
|---|---|---|---|
| HighErrorRate | [链接](#) | DB 连接超时/下游服务挂 | 重启 pod/扩容/降级 |
| ServiceDown | [链接](#) | OOM/Crash/部署失败 | kubectl rollback |
| HighLatencyP99 | [链接](#) | 慢查询/GC 停顿 | 查 slow log/调优 |
| LowPaymentSuccessRate | [链接](#) | 支付宝接口抖动/验签失败 | 检查 API key/网络 |
| HighDispatchFailureRate | [链接](#) | 工作室容量满/评分算法 bug | 人工派单/调整阈值 |
| DatabaseConnectionPoolExhausted | [链接](#) | 慢查询堆积/连接泄漏 | kill 长事务/扩池 |

---

## 五、监控仪表盘

**Grafana 面板** (见 [business-metrics-dashboard.md](business-metrics-dashboard.md)):
1. **SLO 总览** - 可用性/延迟/支付/派单 4 个核心指标实时趋势
2. **错误预算燃烧率** - 当前消耗速度,预计何时耗尽
3. **告警热力图** - P0/P1/P2 分布,按时间/类别聚合
4. **业务漏斗** - 订单创建 → 支付 → 派单 → 完成的转化率

**Prometheus 查询示例**:
```promql
# 错误预算剩余百分比
1 - (
  sum(rate(http_requests_total{status=~"5.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
) / 0.005
```

---

## 六、SLO 审查机制

- **周会**: 每周一回顾上周 SLO 达成情况,分析未达标原因
- **月报**: 每月生成 SLO 报告(可用性/延迟/业务指标趋势)
- **季度复盘**: 每季度调整 SLO 目标(根据业务增长/用户反馈)

**SLO 变更流程**:
1. 提出变更(附数据支撑)
2. 团队评审(影响面/成本/优先级)
3. 更新本文档 + 告警规则
4. 周知全员 + 更新 Runbook

---

**维护者**: OPS Team  
**最后更新**: 2026-06-23  
**关联文档**: [next-steps-2026-06-23.md](next-steps-2026-06-23.md) · [business-metrics-dashboard.md](business-metrics-dashboard.md)
