# 陶语 (ClayWords) 技术方案

> AI 创造力大赛 · 初赛技术方案 · 当前版本 v1.3（2026-06-19，详见文末修订记录）

---

## 一、项目概述

### 1.1 产品定位

陶语是一个对话式陶瓷定制 Web 应用，用户通过自然语言描述想要的陶瓷摆件，AI 自动生成可烧制的 3D 造型方案，并直连景德镇/德化等产区的陶瓷工作室完成烧制配送。

### 1.2 核心价值

- **需求侧**：降低陶瓷定制门槛，实现"所见即所得"的轻量消费体验
- **供给侧**：为中小陶瓷工作室提供数字化需求管道，减少沟通成本
- **效率提升**：将"想法 → 实物到手"链路从 2–3 周缩短到 7–10 天

### 1.3 技术挑战

| 挑战 | 描述 |
| :--- | :--- |
| 语义理解 | 将自然语言解析为结构化的陶瓷设计参数 |
| 3D 方案生成 | 结合陶瓷工艺约束生成可烧制的造型方案；text-to-3D 输出几何不稳定，需自动校验与修复（详见 §3.3） |
| 智能派单 | 根据工艺、产能、地域匹配最合适的工作室 |
| 实时交互 | 支持对话式微调，所见即所得 |

---

## 二、系统架构设计

### 2.1 整体架构

初赛阶段采用**模块化单体 + GPU 推理工作进程**的拓扑：业务侧用一个 FastAPI 进程承载所有领域模块（设计 / 派单 / 订单 / 用户），3D 生成等长任务通过队列下发给独立的 GPU Worker，避免把 GPU 资源耦合进 Web 进程。这样既保留了未来按模块拆分微服务的边界，又把组件数量控制到初赛 10 周可交付的范围。

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户端 (Web)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 对话式设计台 │  │ 方案预览区  │  │    订单管理中心          │  │
│  │  (Chat UI)  │  │ (Three.js)  │  │ (Order Management)      │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │  HTTPS / SSE   │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Nginx (反向代理 / SSL / 限流)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI 单体应用（领域模块化）                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 会话/设计 │ │ 语义解析 │ │ 派单匹配 │ │ 订单结算 │ │ 用户   ││
│  │  module  │ │  module  │ │  module  │ │  module  │ │ module ││
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘│
└───────┼────────────┼────────────┼────────────┼───────────┼─────┘
        │            │            │            │           │
        │            ▼            │            │           │
        │   ┌────────────────┐    │            │           │
        │   │  LLM Provider  │    │            │           │
        │   │ (OpenAI/通义)  │    │            │           │
        │   └────────────────┘    │            │           │
        │                         │            │           │
        ▼ enqueue                 ▼            ▼           ▼
┌─────────────────────┐  ┌──────────────────────────────────────┐
│   Redis (Streams)   │  │             数据存储层                │
│  长任务队列 + 缓存   │  │  ┌────────────┐  ┌───────────────┐  │
└──────────┬──────────┘  │  │ PostgreSQL │  │     MinIO     │  │
           │             │  │ (业务+JSONB)│  │  (mesh/纹理)  │  │
           ▼             │  └────────────┘  └───────────────┘  │
┌─────────────────────┐  └──────────────────────────────────────┘
│  GPU Worker (1..N)  │
│ - text-to-3D 推理   │
│ - 工艺校验/修复     │
│ - 缩略图烘焙        │
└─────────────────────┘

外部集成：LLM API · text-to-3D 模型（自托管或云推理）· 顺丰物流 API · 支付网关
```

> 说明：初赛只跑 1 个 FastAPI 实例 + 1 个 GPU Worker，但通过 Redis Streams 解耦，复赛上量时 Worker 可水平扩展；当某个领域模块成为瓶颈，再单独拆分为独立服务即可。

### 2.2 核心技术栈

| 层级 | 技术 | 版本 | 选型理由 |
| :--- | :--- | :--- | :--- |
| 前端框架 | Vue 3 | 3.4.x | 响应式 + Composition API，与 Element Plus 生态成熟 |
| UI 组件 | Element Plus | 2.5.x | 中后台组件齐全，主题可定制 |
| 3D 渲染 | Three.js | r170+ | 加载 GLB / 实时预览 / 后处理生态完整 |
| 3D 生成 | Hunyuan3D-2 / Trellis | — | text-to-3D / image-to-3D，自托管推理（详见 §3.3）。**显存基线 ≥ 24GB**（推荐 RTX 4090 / A10 / L20），fp16 推理；< 24GB 需走云推理 API |
| Mesh 处理 | trimesh + Open3D | 4.x / 0.18.x | 几何校验、壁厚检测、修复、布尔运算 |
| 后端语言 | Python | 3.12 | LLM / 3D 推理 / 几何处理生态统一 |
| 后端框架 | FastAPI | 0.115+ | 异步、Pydantic v2 校验、SSE 友好、自动 OpenAPI |
| 任务队列 | Redis Streams + arq | redis 7.2 / arq 0.26 | 与缓存共用 Redis，零额外组件，支持失败重试与延迟任务 |
| 数据库 | PostgreSQL | 16.x（含 pgvector 0.7+） | JSONB 存设计参数、pgvector 模板检索、事务可靠 |
| 文件存储 | MinIO | RELEASE.2024-12-13T22-19-12Z | S3 兼容，本地部署存放 mesh / 纹理 / 缩略图 |
| 部署容器 | Docker + Compose | 24.x / v2 | 初赛单机交付，复赛迁 K8s 改造量小 |

> 删除原方案中的 MySQL（与 PostgreSQL 重复）和 RabbitMQ（Redis Streams 已能满足初赛队列需求，少一个组件意味着少一份运维负担）。

---

## 二·补 通信协议与长任务约定

### 2.3 协议分层

| 场景 | 协议 | 说明 |
| :--- | :--- | :--- |
| 普通 REST 调用（登录、订单、工作室列表） | HTTPS + JSON | 标准请求-响应 |
| 对话流（用户消息 → LLM 解析 → 任务派发） | **HTTPS + Server-Sent Events** | 单向服务端推送，浏览器原生支持，比 WebSocket 简单且能穿透常规反向代理 |
| 长任务进度（3D 方案生成） | SSE 事件流 + 任务 ID 轮询兜底 | Worker 把进度写入 Redis，FastAPI 通过 SSE 转发；网络断开后前端可用 `GET /tasks/{task_id}` 查询最终态 |
| 文件上传 / 下载 | HTTPS + 预签名 URL | 客户端直传 MinIO，避免大文件穿透业务进程 |

### 2.4 长任务时序

```
浏览器                FastAPI               Redis Streams           GPU Worker
   │  POST /sessions/{id}/messages          │                          │
   ├──────────────────────►│                │                          │
   │                       │ XADD design.gen│                          │
   │                       ├───────────────►│                          │
   │  202 {task_id}        │                │  XREADGROUP              │
   │◄──────────────────────┤                │◄─────────────────────────┤
   │                                                                   │
   │  GET /tasks/{task_id}/events  (SSE)                               │
   ├──────────────────────►│                                           │
   │                       │  SUBSCRIBE task:{id}:progress             │
   │                       │◄──────────────────────  PUBLISH ──────────┤
   │  event: progress      │                                  parsing  │
   │◄──────────────────────┤                                           │
   │  event: progress      │                            mesh_generated │
   │◄──────────────────────┤                                           │
   │  event: progress      │                          craft_validated  │
   │◄──────────────────────┤                                           │
   │  event: done {options}│                              completed    │
   │◄──────────────────────┤                                           │
```

> SSE 选型理由：3D 生成是单向"服务端 → 浏览器"的进度推送，不需要 WebSocket 的双向能力；SSE 走标准 HTTP，Nginx `proxy_buffering off` 即可穿透，上线复杂度更低。

### 2.5 SSE 鉴权与事件契约

浏览器原生 `EventSource` 不支持自定义 header，鉴权采用**短期一次性票据**（避免长 JWT 进 Nginx access log）：

1. 客户端用主 JWT 调 `POST /api/v1/sse/tickets { "task_id": "..." }`，服务端在 Redis 写 `sse:ticket:{uuid} → {user_id, task_id}`，TTL 60s，返回 `ticket`
2. 客户端 `new EventSource('/api/v1/tasks/{task_id}/events?ticket=' + ticket)`
3. FastAPI 校验票据归属、删除（一次性），订阅 `task:{task_id}:progress` 频道，转发事件流

事件 schema（`event:` + JSON `data:`）：

```jsonc
// 进度事件，多次推送
event: progress
data: {"stage": "parsing|template_match|gen_inference|craft_check|post_process",
       "percent": 42, "option_no": 2, "message": "工艺校验中"}

// 单方案完成（三方案分别推送）
event: option_ready
data: {"option_id": "uuid", "name": "玉兔捧月", "thumbnail_url": "...",
       "glb_url": "...", "pipeline": "template|generative|hybrid",
       "craft_check": { "passed": true, "issues": [], "auto_fixed": false }}

// 全部完成
event: done
data: {"task_id": "uuid", "options": ["option_id_1", "option_id_2", "option_id_3"]}

// 失败
event: error
data: {"task_id": "uuid", "code": "GEN_TIMEOUT|CRAFT_HARD_FAIL|...", "message": "..."}
```

断线重连：客户端带 `Last-Event-ID` header，服务端从 Redis 队列回放未确认事件；超过 5 分钟则改走 `GET /api/v1/tasks/{task_id}` 拉取终态。

---

## 三、核心模块设计

### 3.1 对话式设计台模块

#### 3.1.1 功能描述

用户通过自然语言输入陶瓷设计需求，系统解析并生成 3D 方案，支持对话式微调。

#### 3.1.2 数据流

```
用户输入 → 语义解析 → 参数结构化 → 3D方案生成 → 方案预览 → 用户确认/微调
```

#### 3.1.3 关键数据结构

```python
class DesignRequest(BaseModel):
    user_id: str
    message: str
    session_id: str

class DesignParams(BaseModel):
    shape: str                    # 造型描述
    glaze_color: str              # 釉色
    size: str                     # 尺寸
    style: str                    # 风格
    emotion: str                  # 情感意象
    material: str                 # 材质
    usage: str                    # 用途

# DesignOption 详见 §3.3.6，包含 glb_url / craft_check / pipeline 等完整字段
```

#### 3.1.4 API 设计

详见 §5.2，统一到 `/sessions/{id}/...` 子资源风格，对话消息（首发与微调）共享同一接口 `POST /sessions/{id}/messages`，由 LLM Router 决定是触发新建方案还是局部重绘。

### 3.2 语义解析模块

#### 3.2.1 功能描述

调用大模型 API，将自然语言解析为结构化的陶瓷设计参数。

#### 3.2.2 解析规则

| 解析维度 | 示例 | 提取规则 |
| :--- | :--- | :--- |
| 造型 | "兔子坐在月亮上" | 提取主体和动作关系 |
| 釉色 | "冷白釉" | 颜色词 + 釉料词组合 |
| 尺寸 | "玄关摆件" | 根据用途推断尺寸范围 |
| 风格 | "新中式" | 风格关键词匹配 |
| 情感 | "送给妈妈的生日礼物" | 情感词和场景词 |

#### 3.2.3 Prompt 设计

```
你是一个专业的陶瓷设计师助手。请分析用户的描述，提取以下设计参数：
- shape: 主体造型描述
- glaze_color: 釉色（如：冷白釉、青瓷釉、哑光黑等）
- size: 建议尺寸（如：18-22cm）
- style: 风格（如：新中式、极简、侘寂等）
- emotion: 情感意象（如：温馨、庄重、治愈等）
- material: 材质（如：白瓷、紫砂、粗陶等）
- usage: 用途（如：玄关摆件、花瓶、茶宠等）

请以JSON格式输出，每个字段都要有值。

用户输入：{user_input}
```

### 3.3 3D 方案生成模块

#### 3.3.1 功能描述

把 §3.2 解析得到的 `DesignParams` 转化为**三个可烧制的 3D 方案**（GLB + 缩略图 + 工艺参数包），支持自然语言微调。这是项目最核心、也是工程不确定性最大的一环，因此单独展开技术选型与管线。

#### 3.3.2 选型对比与最终方案

为同时满足"造型多样性"与"可烧制"两个互相拉扯的目标，我们对比了三条路线：

| 路线 | 多样性 | 可烧制率 | 微调成本 | 推理时延 | 初赛可行性 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| A. 纯参数化模板库（LLM 选模板填参数） | 低 | 高 | 极低（改参数） | < 2s | 兜底首选 |
| B. 纯 text-to-3D 生成模型（如 Hunyuan3D-2 / Trellis） | 高 | 中 | 高（需重生成或局部编辑） | 15–40s | 主航道但风险高 |
| C. **检索增强 + 生成混合** | 中-高 | 高 | 中 | 5–25s | **采用** |

**最终采用 C 方案**：以模板库（约 30–50 个基础造型，按"动物 / 山水 / 器皿 / 抽象"分类）为骨架，LLM 决定走哪条分支：

- **强约束语义**（如"花瓶""茶杯""香插"）→ 走 A，参数化模板，秒级返回，可烧制率近 100%
- **弱约束 / 创意叙事**（如"兔子坐在月亮上""像我家橘猫的样子"）→ 走 B，调用 text-to-3D 模型生成 mesh，再进 §3.3.4 工艺校验流水线
- **混合**（"中式花瓶但瓶身是月亮形状"）→ 取模板基底 + 生成式细节，布尔合成

三个返回方案的策略改为：

| 方案编号 | 路线 | 风格倾向 |
| :--- | :--- | :--- |
| 方案一 | A 模板派生（最稳） | 写实具象，从模板库选择最贴近的基底，参数微调 |
| 方案二 | B 生成式 | 抽象写意，text-to-3D 模型自由发挥，工艺校验通过即可 |
| 方案三 | C 混合 | 创新融合，模板基底 + 生成式细节布尔合成 |

> 即使 B 方案生成失败或工艺校验不过，方案一仍能作为兜底交付给用户，避免"什么都给不出"。

#### 3.3.3 生成管线

```
DesignParams
    │
    ▼
┌──────────────────┐
│ Router (LLM)     │  根据 shape 复杂度 / 是否含叙事意象，路由到 A/B/C
└─────┬────────────┘
      │
      ├──── A ────► 模板检索（pgvector 相似度）→ 参数化变形 → mesh
      │
      ├──── B ────► Prompt 改写 → text-to-3D 推理 → 原始 mesh
      │
      └──── C ────► A 出基底 + B 出局部 → 布尔合成
                       │
                       ▼
              ┌──────────────────┐
              │ §3.3.4 工艺校验  │  壁厚/悬臂/底面/收缩
              └─────┬────────────┘
                    │ 通过
                    ▼
              ┌──────────────────┐
              │ §3.3.5 后处理    │  减面 / UV / 釉色烘焙 / GLB 导出
              └─────┬────────────┘
                    │
                    ▼
                MinIO + 缩略图 + 工艺参数包
```

#### 3.3.4 工艺校验与自动修复

陶瓷烧制有一组硬约束，生成出来的 mesh **必须先过校验**才能进入用户预览，否则会出现"看起来好看但烧不出来"的烂尾。校验由 trimesh + Open3D 实现。不同材质的安全阈值差异很大（白瓷收缩可达 18%，紫砂仅 8% 左右），因此 `CRAFT_RULES` 按材质分组配置，并允许每家工作室基于真实成品数据回写校准：

```python
class CraftCheckResult(BaseModel):
    passed: bool
    issues: list[str]            # ["wall_too_thin@(x,y,z)", "overhang_67deg", ...]
    auto_fixed: bool             # 是否已自动修复
    fixed_mesh_uri: str | None

class CraftRules(BaseModel):
    min_wall_thickness_mm: float
    max_height_mm: float
    max_overhang_deg: float       # 陶瓷烧制时泥料软化 + 重力，比 3D 打印更严
    min_base_ratio: float
    shrinkage_factor: float       # 烧制收缩补偿（建模时整体放大）
    max_aspect_ratio: float

# 默认阈值表（可被工作室级别的覆盖配置替换）
CRAFT_RULES: dict[str, CraftRules] = {
    "porcelain_white": CraftRules(   # 景德镇白瓷
        min_wall_thickness_mm=3.0, max_height_mm=400,
        max_overhang_deg=30, min_base_ratio=0.15,
        shrinkage_factor=1.18, max_aspect_ratio=4.0,
    ),
    "porcelain_celadon": CraftRules( # 青瓷
        min_wall_thickness_mm=3.5, max_height_mm=350,
        max_overhang_deg=30, min_base_ratio=0.15,
        shrinkage_factor=1.15, max_aspect_ratio=4.0,
    ),
    "zisha": CraftRules(             # 宜兴紫砂
        min_wall_thickness_mm=2.5, max_height_mm=300,
        max_overhang_deg=35, min_base_ratio=0.18,
        shrinkage_factor=1.08, max_aspect_ratio=3.5,
    ),
    "stoneware_coarse": CraftRules(  # 粗陶
        min_wall_thickness_mm=4.0, max_height_mm=500,
        max_overhang_deg=40, min_base_ratio=0.20,
        shrinkage_factor=1.10, max_aspect_ratio=3.0,
    ),
}
```

> 校验时先按 `DesignParams.material` 取默认规则，再用 `studio_craft_overrides`（工作室提交的真实收缩 / 壁厚校准数据）覆盖，确保派单后的二次校验贴近该工作室实际能力。

校验失败的处理策略：

| 失败类型 | 自动修复 | 修复失败的兜底 |
| :--- | :--- | :--- |
| 壁厚不足 | trimesh 局部沿法线外推 | 标记"需打样"，前端提示成本上浮 |
| 悬臂超限 | 自动加支撑结构（隐藏在底部） | 退到方案一模板派生 |
| 底面不稳 | 自动加底座 | 重新生成（最多 2 次） |
| 收缩补偿 | 全 mesh 等比放大 1.15× | — |

> 软失败（标记需打样、成本上浮）走前端确认；硬失败（多次重生成仍不通过）直接降级到方案一兜底，对用户透明。

#### 3.3.5 自然语言微调

"把兔子耳朵再长一点点"这类微调请求按生成路线分别处理：

| 原方案路线 | 微调实现 |
| :--- | :--- |
| A 模板派生 | LLM 解析 → 调整模板参数（耳朵长度 +20%）→ 秒级重出 |
| B 生成式 | 走**局部重绘**：对原 mesh 选区生成 mask，仅对耳朵区域重新推理（参考 SDEdit 思路） |
| C 混合 | 仅重生成被点名的子部件，其他部件保留 |

每次微调结果保存为 `design_versions` 一行（见 §4），支持回滚到任意历史版本。

#### 3.3.6 关键数据结构

```python
class DesignOption(BaseModel):
    option_id: str
    name: str                     # "玉兔捧月"
    description: str
    pipeline: Literal["template", "generative", "hybrid"]
    glb_url: str                  # MinIO 中的 GLB 模型
    thumbnail_url: str            # 256×256 渲染图
    craft_check: CraftCheckResult
    estimated_volume_cm3: float   # 用于报价
    estimated_weight_g: float
    price: float
    estimated_days: int
    studio_info: dict
```


### 3.4 智能派单模块

#### 3.4.1 功能描述

根据方案的工艺复杂度、尺寸、地域等因素，匹配最合适的陶瓷工作室。

#### 3.4.2 匹配算法

每个候选工作室计算 0-1 归一化得分：

```
score = 0.40 × craft_match + 0.30 × capacity_match + 0.20 × geo_match + 0.10 × rating_norm
```

- **工艺匹配度（craft_match）**：方案 `pipeline` 与 `CraftCheckResult.issues` 反映的工艺难度（普通 / 镂空 / 浮雕）与工作室 `specialties` 的 Jaccard 相似度；硬约束工艺（如必须紫砂烧制）不匹配直接得 0 并剔除
- **产能匹配度（capacity_match）**：`max(0, (capacity - current_load) / capacity)`，再乘以"未来 7 天档期空闲率"
- **地域匹配度（geo_match）**：根据顺丰区域表，按预计妥投时效映射 `1d → 1.0, 2d → 0.85, 3d → 0.7, 4d+ → 0.5`
- **信誉评分（rating_norm）**：`rating / 5.0`，新工作室默认 4.0 起评

#### 3.4.3 决策规则

- **派单阈值**：`score ≥ 0.55` 才视为有效候选；低于该值进入派单兜底（见 §3.4.4）
- **Tie-breaker**（得分差 ≤ 0.02 视为同分）：依次比较 `current_load` 升序 → `rating` 降序 → 最近 30 天准时交付率降序 → `studio_id` 字典序（保证可重现）
- **多样性约束**：同一用户连续 3 单避免派给同一工作室（除非用户主动指定），鼓励用户体验多样手作

#### 3.4.4 冷启动与兜底策略

初赛阶段没有真实工作室入驻，派单算法的关键字段（`current_load` / `rating` / 历史成单）是空的，必须有冷启动方案：

| 字段 | 冷启动来源 |
| :--- | :--- |
| 种子工作室 | 与 3–5 家合作工作室签约入驻，覆盖景德镇 / 德化 / 宜兴三大产区 |
| `specialties` | 入驻问卷 + 师傅作品集人工标注（白瓷、青花、紫砂、粗陶等） |
| `capacity` | 师傅自报，平台审核校准 |
| `current_load` | 由订单状态机实时维护，无订单时为 0 |
| `rating` | 默认 4.0，前 10 单后启用真实评价 |
| 价格区间 | 入驻时人工核定，每 30 天复核 |

派单兜底链路：

1. 所有候选 `score < 0.55` → 自动派给"平台中央工作室"（合作的兜底产能），订单标注"由平台代选工作室"
2. 中央工作室也无可用产能 → 订单转 `已派单`但工作室 ID 为空，进入 `待人工派单` 队列，运营 24h 内手动指派
3. 仍无可派单 → 进入退款流转（见 §3.5.2）

#### 3.4.5 工作室拒单与重派

- 工作室在订单创建后 **24 小时内**可"接单 / 拒单"；超时未操作视为拒单，自动重派
- 拒单时必须提供原因（产能不足 / 工艺不匹配 / 价格不接受），写入 `order_logs.metadata`
- 同一订单**最多重派 2 次**，第 3 次失败转退款
- 拒单不会立即扣减工作室 `rating`，但**连续 3 次拒单或单月拒单率 > 30%** 自动降低派单权重 20%（在 `score` 计算外乘衰减系数），人工介入复核
- `current_load` 在订单进入 `已派单` 时 +1，在 `已签收 / 已退款 / 已取消` 终态时 -1，由订单状态机统一维护

#### 3.4.6 工作室数据模型

```python
class Studio(BaseModel):
    studio_id: str
    name: str
    location: str                 # 产区（景德镇/德化/宜兴等）
    specialties: list[str]        # 擅长工艺
    capacity: int                 # 日产能
    current_load: int             # 当前负载
    rating: float                 # 信誉评分
    price_range: dict             # 价格区间
    estimated_days: int           # 预计工期
```

### 3.5 订单管理模块

#### 3.5.1 功能描述

管理订单全生命周期：下单 → 派单 → 制作 → 质检 → 发货 → 签收

#### 3.5.2 订单状态流转

```
                                              ┌──── 派单失败 ──┐
                                              │  (无可用工作室) │
                                              ▼                │
待确认 ─支付─► 已支付 ─派单中─► 已派单 ─接单─► 制作中 ─► 待质检 ─► 已质检 ─► 待发货 ─► 运输中 ─► 已签收
   │              │             │      ↑       │                                              │
   │              │             │      │       │                                              ▼
   │              │       拒单/超时未接           制作失败 ─► 重新派单 / 退款                完成
   │              │
   └──未支付取消──┴──支付后申请取消──► 退款中 ─► 已退款 / 退款失败
```

状态说明：
- **待确认**：confirm 接口落库初始态，等待支付（30 分钟超时自动取消）
- **已支付**：触发派单
- **派单中 → 已派单 → 制作中**：派单算法选出工作室、工作室接单（24h 内未接单自动重派）、师傅确认开工
- **派单失败**：所有候选工作室得分低于阈值或全部拒单 → 自动派给"平台中央工作室"（见 §3.4.3）；若中央工作室也无产能，进入"待人工派单"，超过 48h 转退款
- **制作失败**：素烧/釉烧失败、工艺二审驳回 → 默认重新派单一次，第二次失败转全额退款
- **退款流转**：用户主动取消（已支付）或系统判定退款 → 进入 `退款中` → 调用支付网关 → `已退款`（成功）或 `退款失败`（人工介入工单）

终态：`已签收` / `已退款` / `已取消`。所有状态变更写 `order_logs` 表（operator + reason），支持审计与售后回溯。

#### 3.5.3 订单数据模型

```python
class Order(BaseModel):
    order_id: str
    user_id: str
    option_id: str                # 锁定下单时的方案版本快照（design_versions.option_id）
    design_id: str                # 冗余字段，便于按设计聚合查询
    studio_id: str
    status: str
    price: float
    paid_amount: float
    create_time: datetime
    estimated_delivery_time: datetime
    tracking_number: Optional[str]
    history: list[dict]           # 状态变更记录
```

---

## 四、数据库设计

### 4.1 数据库 ER 图

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │       │    Studio    │       │    Order     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ user_id (PK) │       │ studio_id(PK)│       │ order_id (PK)│
│ username     │       │ name         │       │ user_id (FK) │
│ phone        │       │ location     │       │ option_id(FK)│
│ avatar       │       │ specialties  │       │ studio_id(FK)│
│ created_at   │       │ capacity     │       │ status       │
└──────────────┘       │ rating       │       │ price        │
                       └──────────────┘       │ create_time  │
                                              └──────────────┘
         │                                           │
         │ 1:N                                       │ 1:N
         ▼                                           ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   Session    │       │   Design     │       │  OrderLog    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ session_id(PK)│      │ design_id(PK)│       │ log_id (PK)  │
│ user_id (FK) │       │ session_id(FK)│      │ order_id(FK) │
│ messages     │       │ params       │       │ status       │
│ created_at   │       │ options      │       │ operator     │
└──────────────┘       │ selected_idx │       │ create_time  │
                       └──────────────┘       └──────────────┘
```

### 4.2 核心表结构

#### users 表

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| user_id | VARCHAR(36) | PRIMARY KEY | 用户唯一标识 |
| username | VARCHAR(50) | NOT NULL | 用户名 |
| phone | VARCHAR(255) | NOT NULL | 手机号（AES-256-GCM 加密存储，随机 IV） |
| phone_hash | VARCHAR(64) | UNIQUE NOT NULL | 手机号哈希（HMAC-SHA256 + server-side pepper），用于登录查询与去重，pepper 存环境变量 |
| email | VARCHAR(100) | | 邮箱（可选，加密存储） |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希（argon2） |
| role | VARCHAR(20) | NOT NULL DEFAULT 'user' | user / studio_admin / platform_admin |
| avatar | VARCHAR(255) | | 头像URL |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

> 手机号定为登录主键且 NOT NULL，邮箱可选；`role` 字段提供基础 RBAC，工作室管理员通过 `studio_users` 表绑定具体工作室。`phone_hash` 专用于登录验证与去重检测（输入明文手机号 → 计算 HMAC → 查 `phone_hash` 索引 → 取回该行 → 解密 `phone` 列校验），pepper 随机生成后写入 `.env` 且定期轮换（历史 pepper 保留用于旧数据重算）。

#### studio_users 表（工作室成员关系）

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PRIMARY KEY | 自增主键 |
| user_id | VARCHAR(36) | FOREIGN KEY → users | 平台用户 |
| studio_id | VARCHAR(36) | FOREIGN KEY → studios | 关联工作室 |
| role | VARCHAR(20) | NOT NULL | owner / craftsman / dispatcher |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### studios 表

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| studio_id | VARCHAR(36) | PRIMARY KEY | 工作室唯一标识 |
| name | VARCHAR(100) | NOT NULL | 工作室名称 |
| location | VARCHAR(50) | NOT NULL | 产区 |
| specialties | TEXT[] | NOT NULL | 擅长工艺数组 |
| capacity | INT | DEFAULT 10 | 日产能 |
| current_load | INT | DEFAULT 0 | 当前负载 |
| rating | FLOAT | DEFAULT 0 | 信誉评分(0-5) |
| price_min | DECIMAL(10,2) | | 最低报价 |
| price_max | DECIMAL(10,2) | | 最高报价 |
| estimated_days | INT | | 预计工期 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### design_templates 表（模板库，支持向量检索）

在数据库层执行 `CREATE EXTENSION IF NOT EXISTS vector;` 启用 pgvector。

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| template_id | VARCHAR(36) | PRIMARY KEY | 模板唯一标识 |
| name | VARCHAR(100) | NOT NULL | 模板名称（如"经典花瓶""坐姿小兔"） |
| category | VARCHAR(50) | NOT NULL | 分类（animal / landscape / vessel / abstract） |
| description | TEXT | | 语义描述，用于人工浏览 |
| embedding | vector(1536) | NOT NULL | 语义向量（OpenAI text-embedding-3-small / 通义 embedding-v3），用于相似度检索 |
| base_glb_url | VARCHAR(255) | NOT NULL | 基底 mesh 文件 URL（MinIO） |
| default_params | JSONB | NOT NULL | 默认可调参数（高度 / 底座直径 / 耳朵长度等） |
| craft_preset | VARCHAR(50) | | 预设工艺（porcelain_white / zisha 等），匹配 §3.3.4 `CraftRules` |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

> 索引：`CREATE INDEX idx_templates_embedding ON design_templates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`（初赛 30-50 条模板用 `lists=100` 即可，复赛扩容到 500+ 时改 `lists=200`）。路由到 A（模板派生）时，先用 `DesignParams.shape` 生成 embedding，然后 `SELECT * FROM design_templates ORDER BY embedding <=> $1 LIMIT 3` 取最相似的三个候选。

#### sessions 表（设计会话）

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| session_id | VARCHAR(36) | PRIMARY KEY | 会话唯一标识 |
| user_id | VARCHAR(36) | FOREIGN KEY → users | 创建用户 |
| title | VARCHAR(100) | | 会话标题（首条消息自动摘要，可手动编辑） |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | active / archived / closed |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 最近活跃时间，列表按此排序 |

#### session_messages 表（消息流，从 sessions 拆出避免 JSONB 膨胀）

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| message_id | BIGSERIAL | PRIMARY KEY | 自增主键 |
| session_id | VARCHAR(36) | FOREIGN KEY → sessions, NOT NULL | 所属会话 |
| role | VARCHAR(10) | NOT NULL | user / assistant / system |
| content | TEXT | NOT NULL | 消息文本 |
| task_id | VARCHAR(36) | | 触发的长任务 ID（assistant 消息可关联生成任务） |
| metadata | JSONB | | 解析出的 DesignParams、命中模板等附加信息 |
| created_at | TIMESTAMP | DEFAULT NOW() | 时间戳 |

> 索引：`(session_id, created_at)` 覆盖按时间拉取消息列表；超长会话(> 200 条)按需做摘要折叠存到 `sessions.summary` 字段（后续扩展）。拆表的好处是避免单条 JSONB 行无限增长导致 toast 溢出，也方便后续做全文检索。

#### designs 表

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| design_id | VARCHAR(36) | PRIMARY KEY | 设计唯一标识 |
| session_id | VARCHAR(36) | FOREIGN KEY | 关联会话 |
| params | JSONB | NOT NULL | 结构化设计参数（DesignParams） |
| selected_option_id | VARCHAR(36) | | 用户最终选中的方案版本 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### design_versions 表（方案版本，新增）

支持多次微调的版本历史，避免覆盖丢失。每生成一组方案或一次微调写入 N 行（一行对应一个 `DesignOption`）。

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| option_id | VARCHAR(36) | PRIMARY KEY | 方案版本唯一标识 |
| design_id | VARCHAR(36) | FOREIGN KEY → designs | 关联设计 |
| parent_option_id | VARCHAR(36) | FOREIGN KEY (nullable) | 微调来源版本，首批生成为 NULL |
| version_no | INT | NOT NULL | 同 design 内的递增版本号 |
| pipeline | VARCHAR(20) | NOT NULL | template / generative / hybrid |
| name | VARCHAR(50) | | "玉兔捧月" |
| glb_url | VARCHAR(255) | NOT NULL | MinIO 中的 GLB 模型 |
| thumbnail_url | VARCHAR(255) | | 256×256 缩略图 |
| craft_check | JSONB | | CraftCheckResult |
| price | DECIMAL(10,2) | | 报价 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

> 索引：`(design_id, version_no DESC)` 用于快速取最新版本；`parent_option_id` 上建索引便于回溯版本树。

#### orders 表

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| order_id | VARCHAR(36) | PRIMARY KEY | 订单唯一标识 |
| user_id | VARCHAR(36) | FOREIGN KEY → users | 关联用户 |
| option_id | VARCHAR(36) | FOREIGN KEY → design_versions, NOT NULL | **下单锁定的具体方案版本**，下单后即使设计继续微调，订单仍指向当时的快照 |
| design_id | VARCHAR(36) | FOREIGN KEY → designs | 冗余字段，便于按设计聚合查询；权威来源仍是 `option_id` |
| studio_id | VARCHAR(36) | FOREIGN KEY → studios | 关联工作室 |
| status | VARCHAR(20) | NOT NULL | 订单状态 |
| price | DECIMAL(10,2) | NOT NULL | 订单金额 |
| paid_amount | DECIMAL(10,2) | DEFAULT 0 | 已支付金额 |
| tracking_number | VARCHAR(50) | | 物流单号 |
| estimated_delivery | TIMESTAMP | | 预计送达时间 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

> 索引：`(user_id, created_at DESC)` 覆盖"我的订单"列表查询；`option_id` 唯一索引防同一版本重复下单（配合 §5.2 幂等键双重保险）。

---

## 五、API 接口设计

### 5.1 用户认证

| 接口 | 方法 | 路径 | 功能 |
| :--- | :--- | :--- | :--- |
| 用户注册 | POST | `/api/v1/auth/register` | 注册新用户 |
| 用户登录 | POST | `/api/v1/auth/login` | 用户登录 |
| 获取用户信息 | GET | `/api/v1/auth/user` | 获取当前用户信息 |
| 刷新 Token | POST | `/api/v1/auth/refresh` | 刷新访问令牌 |

### 5.2 设计相关

统一到 `/sessions/{id}/...` 子资源风格，避免动词散落在路径中。

| 接口 | 方法 | 路径 | 功能 |
| :--- | :--- | :--- | :--- |
| 创建设计会话 | POST | `/api/v1/sessions` | 创建新的设计会话，返回 `session_id` |
| 发送对话消息 | POST | `/api/v1/sessions/{id}/messages` | 提交自然语言（首发 / 微调通用），返回 `task_id` |
| 订阅任务进度 | GET (SSE) | `/api/v1/tasks/{task_id}/events` | Server-Sent Events 推送生成进度 |
| 查询任务终态 | GET | `/api/v1/tasks/{task_id}` | 断线兜底，返回任务最终结果或失败原因 |
| 获取会话方案列表 | GET | `/api/v1/sessions/{id}/options` | 当前会话已生成的所有方案版本 |
| 获取方案详情 | GET | `/api/v1/options/{option_id}` | 单方案详情（含 `glb_url` / 工艺校验结果） |
| 确认方案下单 | POST | `/api/v1/sessions/{id}/confirm` | Body 携带 `option_id` + 收货地址，触发派单与订单创建，返回 `order_id` |

> 下单是创建订单的**唯一入口**。该接口要求请求方携带 `Idempotency-Key` 头（建议使用 `option_id` + 用户 ID 的哈希），服务端基于 Redis 做 24h 幂等存储，相同 key 命中时直接返回首单结果，避免网络重试或前端误触产生重复订单。

### 5.3 订单相关

| 接口 | 方法 | 路径 | 功能 |
| :--- | :--- | :--- | :--- |
| 获取订单列表 | GET | `/api/v1/orders` | 获取用户订单列表 |
| 获取订单详情 | GET | `/api/v1/orders/{order_id}` | 获取订单详情 |
| 支付订单 | POST | `/api/v1/orders/{order_id}/pay` | 支付订单 |
| 取消订单 | POST | `/api/v1/orders/{order_id}/cancel` | 取消订单 |

### 5.4 工作室相关

| 接口 | 方法 | 路径 | 功能 |
| :--- | :--- | :--- | :--- |
| 获取工作室列表 | GET | `/api/v1/studios` | 获取工作室列表 |
| 获取工作室详情 | GET | `/api/v1/studios/{studio_id}` | 获取工作室详情 |
| 搜索工作室 | GET | `/api/v1/studios/search` | 搜索工作室 |

---

## 六、安全方案

### 6.1 认证与授权

- **JWT Token**：使用 RS256 算法生成访问令牌和刷新令牌
- **Token 有效期**：访问令牌 2 小时，刷新令牌 7 天
- **权限控制**：基于角色的访问控制（RBAC），区分普通用户、工作室管理员、平台管理员

### 6.2 数据安全

- **数据加密**：敏感数据（手机号、邮箱、收货地址）使用 AES-256-GCM 加密存储；查询用字段额外存 HMAC 哈希列（见 §4.2 users 表）
- **传输安全**：全站 HTTPS，API 接口强制 TLS 1.3
- **文件安全**：客户端通过预签名 URL 直传 MinIO（见 §2.3），上传完成后调用 `POST /api/v1/uploads/{key}/commit` 通知后端；后端将该对象入队异步扫描（ClamAV / 云端审核 API），扫描期间对象状态为 `pending`，未通过则置 `quarantined` 并禁止任何业务引用，前端通过 SSE / 轮询获取扫描结果后再渲染。同时强制校验 MIME / 文件头 / 大小上限（图片 ≤ 10MB、GLB ≤ 50MB）

### 6.3 防攻击措施

| 攻击类型 | 防护措施 |
| :--- | :--- |
| SQL 注入 | 使用 ORM 参数化查询 |
| XSS 攻击 | 前端输入过滤，后端输出转义 |
| CSRF 攻击 | 使用 SameSite Cookie，Token 验证 |
| 暴力破解 | 登录失败次数限制，验证码 |
| DDoS 攻击 | Nginx 限流，CDN 防护 |

---

## 七、部署方案

### 7.1 基础设施架构

```
┌─────────────────────────────────────────────────────────────┐
│                     CDN (Cloudflare)                        │
│              静态资源加速（前端构建产物 / 缩略图）            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Nginx (反向代理)                            │
│         SSL 终止 · 限流 · SSE 不缓冲 · 直传 MinIO            │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                                   ▼
┌────────────────┐                ┌────────────────┐
│   Frontend     │                │  FastAPI 单体  │
│   (Vue 3 静态) │                │   Container    │
│   Container    │                │ (含所有领域)   │
└────────────────┘                └────────┬───────┘
                                           │
                          ┌────────────────┼─────────────────┐
                          ▼                ▼                 ▼
                  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                  │ PostgreSQL  │  │    Redis    │  │    MinIO    │
                  │ (业务+JSONB)│  │ 缓存/Streams│  │ mesh / 纹理 │
                  └─────────────┘  └──────┬──────┘  └─────────────┘
                                          │ XREADGROUP
                                          ▼
                                ┌─────────────────────┐
                                │   GPU Worker (1..N) │
                                │  text-to-3D / 校验  │
                                └─────────────────────┘
```

> 初赛交付：单机 Docker Compose，单 GPU Worker；复赛上量时 Worker 改 K8s Deployment 横向扩展，Postgres / Redis / MinIO 切外置高可用集群。

### 7.2 单点风险与数据保护（初赛）

初赛单机部署存在多个单点，必须有清晰的备份与恢复约定：

| 组件 | 单点风险 | 备份策略 | RPO | RTO |
| :--- | :--- | :--- | :--- | :--- |
| PostgreSQL | 主库故障 → 业务全停 | `pg_dump` 每日凌晨打全量到 MinIO；WAL 归档每 15 分钟一次 | 15 分钟 | 30 分钟（恢复全量 + WAL 重放） |
| Redis | 缓存丢失 → SSE 票据 / 进度失效，可恢复 | `appendonly yes` + `everysec` fsync；每日 RDB 落盘 | 1 秒 | 即起即用（重启），客户端会自动重连 SSE 票据接口 |
| MinIO | 文件丢失 → mesh / 缩略图不可访问 | bucket 启用 versioning；每日 `mc mirror` 同步到云对象存储（OSS / S3）做异地备份 | 24 小时 | 30 分钟（拉回最近一次镜像） |
| GPU Worker | 进程崩溃 → 长任务中断 | 任务在 Redis Streams 中带 ACK，Worker 重启后从 pending list 重新消费 | 0（任务可重放） | < 1 分钟（自动重启） |
| FastAPI 进程 | 业务全停 | Compose `restart: unless-stopped`；状态全在 PG/Redis | 0 | < 30 秒 |

> 备份脚本由 cron 触发并在 Sentry / 邮件告警未成功执行的情况；每月做一次**演练性恢复**，把生产备份在测试环境拉起验证可恢复性，避免"备份了但恢复不了"。复赛上线时，PostgreSQL 切流式复制主备 + 自动 failover（Patroni）、Redis 改 Sentinel 集群、MinIO 改分布式四节点纠删码模式，单点全部消除。

### 7.3 Docker Compose 配置

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DB_URL=postgresql://claywords:${DB_PASSWORD}@postgres:5432/claywords
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on: [postgres, redis, minio]

  worker:
    build: ./worker        # GPU 推理 + 几何校验
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: ["gpu"]
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MODEL_BACKEND=hunyuan3d-2     # 可切换 trellis / 云推理
    depends_on: [redis, minio]

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=claywords
      - POSTGRES_USER=claywords
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:RELEASE.2024-12-13T22-19-12Z
    ports:
      - "9000:9000"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
    command: server /data --console-address ":9001"

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

> 删除原 `version: '3.8'` 字段（Compose v2 已废弃），密码全部改为环境变量注入，避免明文进仓库；新增 `worker` 服务承载 GPU 推理。

---

## 八、性能优化

### 8.1 前端优化

| 优化项 | 措施 |
| :--- | :--- |
| 代码分割 | Vue 路由懒加载，按需引入组件 |
| 资源压缩 | Gzip/Brotli 压缩，图片 WebP 格式 |
| 缓存策略 | 静态资源 CDN + 版本哈希 |
| 3D 渲染 | 模型 LOD 优化，纹理压缩 |

### 8.2 后端优化

| 优化项 | 措施 |
| :--- | :--- |
| 查询优化 | 数据库索引优化，慢查询日志分析 |
| 缓存策略 | Redis 缓存热点数据，会话管理 |
| 异步处理 | Redis Streams + arq 处理长任务（3D 生成、工艺校验、缩略图烘焙） |
| 连接池 | 数据库连接池，HTTP 连接池 |

### 8.3 预期性能指标

区分"初赛达标值"与"复赛/上线目标值"，避免一次性把指标写到工业级，初赛却交付不出来。

| 指标 | 初赛达标 | 复赛目标 | 备注 |
| :--- | :--- | :--- | :--- |
| 首屏加载时间 | < 3s | < 2s | 含 Three.js + 首方案缩略图 |
| 普通 API P95 响应 | < 800ms | < 500ms | 不含 LLM / 3D 路径 |
| LLM 语义解析 | < 5s | < 3s | 受上游 API 影响 |
| 单方案生成（A 模板） | < 3s | < 2s | 参数化几乎瞬时 |
| 单方案生成（B 生成式） | < 30s | < 20s | 取决于 GPU 配额 |
| 三方案并行返回 | < 35s | < 25s | A 先返回，B/C 串行/并行视 GPU 数 |
| 工艺校验耗时 | < 5s | < 2s | 单 mesh 几何分析 |
| 在线用户（同时浏览） | 200 | 1000+ | 单进程 + Nginx 即可承载 |
| 同时生成中（占用 GPU） | 5 | 20+ | 按 GPU Worker 数线性扩展 |
| 订单创建链路 | < 1s | < 500ms | 派单 + 写库 + 通知 |

---

## 九、项目进度计划

### 9.1 里程碑规划

| 阶段 | 时间 | 目标 | 出口标准 |
| :--- | :--- | :--- | :--- |
| 第一阶段 | 第 1-2 周 | 核心架构与开发环境 | Compose 一键起前后端 + PG/Redis/MinIO + GPU Worker；OpenAPI 骨架可访问；CI 流水线跑通 lint + 单测 |
| 第二阶段 | 第 3-4 周 | 语义解析 + 3D 方案生成 | 100 条样本意图解析准确率 ≥ 80%；A/B/C 三路线各跑通至少 1 个 demo case；工艺校验对 20 个样例 mesh 全部产出 `CraftCheckResult` |
| 第三阶段 | 第 5-6 周 | 对话台前端 + 智能派单 | 端到端流程"输入 → 三方案 SSE 推送 → 选择 → 派单"贯通；3 家种子工作室入驻数据落库；派单算法对 50 条模拟订单输出可解释得分 |
| 第四阶段 | 第 7-8 周 | 订单管理 + 支付 | 订单状态机 12 个节点全部覆盖（含派单失败 / 拒单重派 / 退款）；接入支付网关沙箱跑通支付 + 退款；幂等键防重测试通过 |
| 第五阶段 | 第 9-10 周 | 优化、加固、上线 | §8.3 初赛达标值全部命中；OWASP Top 10 自检通过；备份恢复演练成功；端到端 P95 在压测 200 并发下达标 |

### 9.2 关键路径

```
需求分析 → 架构设计 → 语义解析开发 → 3D引擎集成 → 前端开发 → 订单系统 → 测试上线
```

---

## 十、风险评估与应对

### 10.1 工程技术风险

| 风险 | 概率 | 影响 | 应对措施 |
| :--- | :--- | :--- | :--- |
| text-to-3D 生成质量不稳定（B 路线） | 高 | 高 | 模板库（A 路线）始终作为兜底；生成失败自动降级；建立"差案例"回收机制持续 fine-tune 提示词 |
| 工艺校验自动修复失败率高 | 中 | 高 | 软失败（标记需打样、成本上浮）+ 硬失败（多次重试后降级模板）双轨；保留人工审核工位作为最后兜底 |
| 自然语言微调无法精准定位部件 | 中 | 中 | 优先走参数化模板的局部参数调整；生成式走 SDEdit 局部重绘 + 用户在 3D 预览中点选区域辅助 |
| 烧制收缩与实际工艺偏差 | 中 | 中 | `shrinkage_factor` 按釉料/泥料分类配置，与每家工作室的真实数据双向对齐 |
| LLM Prompt 注入 / 输出不可控 | 中 | 中 | 输入做语义白名单 + 长度限制；输出强制 JSON Schema 校验，失败时重试 |
| GPU 推理资源不足导致生成排队 | 高 | 中 | 优先级队列：首方案（A）走 CPU 模板秒级返回，给用户即时反馈；生成式（B/C）排队推理 |
| 3D 模型在浏览器端加载慢 | 中 | 中 | Draco 压缩 + LOD 多级，方案缩略图先行展示 |

### 10.2 业务运营风险

| 风险 | 概率 | 影响 | 应对措施 |
| :--- | :--- | :--- | :--- |
| 大模型 API 调用成本高 | 中 | 中 | 单用户日预算上限；高频意图缓存；Router 用小模型路由，仅复杂语义用大模型 |
| 工作室产能波动 / 爆单 | 中 | 高 | 多工作室备份，平台中央工作室兜底，提前 7 天产能预警 |
| 用户需求理解偏差导致退款 | 中 | 中 | 三方案对比 + 微调确认 + 下单前 3D 预览强制旋转一周，沉默用户提示"是否需要平台审核" |
| 物流配送破损 | 低 | 中 | 专业泡沫包装 + 顺丰保价；破损照片回传后自动启动重做或全额退款 |
| 物理打样实际无法烧制 | 中 | 高 | 工作室签收订单后 24 小时内有"工艺二审"窗口，可申请退单且不计入信誉 |
| 工作室单方爽约 | 低 | 高 | 30% 预付 + 平台保险池；连续爽约自动降级该工作室派单权重 |

### 10.3 安全合规风险

| 风险 | 概率 | 影响 | 应对措施 |
| :--- | :--- | :--- | :--- |
| 用户上传图片含违规内容 | 中 | 高 | 接入图片审核 API，命中规则自动驳回 |
| 生成式 3D 包含敏感意象 | 低 | 中 | LLM 解析阶段内容审核，命中关键词清单时拒绝 |
| 用户隐私泄露 | 低 | 高 | 手机号 / 收货地址 AES-256 加密存储，日志脱敏 |

---

## 十一、测试策略

### 11.1 测试金字塔

| 层级 | 框架 | 覆盖目标 | 触发时机 |
| :--- | :--- | :--- | :--- |
| 单元测试 | pytest + pytest-asyncio | 工艺校验规则、派单算法、状态机迁移、Pydantic 模型边界 | 每次 commit（pre-commit + CI） |
| 契约测试 | schemathesis（基于 OpenAPI） | 所有 API 的输入/输出符合 schema，模糊测试参数 | 每次 PR |
| 集成测试 | pytest + testcontainers | DB / Redis / MinIO 真实容器，覆盖订单全链路、SSE 推送 | 每次 PR（夜间全跑） |
| 端到端测试 | Playwright | 关键用户旅程：注册 → 设计 → 下单 → 支付 | 每晚定时 + 发布前手动 |
| 几何回归 | 自建测试集（30 个 mesh 样本） | text-to-3D 输出与基线模型的 IoU / 壁厚分布偏移 | 每次模型版本更新 |
| 负载压测 | locust | API P95、SSE 长连接稳定性 | 上线前 + 每月一次 |

### 11.2 覆盖率门槛

- 单测覆盖率：业务模块 ≥ 80%，工艺校验/派单算法 ≥ 95%（关键路径不留盲区）
- 契约测试：所有 `POST/PUT/DELETE` 接口必须有；schemathesis 模糊测试零 5xx
- E2E：5 条核心旅程必须 green 才能合并 main 分支

---

## 十二、可观测性

### 12.1 三大支柱

| 维度 | 工具 | 关键内容 |
| :--- | :--- | :--- |
| 日志 | structlog（JSON 格式）→ Promtail → Loki | 所有日志带 `request_id` / `user_id` / `task_id` 三件套，敏感字段（手机号、地址）脱敏后输出 |
| 指标 | prometheus-fastapi-instrumentator + 自定义业务指标 → Prometheus → Grafana | 系统：QPS / P50P95P99 / 错误率；业务：方案生成成功率（按 A/B/C 路线）、工艺校验通过率、派单兜底率、支付成功率 |
| 追踪 | OpenTelemetry SDK → OTLP → Jaeger | 跨服务（FastAPI ↔ Redis ↔ Worker）链路；3D 生成全过程时延分解 |

### 12.2 告警阈值（初赛）

| 告警 | 触发条件 | 通道 |
| :--- | :--- | :--- |
| API 5xx 飙升 | 5 分钟内 5xx 比率 > 1% | 飞书机器人 + 邮件 |
| 方案生成成功率下跌 | 30 分钟内成功率 < 85% | 飞书机器人 |
| 派单兜底率异常 | 1 小时内兜底率 > 30%（说明候选工作室普遍不可用） | 邮件 |
| GPU Worker 队列堆积 | Streams pending > 50 持续 10 分钟 | 飞书机器人 |
| 备份未成功 | `pg_dump` / MinIO mirror 任一失败 | 邮件 + PagerDuty 备用 |

---

## 十三、数据迁移

- **工具**：Alembic（与 SQLAlchemy 集成），所有 schema 变更走 migration，禁止线上手动 DDL
- **首版基线**：`alembic revision -m "initial schema"` 生成 v1，包含 §4.2 所有表 + pgvector 扩展安装
- **变更原则**：
  - 兼容性优先：先加列（nullable）→ 双写过渡 → 再回填 → 最后改 NOT NULL
  - 改名 / 删列必须分两次发布，避免新代码与旧代码冲突
  - 索引创建用 `CONCURRENTLY`（Postgres 不锁表）
- **回滚**：每个 migration 必须实现 `downgrade()`；上线前在 staging 跑通 `upgrade head` → `downgrade -1` → `upgrade head` 三步

---

## 十四、CI/CD

```
GitHub Push
    │
    ▼
┌───────────────────────────────────────────────────┐
│ GitHub Actions（PR 触发）                          │
│  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐│
│  │ lint │ │ type │ │ pytest │ │ E2E  │ │ Trivy  ││
│  │ ruff │ │ mypy │ │  +cov  │ │ Play │ │ 镜像扫 ││
│  └──────┘ └──────┘ └────────┘ └──────┘ └────────┘│
└─────────────────────┬─────────────────────────────┘
                      │ all green + 1 review
                      ▼
              merge to main → tag vX.Y.Z
                      │
                      ▼
            Docker buildx multi-arch
                      │
                      ▼
        Push to 内部 Registry (image:vX.Y.Z + sha)
                      │
                      ▼
         staging 自动部署 → 烟雾测试 → 人工触发生产
```

镜像标签策略：`<service>:<git-sha>`（不可变）+ `<service>:vX.Y.Z`（可读）+ `<service>:latest`（仅 dev）；生产部署只允许 `vX.Y.Z` 标签。

---

## 十五、License 与合规

| 资产 | License | 商用约束 |
| :--- | :--- | :--- |
| Hunyuan3D-2 模型权重 | Tencent Hunyuan Community License | 可商用但有用户量阈值（超 1 亿 MAU 需另议），输出物商用需保留模型卡片署名 |
| Trellis 模型权重 | MIT | 完全开源可商用 |
| Vue 3 / Element Plus / FastAPI / trimesh / Open3D | MIT / Apache-2.0 | 自由商用 |
| MinIO | AGPL-3.0（社区版） | 自托管商用合规；如不愿开源衍生服务可用 RELEASE 版本（受限）或购买商业 license |
| 用户生成内容（UGC） | 平台获非排他使用授权 | 用户协议明确：用户保留 IP，平台获展示 / 派单 / 改善模型授权；删除账号时关联 mesh 一并删除 |
| 手作师傅作品集 | 工作室入驻协议中约定 | 用于派单匹配与平台展示，不再分发 |

> 模型 license 是最容易踩雷的环节，必须在选型阶段法务过一遍；切换 Hunyuan3D ↔ Trellis 应保留接口抽象，避免被单一 license 绑死。

---

> 本文档为 AI 创造力大赛初赛技术方案

### 修订记录

| 版本 | 日期 | 修订人 | 摘要 |
| :--- | :--- | :--- | :--- |
| v1.0 | 2026-06-19 | ClayWords 团队 | 初稿 |
| v1.1 | 2026-06-19 | ClayWords 团队 | 评审反馈第一轮：下单接口去重、订单 option_id 锁版本、phone_hash 去重、DesignOption 收敛、上传安全闭环 |
| v1.2 | 2026-06-19 | ClayWords 团队 | 评审反馈第二轮：工艺规则按材质分组、SSE 鉴权与事件契约、订单状态机补全、备份与 RTO/RPO |
| v1.3 | 2026-06-19 | ClayWords 团队 | 评审反馈第三轮：补 design_templates / sessions / session_messages 表，派单决策细化，新增测试 / 可观测性 / 迁移 / CI / License 章节 |