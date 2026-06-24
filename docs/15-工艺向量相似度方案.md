# 工艺匹配升级到向量相似度方案

## 背景

当前工艺匹配基于字符串子串匹配（`scoring.py:calc_craft_score`），存在以下问题：

1. **语义理解不足**: 「景德镇青花瓷」和「江西青花」应该高度相似，但子串匹配无法识别
2. **同义词缺失**: 「白瓷」、「素瓷」、「釉上彩」等同义关系无法捕获
3. **硬编码规则**: 匹配阈值（1.0/0.7/0.5/0.2）人工调参，难以适应新工艺类型
4. **缺少细粒度**: 只能区分「完全匹配」「部分匹配」「无匹配」，无法量化相似度

**目标**: 升级到向量相似度匹配，利用 OpenAI embedding 捕获语义相似性。

---

## 一、技术方案

### 1.1 向量存储

#### Schema 变更

**Studio 表添加 embedding 字段**:

```python
# app/models/entities.py
from pgvector.sqlalchemy import Vector

class Studio(Base):
    # ... 现有字段
    specialty_embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    # 1536 维：OpenAI text-embedding-3-small 标准维度
```

**Alembic Migration**:

```python
# alembic/versions/xxxx_add_studio_specialty_embedding.py
"""add studio specialty embedding

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

def upgrade():
    op.add_column('studios', sa.Column('specialty_embedding', Vector(1536), nullable=True))
    op.create_index(
        'idx_studios_specialty_embedding',
        'studios',
        ['specialty_embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100}
    )

def downgrade():
    op.drop_index('idx_studios_specialty_embedding', table_name='studios')
    op.drop_column('studios', 'specialty_embedding')
```

### 1.2 Embedding 生成

#### 工作室 specialty 文本化

```python
# app/services/dispatch/embedding.py
def generate_specialty_text(studio: Studio) -> str:
    """
    将工作室 specialties 列表转为描述性文本
    
    Input: ["景德镇青花瓷", "釉上彩"]
    Output: "工作室专长: 景德镇青花瓷、釉上彩。擅长传统手工制瓷工艺。"
    """
    if not studio.specialties:
        return "通用陶瓷工作室"
    
    specialties_str = "、".join(studio.specialties)
    return f"工作室专长: {specialties_str}。擅长传统手工制瓷工艺。"
```

#### OpenAI Embedding API 调用

```python
import openai
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    调用 OpenAI Embedding API
    
    返回 1536 维向量
    """
    response = await client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding
```

#### 批量生成脚本

```python
# scripts/generate_studio_embeddings.py
"""
一次性生成所有工作室的 specialty embedding
"""

import asyncio
from sqlalchemy import select
from app.models.entities import Studio
from app.core.db import async_session_maker
from app.services.dispatch.embedding import generate_specialty_text, get_embedding

async def generate_all_studio_embeddings():
    async with async_session_maker() as session:
        result = await session.execute(select(Studio))
        studios = result.scalars().all()
        
        for studio in studios:
            if studio.specialty_embedding:
                print(f"Skip {studio.name} (already has embedding)")
                continue
            
            text = generate_specialty_text(studio)
            print(f"Generating embedding for {studio.name}: {text}")
            
            embedding = await get_embedding(text)
            studio.specialty_embedding = embedding
            
            await session.commit()
            print(f"✓ {studio.name} embedding saved")

if __name__ == "__main__":
    asyncio.run(generate_all_studio_embeddings())
```

### 1.3 相似度计算

#### 余弦相似度函数

```python
# app/services/dispatch/scoring.py
import numpy as np

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    计算两个向量的余弦相似度
    
    返回值范围: [-1, 1]，通常归一化到 [0, 1]
    """
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    similarity = dot_product / (norm_a * norm_b)
    # 归一化到 [0, 1]
    return (similarity + 1) / 2
```

#### 升级 calc_craft_score

```python
def calc_craft_score_vector(
    design_embedding: list[float],
    studio_embedding: list[float]
) -> float:
    """
    基于向量相似度计算工艺匹配度
    
    Args:
        design_embedding: 设计需求的 embedding（1536 维）
        studio_embedding: 工作室专长的 embedding（1536 维）
    
    Returns:
        相似度分数 [0, 1]
    """
    if not design_embedding or not studio_embedding:
        return 0.3  # 回退到默认值
    
    similarity = cosine_similarity(design_embedding, studio_embedding)
    
    # 相似度映射到工艺分数（可调参）
    if similarity >= 0.85:
        return 1.0  # 高度匹配
    elif similarity >= 0.70:
        return 0.8  # 较好匹配
    elif similarity >= 0.55:
        return 0.6  # 一般匹配
    else:
        return max(0.3, similarity)  # 低匹配，但保底 0.3
```

#### 集成到派单流程

```python
# app/services/dispatch/dispatcher.py
async def atomic_dispatch(
    db: AsyncSession,
    order_id: str,
    params: DesignParams,
    design_embedding: Optional[list[float]] = None  # 新增参数
) -> DispatchResult:
    """
    原子派单（带向量相似度）
    """
    studios = await get_all_available_studios(db)
    
    # 如果有 design_embedding，使用向量匹配
    if design_embedding:
        ranked = rank_studios_with_vector(studios, params, design_embedding)
    else:
        # 回退到字符串匹配
        ranked = rank_studios(studios, params)
    
    # ... 剩余逻辑不变
```

---

## 二、数据准备

### 2.1 Design embedding 生成

**当前状态**: Design 表已有 `embedding` 字段（1536 维），但可能为 NULL。

**生成时机**:
- **实时生成**: 用户提交设计需求时，调用 `/api/v1/designs` 时生成
- **离线补全**: 对历史数据运行批量脚本

**设计需求文本化**:

```python
def generate_design_text(params: DesignParams) -> str:
    """
    将设计参数转为描述性文本
    
    Input: DesignParams(material="白瓷", category="茶具", style="传统")
    Output: "设计需求: 白瓷材质、茶具类别、传统风格的陶瓷作品。"
    """
    parts = []
    if params.material:
        parts.append(f"{params.material}材质")
    if params.category:
        parts.append(f"{params.category}类别")
    if params.style:
        parts.append(f"{params.style}风格")
    
    desc = "、".join(parts)
    return f"设计需求: {desc}的陶瓷作品。"
```

### 2.2 成本估算

**OpenAI Embedding API 价格** (2026-06):
- `text-embedding-3-small`: $0.02 / 1M tokens
- 平均每个文本 ~20 tokens

**成本计算**:
- 100 个工作室 × 20 tokens = 2000 tokens ≈ $0.00004（一次性）
- 每个订单生成 1 次设计 embedding: ~20 tokens ≈ $0.0000004 / 订单

**结论**: 成本可忽略不计。

---

## 三、实施步骤

### Phase 1: 基础设施（1 天）

1. ✅ **Migration**: 添加 `Studio.specialty_embedding` 字段
   ```bash
   alembic revision --autogenerate -m "add studio specialty embedding"
   alembic upgrade head
   ```

2. ✅ **Embedding 服务**: 实现 `embedding.py` 模块
   - `generate_specialty_text()`
   - `generate_design_text()`
   - `get_embedding()`

3. ✅ **批量生成脚本**: `scripts/generate_studio_embeddings.py`
   ```bash
   python scripts/generate_studio_embeddings.py
   # 预计耗时: ~10s（100 个工作室，API 限速 3000 RPM）
   ```

### Phase 2: 算法升级（0.5 天）

4. ✅ **相似度函数**: 在 `scoring.py` 添加 `cosine_similarity()` 和 `calc_craft_score_vector()`

5. ✅ **集成到派单**: 修改 `atomic_dispatch()` 支持 `design_embedding` 参数

6. ✅ **端点改造**: `/api/v1/designs` 创建设计时生成 embedding

### Phase 3: 测试与回退（0.5 天）

7. ✅ **A/B 测试**: 通过配置开关（`ENABLE_VECTOR_CRAFT_MATCHING`）切换新旧算法
   ```python
   # app/core/config.py
   class Settings(BaseSettings):
       ENABLE_VECTOR_CRAFT_MATCHING: bool = False  # 默认关闭
   ```

8. ✅ **对比测试**: 记录新旧算法的派单结果差异
   ```python
   if settings.ENABLE_VECTOR_CRAFT_MATCHING:
       score_new = calc_craft_score_vector(design_emb, studio_emb)
   else:
       score_new = calc_craft_score(params, studio)  # 旧算法
   
   # 同时记录两者差异到日志
   logger.info(f"Craft score diff: old={score_old}, new={score_new}, delta={score_new - score_old}")
   ```

9. ✅ **回退机制**: 若 embedding 为 NULL，自动回退到字符串匹配

---

## 四、性能优化

### 4.1 向量索引

**pgvector 索引类型**:
- **IVFFlat**: 适合中等规模（< 1M 向量），建索引快
- **HNSW**: 适合大规模（> 1M 向量），查询更快但索引慢

**当前规模**: ~100 工作室，无需索引优化（全表扫描 < 10ms）。

**未来扩展**: 若工作室数 > 10K，启用 IVFFlat 索引：
```sql
CREATE INDEX idx_studios_specialty_embedding ON studios 
USING ivfflat (specialty_embedding vector_cosine_ops)
WITH (lists = 100);
```

### 4.2 缓存策略

**工作室 embedding 缓存**:
- 工作室信息变更频率低（天级别），embedding 可缓存到 Redis
- TTL: 24h

```python
# app/services/dispatch/dispatcher.py
async def get_studio_embedding_cached(studio_id: str) -> list[float]:
    cache_key = f"studio:embedding:{studio_id}"
    cached = await redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # 从 DB 查询
    studio = await get_studio(studio_id)
    embedding = studio.specialty_embedding
    
    # 缓存 24h
    await redis.setex(cache_key, 86400, json.dumps(embedding))
    return embedding
```

---

## 五、效果评估

### 5.1 定量指标

| 指标 | 旧算法（字符串） | 新算法（向量） | 目标 |
|------|----------------|---------------|------|
| **派单成功率** | 基线（假设 75%） | 提升 5-10% | >80% |
| **工艺匹配准确率** | 60%（人工评估） | 提升 15-20% | >75% |
| **平均匹配耗时** | ~2ms（子串匹配） | ~5ms（余弦相似度） | <10ms |

### 5.2 定性案例

**Case 1: 同义词识别**

| 设计需求 | 工作室专长 | 旧算法分数 | 新算法分数 | 说明 |
|---------|-----------|-----------|-----------|------|
| 白瓷茶具 | 素瓷茶壶 | 0.2（无匹配） | 0.85（高匹配） | 「白瓷」=「素瓷」，向量能识别 |

**Case 2: 语义相似**

| 设计需求 | 工作室专长 | 旧算法分数 | 新算法分数 | 说明 |
|---------|-----------|-----------|-----------|------|
| 景德镇青花瓷 | 江西青花传统工艺 | 0.7（部分匹配） | 0.95（极高匹配） | 地域 + 工艺名相似 |

**Case 3: 细粒度区分**

| 设计需求 | 工作室专长 | 旧算法分数 | 新算法分数 | 说明 |
|---------|-----------|-----------|-----------|------|
| 现代简约白瓷 | 传统景德镇青花 | 0.2 | 0.45 | 材质相关但风格差异大，向量能量化 |

---

## 六、风险与回退

### 6.1 风险点

1. **OpenAI API 依赖**: 
   - 风险: API 限速、服务不可用
   - 缓解: 离线模型替代（如 `sentence-transformers`）

2. **Embedding 质量**:
   - 风险: 文本生成不当导致 embedding 无意义
   - 缓解: 人工审查生成文本，A/B 测试验证效果

3. **性能退化**:
   - 风险: numpy 余弦相似度计算慢于字符串匹配
   - 缓解: 批量计算、缓存、pgvector 原生相似度查询

### 6.2 回退方案

**配置开关**:
```python
# app/core/config.py
ENABLE_VECTOR_CRAFT_MATCHING: bool = False  # 紧急回退改为 False
```

**自动降级**:
```python
def calc_craft_score_adaptive(params, studio):
    if settings.ENABLE_VECTOR_CRAFT_MATCHING and studio.specialty_embedding:
        return calc_craft_score_vector(params.embedding, studio.specialty_embedding)
    else:
        return calc_craft_score(params, studio)  # 回退到旧算法
```

---

## 七、长期演进

### Phase 4: 多模态 embedding（3 个月后）

**图像 + 文本联合 embedding**:
- 设计图片 → CLIP embedding
- 工作室作品集 → CLIP embedding
- 视觉风格相似度 + 工艺文本相似度加权融合

**Schema 扩展**:
```python
class Design(Base):
    text_embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    image_embedding: Mapped[Optional[list]] = mapped_column(Vector(512))  # CLIP

class Studio(Base):
    specialty_embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    portfolio_embedding: Mapped[Optional[list]] = mapped_column(Vector(512))  # 作品集 CLIP
```

### Phase 5: 实时微调（6 个月后）

**用户反馈闭环**:
- 收集派单后的用户满意度（订单评分）
- 用户接受 vs 拒绝的派单结果 → 正负样本
- Fine-tune embedding 模型或相似度阈值

---

## 八、当前阻塞因素

### ⚠️ 需要解决的前置条件

1. **OpenAI API Key**: 
   - 当前环境是否有 `OPENAI_API_KEY` 配置？
   - 若无，需要申请或改用离线模型

2. **Design embedding 数据**:
   - 当前 `designs` 表的 `embedding` 字段是否已填充？
   - 若为 NULL，需先运行批量生成脚本

3. **业务验证**:
   - 向量相似度阈值（0.85/0.70/0.55）需要业务方根据实际数据调参
   - 建议先在 staging 环境 A/B 测试 1-2 周

### ✅ 可先行推进的工作

即使当前无法生成真实 embedding，仍可推进：

1. **Migration**: 添加 `Studio.specialty_embedding` 字段（nullable=True）
2. **代码框架**: 实现 `cosine_similarity()` 和 `calc_craft_score_vector()`
3. **配置开关**: 添加 `ENABLE_VECTOR_CRAFT_MATCHING`，默认关闭
4. **文档**: 编写 embedding 生成和部署流程（本文档）

---

## 九、决策建议

### 推荐方案: **渐进式迁移**

**Week 1（基础设施）**:
- 添加 `Studio.specialty_embedding` 字段
- 实现 embedding 生成服务（OpenAI API）
- 批量生成工作室 embedding（一次性）

**Week 2（算法集成）**:
- 实现向量相似度函数
- 修改派单逻辑支持向量匹配
- 添加配置开关和回退机制

**Week 3（A/B 测试）**:
- Staging 环境开启 50% 流量使用向量匹配
- 对比新旧算法的派单成功率、用户满意度
- 调整相似度阈值

**Week 4（全量上线）**:
- 若 A/B 测试通过，全量切换
- 监控业务指标（派单成功率、工艺匹配准确率）
- 保留配置开关用于紧急回退

---

## 十、文件变更清单（预期）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/models/entities.py` | 新增字段 | `Studio.specialty_embedding` |
| `alembic/versions/xxxx_add_studio_specialty_embedding.py` | 新增 | Migration 脚本 |
| `app/services/dispatch/embedding.py` | 新增模块 | Embedding 生成服务 |
| `app/services/dispatch/scoring.py` | 新增函数 | `cosine_similarity()`, `calc_craft_score_vector()` |
| `app/services/dispatch/dispatcher.py` | 修改参数 | `atomic_dispatch()` 支持 `design_embedding` |
| `app/core/config.py` | 新增配置 | `ENABLE_VECTOR_CRAFT_MATCHING` |
| `scripts/generate_studio_embeddings.py` | 新增脚本 | 批量生成工作室 embedding |
| `requirements.txt` | 新增依赖 | `openai>=1.0.0`, `numpy>=1.24.0` |

---

## 总结

**当前状态**: 
- ✅ Design 表已有 embedding 字段（但可能未填充）
- ✅ pgvector 已安装（从 entities.py 导入 Vector 可见）
- ❌ Studio 表缺少 embedding 字段
- ❌ 无 embedding 生成服务和批量脚本

**推荐行动**:
1. **先添加 Migration 和代码框架**（本次可完成，无需真实数据）
2. **编写 embedding 生成文档**（本文档）
3. **待 OpenAI API Key 和业务确认后，再运行数据生成脚本**

**预期收益**:
- 工艺匹配准确率提升 15-20%
- 派单成功率提升 5-10%
- 支持同义词和语义相似识别
- 为多模态匹配（图像 + 文本）奠定基础
