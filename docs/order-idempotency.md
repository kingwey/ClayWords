# Order 幂等性机制梳理

## 背景

当前存在两个幂等性机制，职责存在重叠与混淆：
1. **`Order.idempotency_key`** — Order 表的唯一索引字段
2. **`IdempotencyKey` 表** — 独立的幂等性键持久化表

本文档梳理两者的实际用途、设计初衷、重叠点与改进建议。

---

## 一、Order.idempotency_key

### Schema 定义
```python
# app/models/entities.py
class Order(Base):
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
```

- **类型**: `String(64)`，唯一索引
- **强制**: `nullable=False`
- **用途**: 防止同一设计选项重复创建订单

### 使用场景

**仅在创单场景**: `/api/v1/options/confirm`

```python
# app/api/options.py:187
idempotency_key = request.option_id  # 直接用 option_id（设计方案 ID）

# 查询是否已存在相同 idempotency_key 的订单
existing_order = session.execute(
    select(OrderModel).where(OrderModel.idempotency_key == idempotency_key)
).scalar_one_or_none()

if existing_order:
    return ConfirmResponse(order_id=existing_order.order_id)  # 幂等返回

# 创建新订单
new_order = OrderModel(idempotency_key=idempotency_key, ...)
```

### 设计初衷

**目标**: 防止用户在前端重复点击「确认下单」按钮时，创建多个订单。

**实现方式**: 
- `idempotency_key = option_id`（设计方案 ID）
- 利用数据库唯一索引自然防止重复插入
- 重复请求返回已存在的订单（不报错）

### 优势
- ✅ 简单直接，利用数据库唯一约束天然防重
- ✅ 查询性能好（唯一索引）
- ✅ 无需额外清理机制（订单本身是长期保留的）

### 局限
- ❌ **与业务实体绑定**: 只能用于 Order，无法推广到其他资源（如 Task、Design）
- ❌ **key 生成规则分散**: 当前 `idempotency_key = option_id`，若后续有其他创单入口（如「重新下单」），需要重新设计 key 生成逻辑
- ❌ **缺少 TTL**: 订单永久保留，幂等性无过期时间（业务上合理，但理论上用户一年后用同一设计下单应该创建新订单）

---

## 二、IdempotencyKey 表

### Schema 定义
```python
# app/models/entities.py
class IdempotencyKey(Base):
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    response_body: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- **key**: 主键，幂等性标识
- **resource_id**: 关联资源 ID（如 `order_id`、`trade_no`）
- **resource_type**: 资源类型（如 `payment_callback`）
- **response_body**: 缓存的响应内容（JSONB）
- **expires_at**: 过期时间（支持 TTL）

### 使用场景

**仅在支付回调场景**: `/api/v1/payments/callback`

```python
# app/api/payments.py:155
idempotency_key = f"payment_callback_{trade_no}"  # 支付宝交易号

# 查询是否已处理过
existing = session.execute(
    select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
).scalar_one_or_none()

if existing:
    return "success"  # 幂等返回，避免支付宝重复回调

# 记录幂等性键
idem_key = IdempotencyKey(
    key=idempotency_key,
    resource_id=out_trade_no,  # 订单号
    resource_type="payment_callback",
    response_body={"trade_no": trade_no, "trade_status": trade_status, ...},
    expires_at=utcnow() + timedelta(days=7)
)
session.add(idem_key)

# 处理订单状态迁移（pending → dispatched）
```

### 设计初衷

**目标**: 防止支付宝重复回调时，多次修改订单状态或重复发送通知。

**实现方式**:
- `key = f"payment_callback_{trade_no}"`（支付宝交易号）
- 首次回调时插入 `IdempotencyKey` 记录，后续回调检测到记录存在则直接返回 `"success"`
- 支持 TTL（7 天后过期，可定期清理）

### 优势
- ✅ **通用性强**: 可用于任意异步回调、webhook、重试场景（不限于支付）
- ✅ **支持 TTL**: `expires_at` 字段明确过期时间，可定期清理历史记录
- ✅ **缓存响应**: `response_body` 可用于重放响应（虽然当前场景未用到）
- ✅ **解耦业务逻辑**: 不污染 Order 表，幂等性检查独立

### 局限
- ❌ **额外表查询**: 每次回调需额外查询 `IdempotencyKey` 表（vs `Order.idempotency_key` 利用唯一索引查询订单时顺带检查）
- ❌ **需要主动清理**: `expires_at` 过期后需要定时任务清理，否则表膨胀

---

## 三、对比分析

| 维度 | Order.idempotency_key | IdempotencyKey 表 |
|------|----------------------|------------------|
| **使用场景** | 创单（/options/confirm） | 支付回调（/payments/callback） |
| **幂等性粒度** | 订单级别（防止重复下单） | 操作级别（防止重复处理回调） |
| **key 生成** | `option_id`（设计方案 ID） | `payment_callback_{trade_no}` |
| **TTL** | 无（订单永久保留） | 有（7 天） |
| **通用性** | 绑定 Order 表 | 可用于任意资源 |
| **查询成本** | 利用唯一索引（高效） | 额外表查询 |
| **清理机制** | 无需清理 | 需定时清理过期记录 |
| **响应缓存** | 无 | 支持（response_body 字段） |

---

## 四、职责边界建议

### 当前职责划分（实际运行中）

✅ **职责清晰，无冲突**:
- `Order.idempotency_key`: 防止用户重复下单（创单幂等）
- `IdempotencyKey` 表: 防止支付回调重复处理（异步回调幂等）

两者服务于不同的业务场景，**无职责重叠**。

### 未来扩展场景

#### 场景 1: 重新下单（同一设计多次下单）

**当前行为**: `idempotency_key = option_id` 会阻止同一设计重复下单。

**问题**: 用户一年后用同一设计下单，应该创建新订单，但当前会返回旧订单。

**方案**:
1. **改 key 生成逻辑**: `idempotency_key = f"{option_id}_{user_id}_{timestamp_window}"`
   - 例如按天分桶：`f"{option_id}_{user_id}_{date.today().isoformat()}"`
   - 或加随机数（前端生成）：`f"{option_id}_{client_request_id}"`
2. **保持现状**: 如果业务上认为「同一设计只能下单一次」是合理的，无需改动

#### 场景 2: 其他异步回调（微信支付、第三方 API webhook）

**推荐**: 复用 `IdempotencyKey` 表，统一管理所有异步回调的幂等性。

```python
# 例：微信支付回调
idempotency_key = f"wechat_callback_{transaction_id}"
# 例：AI 生成完成回调
idempotency_key = f"ai_task_callback_{task_id}"
```

#### 场景 3: 同步 API 幂等性（如 POST /orders）

**问题**: 若未来直接暴露创单 API（不通过 /options/confirm），如何防重？

**方案**:
1. **沿用 `Order.idempotency_key`**: 要求前端传 `idempotency_key`，后端插入前检查
2. **改用 `IdempotencyKey` 表**: 更通用，但查询成本略高

**权衡**: 
- 若幂等性检查与资源创建同时进行 → 用 `Order.idempotency_key`（一次查询）
- 若幂等性检查需独立于资源创建（如先返回 202，异步处理）→ 用 `IdempotencyKey` 表

---

## 五、改进建议

### 短期（保持现状）

✅ **无需改动**: 当前两个机制职责清晰，无冲突，代码可维护性良好。

**补充文档**:
- 在 `Order` 和 `IdempotencyKey` 模型注释中明确各自职责
- 在 `/options/confirm` 和 `/payments/callback` 端点注释中说明幂等性实现方式

### 中期（统一 key 生成规则）

**问题**: 当前 key 生成逻辑散落在业务代码中（`options.py:187`、`payments.py:155`）。

**方案**: 抽取工具函数统一管理

```python
# app/core/idempotency.py
def generate_order_idempotency_key(option_id: str, user_id: str) -> str:
    """创单幂等性 key: 同一用户+同一设计当天内只能下单一次"""
    from datetime import date
    return f"order_{option_id}_{user_id}_{date.today().isoformat()}"

def generate_payment_callback_key(trade_no: str) -> str:
    """支付回调幂等性 key"""
    return f"payment_callback_{trade_no}"
```

**优势**:
- 集中管理 key 生成规则，便于后续调整
- 文档化（函数注释说明 key 语义）

### 长期（统一幂等性框架）

**目标**: 所有需要幂等性的 API 都走统一流程。

**方案**: 参考 Stripe API 设计，前端传 `Idempotency-Key` header，后端中间件拦截。

```python
# 前端
axios.post('/api/v1/orders', payload, {
    headers: { 'Idempotency-Key': uuidv4() }
})

# 后端中间件
@app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    idem_key = request.headers.get("Idempotency-Key")
    if idem_key and request.method in ["POST", "PUT", "PATCH"]:
        # 查询 IdempotencyKey 表
        existing = await get_idempotency_record(idem_key)
        if existing:
            return JSONResponse(existing.response_body, status_code=existing.status_code)
        
        # 执行业务逻辑
        response = await call_next(request)
        
        # 缓存响应
        await save_idempotency_record(idem_key, response)
        return response
    
    return await call_next(request)
```

**优势**:
- 业务代码无需关心幂等性检查（框架层透明处理）
- 前端统一传 `Idempotency-Key`，后端自动防重

**劣势**:
- 响应缓存需要序列化（大文件、流式响应不适用）
- 增加复杂度（并非所有 API 都需要幂等性）

**建议**: 仅在高频重试场景（支付、创单）按需实现，不追求全局统一。

---

## 六、当前状态评估

### ✅ 优点
1. **职责清晰**: 创单用 `Order.idempotency_key`，支付回调用 `IdempotencyKey` 表，无重叠
2. **简单有效**: 两个机制都实现了各自场景的幂等性需求
3. **可维护**: 代码逻辑直观，无过度设计

### ⚠️ 潜在问题
1. **key 生成规则缺少文档**: 散落在业务代码中，新人难以理解
2. **Order.idempotency_key 无 TTL**: 用户一年后用同一设计下单会返回旧订单（需确认是否符合业务预期）
3. **IdempotencyKey 表缺少清理任务**: `expires_at` 过期后未主动清理（依赖手动或 DB 自动归档）

### 🔧 建议行动
1. **文档补充**: 在模型和端点注释中说明幂等性实现（本文档可作为附录）
2. **key 生成规则**: 抽取工具函数，集中管理（中期改进）
3. **清理任务**: 添加定时任务清理 `IdempotencyKey` 表过期记录（或用 `partman` 自动归档）

---

## 七、结论

**当前两个幂等性机制设计合理，无需重构**。

- `Order.idempotency_key`: 专用于创单防重，利用数据库唯一索引高效实现
- `IdempotencyKey` 表: 通用异步回调防重，支持 TTL 和响应缓存

**短期无需改动，中期建议补充文档和工具函数，长期可考虑统一框架（但非必需）**。
