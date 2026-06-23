# ClayWords 推进路线 — 2026-06-23

> 本文档基于 2026-06-23 的代码库实测,**修正旧规划文档(`project-analysis.md` / `roadmap-v2.md` / `mvp-sprint-plan.md`)中已与实际脱节的判断**,给出未来 4 周的推进顺序与决策点。
>
> 旧规划仍可作为任务粒度的参考,但**优先级与完成度判断以本文档为准**。

---

## 一、现状摘要(规划 vs 实际)

| 维度 | 旧规划判断 | 2026-06-23 实测 | 结论 |
|---|---|---|---|
| 后端完成度 | 95% | ✅ 95%(技术债已大幅清理) | 一致 |
| 前端完成度 | **0% / 仅骨架** | ⚠️ **用户端已有 4 views + 6 components + 路由 + API;工作室端/管理后台未实现** | **用户端基本完成** |
| Hunyuan3D 接入 | 待开发(Phase Q3, 12 天) | ✅ 后端 617 行已落地;前端未集成 | **后端已完成** |
| 时区迁移 | 已完成 | ✅ 代码完成;**alembic 未在 DB 执行** | 落地未闭环 |
| HttpOnly Cookie | 已完成 | ✅ 前后端就绪 | 一致 |
| CI 覆盖率门槛 | 已完成 | ✅ pytest.ini 70% | 一致 |
| 业务监控埋点 | 已完成(commit 54f2db0) | ✅ 已有 6 处埋点(dispatcher/order/task/payment);**覆盖率需提升** | 部分完成 |
| 生产环境 | 配置完成 | ❌ **无 K8s 集群、无域名、无 TLS、无密钥注入** | **未部署** |
| 单元测试数 | 77 个 | ✅ 77 个(pytest collect 实测,含参数化展开) | 一致 |

**核心结论**:后端比规划文档显示的更成熟(技术债已清),前端比规划文档显示的远超预期(主要 view/component 已写完),**真正的瓶颈是部署落地 + 业务埋点闭环**,而不是新功能开发。

---

## 二、关键差距(必须先解决的 3 件事)

### 差距 1 · 业务监控埋点覆盖不全

`backend/app/core/metrics.py` 已定义 `MetricsRegistry` 与 6 类业务指标,**已有 6 处埋点**:
- `app/services/dispatch/dispatcher.py:151` - 派单成功(`dispatched_to_studio`)
- `app/services/order/order_service.py:166` - 订单取消
- `app/services/tasks/task_service.py:179` - 任务状态变更
- `app/api/options.py:259` - 订单创建(`pending`)
- `app/api/payments.py:200-201` - 支付成功 + 订单派单

**仍缺失**:
- 派单失败路径(CAS 冲突/无可用工作室)未埋点
- 工作室容量(`Studio.current_load`)变更未用 Gauge 记录
- 支付失败/验签失败分支未埋点

**后果**:Prometheus `/metrics` 能看到部分业务指标(订单/支付/任务),但派单失败率、工作室容量利用率等关键 SLI 缺失。

**修复成本**:0.5-1 小时补齐剩余埋点。

### 差距 2 · 部署链路从未走通

- `helm/claywords/values-production.yaml` 已写完(3 副本 backend + 2 副本 worker + HPA)
- `.env.production` 全是 `${CRYPTO_PEPPER}` 等占位符
- 没有真实云账号、域名、TLS 证书
- alembic timezone 迁移文件 `b5e7f8a9c0d1_004_*.py` 从未执行过

**后果**:生产配置 fail-fast 校验(`config.py:_check_production_secrets`)会直接拒启,但因为没真上过线,这套防护本身也没在真实环境验证过。

**修复成本**:2-3 天(取决于云账号采购速度)。

### 差距 3 · 前端用户端基本完成,但工作室端/管理后台缺失

旧规划假设前端 0% 要花 15-20 天做 MVP,实际**用户端**:
- 4 views:`HomeView.vue`(1408 行)、`LoginView.vue`(482 行)、`DesignView.vue`(533 行)、`OrdersView.vue`(580 行)
- 6 components:`ChatPanel`(374 行)、`OptionCards`(440 行)、`PreviewCanvas`(652 行)、`DispatchPanel`(219 行)、`DispatchVisualization`、`WorkOrderPopup`
- API client 2459 行,封装了几乎所有后端端点
- 路由守卫 + Cookie 认证 + 401 自动 refresh 已联通

**仍缺失**:
- **工作室端完全未实现**(接单/拒单/发货界面不存在)
- **管理后台完全未实现**(工作室审核/订单管理/用户管理不存在)
- Hunyuan3D 任务流的前端展示(SSE 进度 + 3D 预览)
- 完整端到端联调(登录→设计→下单→支付→派单→发货→收货)从未在真实后端上跑过

**修复成本**:用户端 3D 集成 2-3 天 + 端到端联调 1-2 天;工作室端新建 5-7 天;管理后台新建 5-7 天。

---

## 三、推进路线(4 周窗口)

### Week 1 · 闭环现有交付

#### P0-1 业务埋点补齐 ⏱ 0.5 天

**当前状态**:已有 6 处埋点(订单创建/取消/派单、支付成功、任务状态)。

补齐缺失点:

| 文件 | 调用点 | 指标 |
|---|---|---|
| `app/services/dispatch/dispatcher.py` | CAS 失败/全部工作室满载分支 | `dispatch_total{outcome=cas_failed\|no_capacity}` |
| `app/api/payments.py` | 验签失败/回调异常分支 | `payments_total{result=verify_failed\|error}` |
| `app/services/dispatch/dispatcher.py` | `release_studio_capacity` 调用后 | `studio_load{studio_id=...}` (Gauge,记录 `current_load`) |

**验收**:
- `curl /metrics | grep -E '(dispatch_total|studio_load)'` 返回新增指标
- 模拟派单失败/支付验签失败后,对应计数器累加
- Grafana 业务仪表盘([business-metrics-dashboard.md](business-metrics-dashboard.md))补充派单成功率面板

#### P0-2 测试数量复核 + 报告同步 ⏱ 0.2 天

**已完成验证**:

```bash
cd backend && pytest tests/ --collect-only -q --override-ini="addopts="
# 输出: 77 tests collected, 1 error (test_craft_check.py 因缺 numpy 依赖导入失败)
```

**结论**:测试数量 77 与 [code-review-2026-06-22.md](code-review-2026-06-22.md) 声称一致。22 个函数声明通过 pytest parametrize 等机制展开为 77 个测试用例。

**后续**:补全 requirements.txt 中的 numpy 依赖,确保 test_craft_check.py 可正常收集。

#### P0-3 端到端冒烟脚本 ⏱ 1 天

写一份 `scripts/e2e_smoke.py`(或 `tests/e2e/test_full_flow.py`),覆盖:

```
登录 → 提交设计需求 → 选定方案 → 创建订单 → 触发支付回调
   → 派单 → 工作室接单 → 发货 → 物流回调 → 确认收货 → 订单 closed
```

**验收**:本地 docker-compose 起完整栈后,该脚本端到端通过。这是上生产前的最后一道地面验证。

#### P0-4 Hunyuan3D 前端联通 ⏱ 2-3 天

- DesignView 把"提交需求"按钮接到 `POST /api/v1/hunyuan3d/tasks`
- 监听 SSE `/api/v1/tasks/{id}/events` 显示进度(后端已修过事件顺序漏窗口,前端 `seen_ids` 去重)
- 3D 预览用 Three.js 加载返回的 GLB(已有 `usePreviewRotation` 可复用)
- 失败/超时降级到默认 3 方案(保持 demo 路径不挂)

**验收**:DesignView 真能从"用户文字" → 看到 3D 预览。

---

### Week 2 · 上生产

#### P0-5 Phase 0 基础设施 ⏱ 2-3 天

按 [roadmap-v2.md § Phase 0](roadmap-v2.md) 执行:

- 云账号 + ACK/TKE 集群(3 master + 5 worker)
- 域名 + DNS A 记录 + cert-manager 自动签发 TLS
- 用 `openssl rand -hex 32` 生成 4 个生产密钥,通过 `kubectl create secret` 注入
- 部署到 staging 命名空间,跑 P0-3 的 e2e 冒烟
- staging 通过后再 `helm upgrade` 到 production

**验收**:[production-deploy-checklist.md](production-deploy-checklist.md) 全部勾完;`https://api.claywords.com/health` 返回 200;Grafana 看到真实流量。

#### P0-6 alembic 迁移在生产执行 ⏱ 0.5 天

```bash
# 维护窗口内
kubectl exec deploy/backend -- alembic upgrade head
```

**前置条件**:必须在 P0-5 之后,首次部署完成才能执行。验证 13 张表的 `DateTime` 列已变为 `timestamptz`。

#### P0-7 灰度发布 + 监控观察 ⏱ 1-2 天

- 先放 5% 流量(用 nginx-ingress canary)
- 看 Grafana:错误率/p99 延迟/业务计数器
- 24h 无异常再放到 100%

---

### Week 3-4 · 中期改进

#### P1-1 工艺匹配向量相似度 ⏱ 3-4 天

按 [craft-vector-similarity.md](craft-vector-similarity.md) 执行,把 `services/dispatch/scoring.py` 的 substring 匹配换成 pgvector 余弦相似度。前置:LLM embedding 服务可用性确认。

**收益**:消除"白瓷"/"薄胎白瓷"/"釉下彩白瓷"互相误中的派单漂移。

#### P1-2 工作室端开发 ⏱ 5-7 天

**当前状态**:工作室端 views 不存在。

**任务清单**:
- [ ] 新建 `StudioLoginView.vue` (复用用户端登录组件,role 判断跳转)
- [ ] 新建 `StudioOrdersView.vue` - 订单列表(已派单 + 已接单 + 制作中 + 已发货)
- [ ] 新建 `StudioOrderDetailView.vue` - 接单/拒单/发货功能(录入物流单号)
- [ ] 路由守卫判断 `role=studio`,非工作室用户拒绝访问

**交付物**:
- ✅ 工作室可查看派发的订单
- ✅ 可接单和发货

**负责人**: FE (1 人)  
**预计时间**: 5-7 天

#### P1-3 管理后台开发 ⏱ 5-7 天

**当前状态**:管理后台 views 不存在。

**任务清单**:
- [ ] 新建 `AdminDashboardView.vue` - 数据概览(订单量/GMV/工作室数/用户数)
- [ ] 新建 `AdminStudiosView.vue` - 工作室审核列表(待审核/已通过/已拒绝)
- [ ] 新建 `AdminOrdersView.vue` - 订单干预(取消/退款/重新派单)
- [ ] 新建 `AdminUsersView.vue` - 用户管理(封禁/解封)
- [ ] 路由守卫判断 `role=admin`

**交付物**:
- ✅ 管理员可审核工作室
- ✅ 可查看和干预订单

**负责人**: FE (1 人)  
**预计时间**: 5-7 天

#### P1-3 物流真实快递 API 集成 ⏱ 2 天

当前物流是 mock。接入顺丰/中通某一家的查询 API,把订单 `tracking_number` 实时同步到 `LogisticsEvent` 表。

#### P1-4 SLO + 告警分级 ⏱ 1-2 天

定义 SLO 表(可用性 99.5%、p99 < 800ms、支付成功率 ≥ 99%),Prometheus alertmanager 按 P0/P1/P2 分级路由(P0 → 电话/短信,P1 → 飞书,P2 → 邮件)。

#### P2-1 测试覆盖率提升 ⏱ 持续

当前门槛 70%,逐步提到 80%。重点补:
- `app/api/` 各端点的 401/403/422 分支(目前主要测 happy path)
- `app/services/dispatch/` 的并发场景(用 `asyncio.gather` 模拟抢单)
- `app/api/payments.py` 的回调验签失败/重放/异常签名分支

---

## 四、风险清单

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| 生产密钥泄漏 | 误把 `.env.production` 真值提交 git | `.gitignore` 已包含;`pre-commit` 加 `gitleaks` |
| alembic 迁移在生产卡住 | 表大且 `ALTER COLUMN` 锁表 | 维护窗口执行;若超时改用 `pg_repack` 或临时表方案 |
| Hunyuan3D API 配额/计费 | 真实流量打满 | 后端已有 `ENABLE_HUNYUAN3D` 开关 + `MAX_POLL_ATTEMPTS`;前端失败降级到默认 3 方案 |
| HttpOnly Cookie 跨域 | 部署成 `app.claywords.com` + `api.claywords.com` 两域 | CORS `allow_origins` 精确匹配;Cookie `domain=.claywords.com`;前端 `withCredentials: true`(已配置) |
| SSE 在 nginx-ingress 下被缓冲 | 默认 proxy_buffering | annotation `nginx.ingress.kubernetes.io/proxy-buffering: "off"` |
| `SameSite=Lax` 仍允许 GET CSRF | 写操作误用 GET | 全项目写操作必须 POST/PUT/DELETE;后续考虑 double-submit token |
| 业务埋点漏点 | 部分分支没插桩 | P0-1 完成后,运行 e2e 冒烟,看 `/metrics` 计数器是否同步累加;不累加的就是漏点 |

---

## 五、决策点(需要业务/运营拍板)

1. **3D 生成是否进 MVP 首发**
   - 进:Week 1 P0-4 必做,上线时间多 3-5 天
   - 不进:首发用固定 3 方案,Hunyuan3D 留作 v1.1 灰度
   - **建议**:进。后端已经写完了,前端联通成本不高,首发没有 3D 等于没有核心卖点。

2. **MVP 是否包含管理后台**
   - 包含:多 3-5 天,但工作室审核可以在线
   - 不包含:工作室审核走人工 + 数据库直改
   - **建议**:不包含。先上线接 5-10 家手动审核过的工作室,管理后台 v1.1 再补。

3. **物流是否首发集成真实快递**
   - 集成:多 2 天
   - Mock:工作室手动录单号,用户看不到实时物流
   - **建议**:首发用 Mock。等真实订单跑起来再决定接哪家(顺丰最贵但最稳,中通便宜但 API 更敏感)。

4. **alembic 时区迁移在哪个时机执行**
   - 首次部署前:风险低(空表),但部署流程复杂一步
   - 首次部署后:有数据更安全(走维护窗口)
   - **建议**:首次部署前,空库直接迁,简单。

---

## 六、本周(2026-06-23 至 06-29)优先级矩阵

按"立即可做、价值最高"排序:

| # | 任务 | 时间 | 阻塞下游 |
|---|---|---|---|
| 1 | P0-1 业务埋点补齐 | 0.5 天 | P0-5 上线后立刻能看到业务指标 |
| 2 | P0-2 测试数量复核 | 0.2 天 | 文档可信度 |
| 3 | P0-3 端到端冒烟脚本 | 1 天 | P0-5 灰度前的最后地面验证 |
| 4 | P0-4 Hunyuan3D 前端联通 | 2-3 天 | 决定 1 — MVP 是否含 3D |
| 5 | P0-5 Phase 0 基础设施 | 2-3 天 | 一切上线动作的前置 |
| 6 | P0-6 alembic 生产迁移 | 0.5 天 | 时区相关数据正确性 |
| 7 | P0-7 灰度 + 观察 | 1-2 天 | 收尾 |

**Week 1 总工时估计**:6.4-9.4 天(单人按串行算)

可并行项:P0-1 / P0-2 / P0-3 / P0-4 之间无强依赖,可以两人并行(P0-4 一人,其他三项一人)。

---

## 七、跟踪机制

- 每完成一项 P0,在本文档对应 checkbox 打 ✅(写明完成日期)
- 每周五更新一次"本周做完了什么 + 下周优先级"到 [worklog-2026-06-22.md](worklog-2026-06-22.md)(或新开 worklog 文件)
- 上线后,业务指标周报作为 PMF 信号锚点

---

**作者**:Kiro · 2026-06-23  
**关联文档**:[CHANGELOG.md](CHANGELOG.md) · [roadmap-v2.md](roadmap-v2.md) · [mvp-sprint-plan.md](mvp-sprint-plan.md) · [code-review-2026-06-22.md](code-review-2026-06-22.md) · [claywords-final-report.md](claywords-final-report.md)
