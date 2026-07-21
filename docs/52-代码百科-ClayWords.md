# ClayWords 陶语 - Code Wiki 代码百科

> **最后更新**: 2026-06-24  
> **版本**: v1.0.0  
> **文档状态**: 已完成

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [项目目录结构](#3-项目目录结构)
4. [后端核心模块](#4-后端核心模块)
5. [前端核心模块](#5-前端核心模块)
6. [Worker 任务处理](#6-worker-任务处理)
7. [数据模型与数据库](#7-数据模型与数据库)
8. [关键类与函数说明](#8-关键类与函数说明)
9. [依赖关系](#9-依赖关系)
10. [运行与部署指南](#10-运行与部署指南)
11. [测试体系](#11-测试体系)
12. [监控与运维](#12-监控与运维)
13. [优化建议与方案](#13-优化建议与方案)

---

## 1. 项目概述

### 1.1 项目简介

**陶语 (ClayWords)** 是一个 AI 驱动的对话式陶瓷定制平台，用户通过自然语言描述想要的陶瓷摆件，AI 自动生成可烧制的 3D 造型方案，并直连景德镇/德化等产区的陶瓷工作室完成烧制配送。

### 1.2 核心特性

| 领域 | 特性 |
|------|------|
| **用户交互** | 对话式设计台、SSE 实时推送、3D 模型预览 |
| **AI 能力** | LLM 需求解析、混元3D文生模型、模板匹配 |
| **订单履约** | 四维评分智能派单、订单状态机、物流追踪 |
| **安全合规** | AES-GCM 字段加密、OWASP Top 10 防护、ClamAV 文件扫描 |
| **支付物流** | 支付宝集成、物流Provider抽象 |
| **运维监控** | Prometheus + Grafana、结构化日志、SLO 告警 |

### 1.3 技术栈概览

| 层级 | 技术选型 |
|------|----------|
| **后端框架** | FastAPI 0.138.0 + Python 3.11 |
| **数据库** | PostgreSQL 16 + pgvector 向量检索 |
| **缓存/队列** | Redis 7 (Streams + Pub/Sub + ARQ) |
| **对象存储** | MinIO (S3 兼容) |
| **ORM** | SQLAlchemy 2.0 (异步) |
| **前端框架** | Vue 3.5 + Vite 6 + TypeScript 5.7 |
| **UI 组件** | Element Plus 2.9 |
| **3D 渲染** | Three.js 0.172 |
| **状态管理** | Pinia 2.3 |
| **容器编排** | Docker Compose + Kubernetes Helm |
| **监控** | Prometheus + Grafana + Alertmanager |

---

## 2. 整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层 (Frontend)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │  用户端   │  │ 工作室端  │  │ 管理后台  │  │ Three.js 3D  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘   │
│       │              │              │                │           │
│       └──────────────┴──────┬───────┴────────────────┘           │
│                             │ HTTP/HTTPS + SSE                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                      API 网关 / 反向代理 (Nginx)                 │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                      后端服务层 (Backend)                        │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │                    FastAPI Application                   │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐  │   │
│  │  │  Auth   │ │ Orders  │ │ Designs │ │  Studios     │  │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬───────┘  │   │
│  │       │           │           │               │          │   │
│  │  ┌────┴───────────┴───────────┴───────────────┴───────┐  │   │
│  │  │              业务服务层 (Services)                 │  │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐ │  │   │
│  │  │  │ Order  │ │Dispatch│ │Payment │ │  Hunyuan3D  │ │  │   │
│  │  │  │Service │ │Service │ │Service │ │   Service   │ │  │   │
│  │  │  └───┬────┘ └───┬────┘ └───┬────┘ └──────┬──────┘ │  │   │
│  │  └──────┼──────────┼──────────┼──────────────┼────────┘  │   │
│  │         │          │          │              │           │   │
│  │  ┌──────┴──────────┴──────────┴──────────────┴────────┐  │   │
│  │  │              核心基础设施 (Core)                    │  │   │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────────┐  │  │   │
│  │  │  │Crypto│ │Redis │ │MinIO │ │ Rate │ │Metrics  │  │  │   │
│  │  │  └──┬───┘ └──┬───┘ └──┬───┘ │Limit │ │Promethe │  │  │   │
│  │  └─────┼────────┼────────┼──────┴──┬───┘ └────┬────┘  │  │   │
│  └────────┼────────┼────────┼─────────┼───────────┼───────┘  │   │
└───────────┼────────┼────────┼─────────┼───────────┼──────────┘
            │        │        │         │           │
┌───────────┼────────┼────────┼─────────┼───────────┼──────────┐
│           ▼        ▼        ▼         ▼           ▼          │
│  ┌────────────┐ ┌─────┐ ┌─────┐ ┌──────────┐ ┌───────────┐  │
│  │ PostgreSQL │ │Redis│ │MinIO│ │ ClamAV   │ │ Prometheu │  │
│  │  +pgvector │ │     │ │     │ │ (杀毒)   │ │  s/Grafana│  │
│  └─────┬──────┘ └──┬──┘ └─────┘ └──────────┘ └───────────┘  │
│        │           │                                          │
│        │     ┌─────┴─────┐                                   │
│        │     │  ARQ      │                                   │
│        │     │  Worker   │◄──────────────────────────────────┘
│        │     │  Pool     │
│        │     └─────┬─────┘
│        │           │
│        ▼           ▼
│  ┌─────────────────────────────────────────────────────┐    │
│  │              GPU Worker 集群                        │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │    │
│  │  │ Template   │ │ Generative │ │  Hybrid    │       │    │
│  │  │ Pipeline   │ │ Pipeline   │ │ Pipeline   │       │    │
│  │  └────────────┘ └────────────┘ └────────────┘       │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ Craft Check (壁厚/悬垂/收缩/比例/稳定性)     │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 分层架构

项目采用清晰的分层架构：

| 层级 | 目录 | 职责 |
|------|------|------|
| **API 路由层** | [backend/app/api/](file:///e:/python-code/ClayWords/backend/app/api/) | HTTP 端点定义、请求校验、响应序列化 |
| **业务服务层** | [backend/app/services/](file:///e:/python-code/ClayWords/backend/app/services/) | 核心业务逻辑、状态管理、服务编排 |
| **核心组件层** | [backend/app/core/](file:///e:/python-code/ClayWords/backend/app/core/) | 加密、存储、缓存、限流、监控等基础设施 |
| **数据模型层** | [backend/app/models/](file:///e:/python-code/ClayWords/backend/app/models/) | ORM 实体定义、自定义类型 |
| **数据访问层** | [backend/app/db/](file:///e:/python-code/ClayWords/backend/app/db/) | 数据库会话管理、连接池 |
| **任务处理层** | [worker/](file:///e:/python-code/ClayWords/worker/) | 异步任务执行、3D 生成流水线 |

---

## 3. 项目目录结构

```
ClayWords/
├── backend/                     # FastAPI 后端服务
│   ├── app/
│   │   ├── api/                 # API 路由 (17 个模块, 60+ 端点)
│   │   │   ├── auth.py          # 认证: 手机号验证码登录
│   │   │   ├── sessions.py      # 设计会话管理
│   │   │   ├── sse.py           # Server-Sent Events 实时推送
│   │   │   ├── tasks.py         # 异步任务状态查询
│   │   │   ├── options.py       # 设计方案选项
│   │   │   ├── orders.py        # 用户订单管理
│   │   │   ├── payments.py      # 支付集成 (支付宝)
│   │   │   ├── logistics.py     # 物流追踪
│   │   │   ├── uploads.py       # 文件预签名上传 + 病毒扫描
│   │   │   ├── studio_onboarding.py  # 工作室入驻申请
│   │   │   ├── studio_orders.py      # 工作室端订单管理
│   │   │   ├── hunyuan3d.py     # 混元3D 文生模型接口
│   │   │   ├── admin.py         # 管理后台 API
│   │   │   ├── alerts.py        # 告警配置
│   │   │   ├── metrics.py       # Prometheus metrics 端点
│   │   │   ├── health.py        # 健康检查
│   │   │   └── demo.py          # 演示数据
│   │   ├── core/                # 核心基础设施 (11 个模块)
│   │   │   ├── config.py        # Pydantic Settings 配置
│   │   │   ├── crypto.py        # AES-256-GCM 加密服务
│   │   │   ├── redis.py         # Redis 客户端封装 (Streams/PubSub)
│   │   │   ├── storage.py       # MinIO 对象存储客户端
│   │   │   ├── rate_limit.py    # 滑动窗口限流中间件
│   │   │   ├── logging_middleware.py  # 结构化日志中间件
│   │   │   ├── metrics.py       # Prometheus 指标收集中间件
│   │   │   ├── clamav.py        # ClamAV 病毒扫描客户端
│   │   │   ├── prompt_defense.py # Prompt 注入防护
│   │   │   └── time.py          # 时区感知时间工具
│   │   ├── db/                  # 数据库层
│   │   │   └── session.py       # 异步引擎 + 会话管理
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   │   ├── entities.py      # 14 张表实体定义
│   │   │   └── types.py         # 自定义列类型 (Vector/EncryptedStr/JSONB)
│   │   ├── services/            # 业务逻辑服务
│   │   │   ├── auth.py          # 认证服务 (JWT)
│   │   │   ├── demo.py          # 演示数据服务
│   │   │   ├── order/           # 订单服务
│   │   │   │   ├── order_service.py  # 订单 CRUD + 状态更新
│   │   │   │   └── state_machine.py  # 订单状态机定义
│   │   │   ├── dispatch/        # 智能派单服务
│   │   │   │   ├── dispatcher.py     # 派单主逻辑 (原子 CAS)
│   │   │   │   ├── scoring.py        # 四维评分算法
│   │   │   │   └── policy.py         # 派单策略与兜底
│   │   │   ├── payment/         # 支付服务
│   │   │   │   └── payment_service.py
│   │   │   ├── logistics/       # 物流服务 (Provider 抽象)
│   │   │   │   ├── base.py           # 物流 Provider 基类
│   │   │   │   ├── mock_provider.py  # Mock 实现
│   │   │   │   └── registry.py       # Provider 注册中心
│   │   │   ├── tasks/           # 任务服务
│   │   │   │   └── task_service.py
│   │   │   ├── alerting/        # 告警服务
│   │   │   │   └── alerting_service.py
│   │   │   ├── hunyuan3d/       # 混元3D 服务
│   │   │   │   ├── client.py         # HTTP API 客户端
│   │   │   │   ├── schemas.py        # 请求/响应 Schema
│   │   │   │   └── worker.py         # Worker 轮询器
│   │   │   ├── llm/             # LLM 解析
│   │   │   │   └── parser.py
│   │   │   └── workorder/       # 工单 PDF 生成
│   │   │       └── pdf.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   └── worker/              # 后端内置 Worker
│   │       ├── main.py
│   │       └── consumer.py
│   ├── alembic/                 # 数据库迁移 (Alembic)
│   │   └── versions/            # 6 个迁移版本
│   ├── tests/                   # 单元测试 (22 个测试文件)
│   ├── scripts/                 # 运维脚本
│   ├── infra/                   # SQL 初始化脚本
│   ├── requirements.txt         # Python 依赖
│   └── Dockerfile               # 后端容器镜像
│
├── worker/                      # GPU Worker 独立进程
│   ├── main.py                  # Worker 入口 (ARQ)
│   ├── pipelines/               # 3D 生成流水线
│   │   ├── template_pipeline.py    # 模板匹配流水线
│   │   ├── generative_pipeline.py  # AI 生成流水线
│   │   └── hybrid_pipeline.py      # 混合流水线
│   └── craft_check/             # 工艺校验模块
│       ├── pipeline.py          # 校验编排
│       ├── models.py            # 校验数据模型
│       ├── rules.py             # 校验规则
│       ├── wall_thickness.py    # 壁厚检测
│       ├── overhang.py          # 悬垂角度检测
│       ├── shrinkage.py         # 收缩率计算
│       ├── aspect_ratio.py      # 比例检测
│       ├── base_stability.py    # 底座稳定性
│       └── auto_fix.py          # 自动修复建议
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── main.ts              # 应用入口
│   │   ├── App.vue              # 根组件
│   │   ├── router/              # Vue Router 配置 (11 个路由)
│   │   │   └── index.ts
│   │   ├── stores/              # Pinia 状态管理
│   │   │   └── auth.ts          # 认证状态
│   │   ├── api/                 # API 客户端封装
│   │   │   ├── client.ts        # Axios 实例 + 拦截器
│   │   │   └── modules.ts       # API 模块定义
│   │   ├── views/               # 页面视图 (11 个)
│   │   │   ├── HomeView.vue     # 首页
│   │   │   ├── LoginView.vue    # 登录/注册
│   │   │   ├── DesignView.vue   # 对话式设计台
│   │   │   ├── OrdersView.vue   # 我的订单
│   │   │   ├── ProfileView.vue  # 个人资料
│   │   │   ├── studio/          # 工作室端
│   │   │   │   ├── StudioOrdersView.vue
│   │   │   │   └── StudioOrderDetailView.vue
│   │   │   └── admin/           # 管理后台
│   │   │       ├── AdminDashboardView.vue
│   │   │       ├── AdminStudiosView.vue
│   │   │       └── AdminOrdersView.vue
│   │   ├── components/          # UI 组件 (8 个)
│   │   │   ├── ChatPanel.vue         # 对话面板
│   │   │   ├── OptionCards.vue       # 方案卡片选择
│   │   │   ├── PreviewCanvas.vue     # 3D 预览画布
│   │   │   ├── ThreeViewer.vue       # Three.js 模型查看器
│   │   │   ├── DispatchPanel.vue     # 派单信息面板
│   │   │   ├── DispatchVisualization.vue  # 派单可视化
│   │   │   ├── DesignHeader.vue      # 设计页顶栏
│   │   │   ├── Hunyuan3DProgress.vue # 混元3D进度
│   │   │   └── WorkOrderPopup.vue    # 工单弹窗
│   │   ├── composables/         # 组合式函数
│   │   │   ├── useDesignMessages.ts  # 设计消息流
│   │   │   ├── useDesignVersions.ts  # 设计版本管理
│   │   │   ├── useHunyuan3D.ts       # 混元3D调用
│   │   │   ├── useOrderFlow.ts       # 订单流程
│   │   │   └── usePreviewRotation.ts # 预览旋转
│   │   ├── types/               # TypeScript 类型定义
│   │   │   ├── design.ts
│   │   │   └── index.ts
│   │   ├── constants/           # 常量定义
│   │   │   └── glaze.ts         # 釉色配置
│   │   ├── styles/              # 全局样式
│   │   │   └── variables.css    # CSS 变量 (陶土暖色主题)
│   │   └── assets/              # 静态资源
│   │       ├── hero-ceramic.png
│   │       └── 玉兔捧月.png
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts           # Vite 构建配置 + API 代理
│   └── tsconfig.json
│
├── infra/                       # 基础设施配置
│   ├── docker-compose.yml       # 本地开发容器编排
│   ├── docker-compose.monitoring.yml  # 监控栈
│   ├── init.sql                 # PostgreSQL 初始化脚本
│   ├── prometheus/              # Prometheus 配置
│   │   ├── prometheus.yml
│   │   └── rules/slo.yml        # SLO 告警规则
│   ├── grafana/                 # Grafana 配置
│   │   └── provisioning/        # 自动 provisioning
│   └── alertmanager/            # Alertmanager 配置
│       └── alertmanager.yml
│
├── helm/claywords/              # Kubernetes Helm Chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── values-production.yaml
│
├── scripts/                     # 运维/数据脚本
│   ├── seed_users.py            # 种子用户数据
│   ├── seed_studios.py          # 种子工作室数据
│   ├── seed_templates.py        # 种子设计模板
│   ├── seed_demo_orders.py      # 种子演示订单
│   ├── backup_pg.sh             # PostgreSQL 备份
│   ├── restore_pg.sh            # PostgreSQL 恢复
│   ├── backup_redis.sh          # Redis 备份
│   ├── deploy_production.sh     # 生产部署脚本
│   ├── rotate_pepper.py         # 加密密钥轮换
│   └── repair_phone_encryption.py  # 手机号加密修复
│
├── docs/                        # 项目文档 (23 份)
│   ├── 00-文档索引.md
│   ├── 11-技术方案v1.3.md
│   ├── 31-安全自检-OWASP-Top10.md
│   └── ...
│
├── Makefile                     # 常用命令快捷方式
├── .env.example                 # 环境变量示例
└── README.md                    # 项目说明
```

---

## 4. 后端核心模块

### 4.1 应用入口 [main.py](file:///e:/python-code/ClayWords/backend/app/main.py)

**职责**: FastAPI 应用初始化、中间件注册、路由挂载、生命周期管理。

**关键配置**:

| 项 | 说明 |
|----|------|
| **CORS** | 显式列举允许的源、方法、Headers，配合 `allow_credentials=True` |
| **中间件顺序** (外→内) | PrometheusMiddleware → RateLimitMiddleware → LoggingMiddleware |
| **全局异常处理** | 未捕获异常统一返回 500，包含 trace_id 便于排查 |
| **生命周期** | startup: 初始化 DB/Redis/MinIO; shutdown: 断开 Redis |

### 4.2 配置模块 [config.py](file:///e:/python-code/ClayWords/backend/app/core/config.py)

**核心类**: `Settings(BaseSettings)`

**关键配置项**:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ENVIRONMENT` | `development` | 环境标识: development/staging/production |
| `DATABASE_URL` | 本地 PG | PostgreSQL 连接串 |
| `DB_POOL_SIZE` | 20 | 连接池大小 |
| `REDIS_URL` | 本地 Redis | Redis 连接串 |
| `MINIO_*` | 本地 MinIO | 对象存储配置 |
| `CRYPTO_PEPPER` | 开发占位符 | 加密密钥 (生产必填) |
| `JWT_SECRET_KEY` | 开发占位符 | JWT 签名密钥 (生产必填) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 (7天) | Access Token 过期时间 |
| `CLAMAV_ENABLED` | False | 病毒扫描开关 (生产必须 True) |
| `CENTRAL_STUDIO_ID` | "" | 兜底工作室 ID (生产必填) |

**生产环境强校验**:
- 启动时检查密钥是否为开发占位符
- 检查 DEBUG 是否关闭
- 检查支付/回调 URL 是否 HTTPS
- 检查 MinIO 是否启用 TLS
- 检查 ClamAV 是否启用
- 检查兜底工作室是否配置

### 4.3 加密服务 [crypto.py](file:///e:/python-code/ClayWords/backend/app/core/crypto.py)

**核心类**: `CryptoService`

| 方法 | 说明 |
|------|------|
| `encrypt(plaintext: str) -> str` | AES-256-GCM 加密，随机 12-byte nonce |
| `decrypt(encrypted: str) -> str` | 解密 |
| `hash_phone(phone: str) -> str` | SHA-256 哈希 (用于唯一约束/查找) |
| `hmac_phone(phone: str) -> str` | HMAC-SHA256 (用于校验) |

**加密流程**:
```
明文 → 规范化(去空格/横线) → SHA-256(pepper) 派生 32-byte 密钥
     → AES-GCM 加密(nonce + ciphertext) → Base64 编码
```

### 4.4 Redis 客户端 [redis.py](file:///e:/python-code/ClayWords/backend/app/core/redis.py)

**核心类**: `RedisClient`

封装的功能:
- **基础 KV**: get/set/delete/expire
- **Pub/Sub**: publish/pubsub (用于 SSE 进度推送)
- **Streams**: xadd/xread/xrange/xlen (任务队列)
- **Consumer Groups**: xgroup_create/xreadgroup/xack/xpending/xclaim
- **Sets**: sadd/sismember (JWT 黑名单)
- **Lua Scripting**: eval (原子滑动窗口限流)

### 4.5 MinIO 存储 [storage.py](file:///e:/python-code/ClayWords/backend/app/core/storage.py)

**核心类**: `MinIOClient`

| 方法 | 说明 |
|------|------|
| `generate_object_key()` | 生成唯一对象键 (UUID + 前缀) |
| `presigned_put_url()` | 生成预签名 PUT URL (浏览器直传) |
| `presigned_get_url()` | 生成预签名 GET URL (临时下载) |
| `get_public_url()` | 获取公开访问 URL |
| `put_object_bytes()` | 服务端直接上传字节 (Hunyuan3D 结果) |
| `get_object_bytes()` | 读取对象内容 (ClamAV 扫描用) |

**上传流程 (客户端直传)**:
```
1. POST /uploads/init → 获取预签名 PUT URL + object_key
2. 浏览器直接 PUT 到 MinIO
3. POST /uploads/{id}/confirm → 触发病毒扫描 + 记录到 DB
4. GET /uploads/{id} → 查询扫描状态 → 获取 public_url
```

### 4.6 限流中间件 [rate_limit.py](file:///e:/python-code/ClayWords/backend/app/core/rate_limit.py)

**实现**: Redis + Lua 脚本实现的滑动窗口限流

**限流规则** (按端点配置):
- 认证接口: 更严格的限制 (防暴力破解)
- 普通 API: 标准限制
- SSE 接口: 宽松限制

### 4.7 数据库会话 [session.py](file:///e:/python-code/ClayWords/backend/app/db/session.py)

**关键配置**:
- 异步引擎 (`create_async_engine`)
- 连接池: pool_size=20, max_overflow=20, pool_recycle=1800
- `pool_pre_ping=True`: 网络抖动时自动校验连接
- 非开发环境跳过 `create_all` (必须走 Alembic 迁移)

**会话管理**:
- `get_session()`: FastAPI 依赖注入，自动 commit/rollback/close
- `session_scope()`: 异步上下文管理器，用于服务层手动控制事务

### 4.8 订单服务 [order_service.py](file:///e:/python-code/ClayWords/backend/app/services/order/order_service.py)

**核心函数**:

| 函数 | 说明 |
|------|------|
| `create_order_log()` | 创建订单状态变更日志 |
| `update_order_status()` | 更新订单状态 (带状态机校验) |
| `cancel_order()` | 取消订单 (释放工作室容量) |
| `pay_order()` | 支付订单 (Mock) |
| `advance_production_status()` | 推进生产流程状态 |

### 4.9 订单状态机 [state_machine.py](file:///e:/python-code/ClayWords/backend/app/services/order/state_machine.py)

**状态流转图**:

```
pending → confirmed → dispatched → producing → glazing → firing
   ↓          ↓                                      ↓
cancelled  cancelled                              cooling
                                                         ↓
                                                         QC
                                                         ↓
                                                      completed
                                                         ↓
                                                   shipping_pending
                                                         ↓
                                                       shipped
                                                         ↓
                                                       delivered
```

**关键规则**:
- 只有特定状态可以取消 (pending/confirmed/dispatched)
- 支付后从 pending → confirmed
- 派单后从 confirmed → dispatched
- 生产流程按固定顺序推进

### 4.10 派单服务 [dispatcher.py](file:///e:/python-code/ClayWords/backend/app/services/dispatch/dispatcher.py)

**核心函数**: `dispatch_to_studio()`

**派单流程**:
1. 获取设计方案信息 (DesignVersion)
2. 查询可用工作室 (SQL 硬约束: current_load < capacity, rating >= 4.0, 限 50 个)
3. 四维评分排序 (`rank_studios()`)
4. **原子 CAS 占位**: 逐个尝试 `UPDATE ... WHERE current_load < capacity` 防止超卖
5. 占位成功 → 关联订单 → 返回派单结果
6. 全部失败 → fallback 到中央兜底工作室或标记人工派单

**并发安全**: 使用原子 UPDATE + CAS 避免多 Worker 抢单超卖。

### 4.11 四维评分算法 [scoring.py](file:///e:/python-code/ClayWords/backend/app/services/dispatch/scoring.py)

**权重配置**:

| 维度 | 权重 | 计算方式 |
|------|------|----------|
| 工艺匹配 (craft) | 35% | 专长标签匹配度 (完全匹配1.0/部分0.7/无0.2) |
| 产能可用 (capacity) | 25% | 剩余产能/总产能，偏好中等负载 (30%-80%) |
| 地理位置 (geo) | 15% | 同城市1.0/同省0.8/其他0.5 |
| 用户评分 (rating) | 25% | 4.0→0.0 线性映射到 5.0→1.0 |

**硬约束 (一票否决)**:
- 评分 < 4.0
- 剩余容量 ≤ 0

---

## 5. 前端核心模块

### 5.1 应用入口 [main.ts](file:///e:/python-code/ClayWords/frontend/src/main.ts)

**初始化流程**:
1. 创建 Vue 应用实例
2. 注册 Pinia 状态管理
3. 注册 Vue Router
4. 注册 Element Plus 组件库
5. 挂载到 `#app`

### 5.2 路由配置 [index.ts](file:///e:/python-code/ClayWords/frontend/src/router/index.ts)

**路由守卫逻辑**:
- `requiresAuth: true` → 检查 localStorage 中是否有 role (未登录跳转登录页)
- `role: 'studio'/'admin'` → 角色校验，不匹配则跳转到对应首页

**路由表** (11 个路由):

| 路径 | 页面 | 权限 |
|------|------|------|
| `/` | 首页 | 公开 |
| `/login` | 登录页 | 公开 |
| `/design` | 对话式设计台 | 登录用户 |
| `/orders` | 我的订单 | 登录用户 |
| `/profile` | 个人资料 | 登录用户 |
| `/studio` | 工作室订单列表 | 工作室角色 |
| `/studio/orders/:orderId` | 工作室订单详情 | 工作室角色 |
| `/admin` | 管理仪表盘 | 管理员 |
| `/admin/studios` | 工作室审核 | 管理员 |
| `/admin/orders` | 全部订单 | 管理员 |

### 5.3 认证状态 [auth.ts](file:///e:/python-code/ClayWords/frontend/src/stores/auth.ts)

**Pinia Store** 管理:
- 用户信息 (user_id, nickname, phone, role)
- 登录/登出逻辑
- Token 管理 (Cookie)
- 角色判断 (isAdmin, isStudio)

### 5.4 API 客户端 [client.ts](file:///e:/python-code/ClayWords/frontend/src/api/client.ts)

**Axios 封装**:
- 基础 URL 配置 (Vite proxy 代理到后端 8000)
- 请求拦截器: 注入认证 Cookie
- 响应拦截器: 统一错误处理、401 自动跳转登录
- 重试机制 (可配置)
- SSE 支持 (EventSource)

### 5.5 核心页面 - 设计台 [DesignView.vue](file:///e:/python-code/ClayWords/frontend/src/views/DesignView.vue)

**三栏布局**:
- **左栏**: ChatPanel (对话流) + OptionCards (方案选择)
- **中栏**: PreviewCanvas (Three.js 3D 预览)
- **右栏**: DispatchPanel (派单信息)
- **底部**: 输入工具栏 (文本输入 + 参考图上传 + 3D生成 + 发送)

### 5.6 Three.js 3D 查看器 [ThreeViewer.vue](file:///e:/python-code/ClayWords/frontend/src/components/ThreeViewer.vue)

**功能**:
- glTF/GLB 模型加载
- 轨道控制器 (旋转/缩放/平移)
- 自动旋转
- 灯光设置 (陶土材质适配)
- 加载进度指示

---

## 6. Worker 任务处理

### 6.1 Worker 架构 [main.py](file:///e:/python-code/ClayWords/worker/main.py)

**基于 ARQ (Async Redis Queue)**:
- 任务队列: Redis Streams
- 最大并发: 10 jobs
- 结果保留: 1 小时
- 进度推送: Redis Pub/Sub → SSE 转发到前端

### 6.2 3D 生成流水线

**三条并行流水线**:

| 流水线 | 模块 | 说明 |
|--------|------|------|
| **Template Pipeline** | [template_pipeline.py](file:///e:/python-code/ClayWords/worker/pipelines/template_pipeline.py) | 基于模板匹配，速度快 |
| **Generative Pipeline** | [generative_pipeline.py](file:///e:/python-code/ClayWords/worker/pipelines/generative_pipeline.py) | AI 文生模型，创意强 |
| **Hybrid Pipeline** | [hybrid_pipeline.py](file:///e:/python-code/ClayWords/worker/pipelines/hybrid_pipeline.py) | 模板 + AI 混合方案 |

**处理流程**:
```
1. 解析设计参数 (10%)
2. 并行执行三条流水线:
   - 模板匹配 (30% → 40%)
   - AI 生成 (50% → 60%)
   - 混合生成 (55%)
3. 工艺校验 (70% → 80%)
4. 后处理/生成缩略图 (90% → 95%)
5. 完成 (100%) → 结果存入 Redis
```

### 6.3 工艺校验模块 [craft_check/](file:///e:/python-code/ClayWords/worker/craft_check/)

| 校验项 | 文件 | 说明 |
|--------|------|------|
| 壁厚检测 | wall_thickness.py | 确保最小壁厚满足烧制要求 |
| 悬垂角度 | overhang.py | 检测过大悬垂 (防止变形/坍塌) |
| 收缩率 | shrinkage.py | 根据材质计算烧结收缩 |
| 比例检测 | aspect_ratio.py | 检测过高/过窄比例 |
| 底座稳定性 | base_stability.py | 重心分析，防止倾倒 |
| 自动修复 | auto_fix.py | 生成修复建议 |

---

## 7. 数据模型与数据库

### 7.1 ER 关系图

```
┌──────────┐       ┌──────────────┐       ┌─────────────┐
│  users   │       │  studios     │       │studio_craft │
│──────────│       │──────────────│       │_overrides   │
│ user_id  │──┐    │ studio_id    │◄──────┤ studio_id   │
│ phone    │  │    │ name         │       │ min_wall_   │
│ nickname │  │    │ location     │       │ thickness   │
│ role     │  │    │ specialties  │       │ shrinkage   │
│ studio_id│◄┘    │ capacity     │       └─────────────┘
└────┬─────┘       │ current_load │
     │             │ rating       │            ┌─────────────┐
     │             └──────┬───────┘            │idempotency_ │
     │                    │                    │  keys       │
     ▼                    ▼                    └─────────────┘
┌──────────┐       ┌──────────────┐
│ sessions │       │   orders     │       ┌─────────────┐
│──────────│       │──────────────│       │ order_logs  │
│session_id│◄──┐   │ order_id     │◄──────┤ order_id    │
│ user_id  │   │   │ user_id      │       │ from_status │
│ title    │   │   │ session_id   │       │ to_status   │
└────┬─────┘   │   │ option_id    │       │ operator    │
     │         │   │ studio_id    │       └─────────────┘
     ▼         │   │ status       │
┌──────────┐   │   │ total_price  │       ┌─────────────┐
│session_  │   │   └──────┬───────┘       │ shipments   │
│messages  │   │          │               └─────────────┘
└──────────┘   │          │
     │         │          ▼
     ▼         │   ┌──────────────┐       ┌─────────────┐
┌──────────┐   │   │ design_      │       │  payments   │
│ designs  │   └──►│ versions     │       └─────────────┘
│──────────│       │──────────────│
│design_id │◄──┐   │ version_id   │       ┌─────────────┐
│session_id│   │   │ design_id    │       │   tasks     │
│ params   │   │   │ glb_url      │       └─────────────┘
└────┬─────┘   │   │ craft_check  │
     │         │   │ price        │       ┌─────────────┐
     │         │   └──────────────┘       │  uploads    │
     └─────────┘                          └─────────────┘
┌──────────────────────────────────────────────────────┐
│                 design_templates                      │
│  (含 1536 维 pgvector embedding 用于相似检索)         │
└──────────────────────────────────────────────────────┘
```

### 7.2 数据表清单 (14 张表)

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `users` | 用户表 | user_id, phone_hash, phone_encrypted, email_encrypted, nickname, role |
| `studios` | 工作室表 | studio_id, name, location, specialties, capacity, current_load, rating |
| `studio_craft_overrides` | 工艺校准配置 | studio_id, min_wall_thickness, shrinkage_rate |
| `sessions` | 设计会话 | session_id, user_id, title |
| `session_messages` | 会话消息 | session_id, role, content, design_params |
| `design_templates` | 设计模板 (含向量) | template_id, name, category, embedding(1536维), glb_url |
| `designs` | 设计 | design_id, session_id, design_params |
| `design_versions` | 设计版本/方案 | version_id, design_id, pipeline, glb_url, craft_check_result, price |
| `orders` | 订单 | order_id, user_id, studio_id, option_id, status, idempotency_key |
| `order_logs` | 订单状态日志 | order_id, from_status, to_status, operator, reason |
| `payments` | 支付记录 | 支付流水、金额、状态 |
| `idempotency_keys` | 幂等性键 | key, resource_id, response_body, expires_at |
| `tasks` | 任务记录 | task_id, state, payload, progress, error_message |
| `uploads` | 文件上传 | upload_id, object_key, file_name, mime_type, state, scan_result |

### 7.3 自定义类型 [types.py](file:///e:/python-code/ClayWords/backend/app/models/types.py)

| 类型 | 说明 |
|------|------|
| `Vector(dim)` | pgvector 向量类型，用于模板 embedding |
| `EncryptedStr(length)` | AES-GCM 加密字符串，自动加解密 |
| `JSONB()` | PostgreSQL JSONB 类型 |

---

## 8. 关键类与函数说明

### 8.1 后端核心类

#### Settings 配置类
[config.py:21-139](file:///e:/python-code/ClayWords/backend/app/core/config.py#L21-L139)

```python
class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "staging", "production"]
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    REDIS_URL: str
    MINIO_*: object storage config
    CRYPTO_PEPPER: str  # 加密密钥
    JWT_SECRET_KEY: str
    CLAMAV_ENABLED: bool = False
    
    def is_production(self) -> bool: ...
    def cors_origins_list(self) -> list: ...
    def _check_production_secrets(self) -> "Settings": ...  # 生产强校验
```

#### CryptoService 加密服务
[crypto.py:12-41](file:///e:/python-code/ClayWords/backend/app/core/crypto.py#L12-L41)

```python
class CryptoService:
    def __init__(self, pepper: Optional[str] = None):
        # SHA-256(pepper) 派生 32-byte 密钥
        
    def encrypt(self, plaintext: str) -> str:
        # AES-256-GCM: 随机 12-byte nonce + ciphertext → Base64
        
    def decrypt(self, encrypted: str) -> str:
        # 逆向解密
        
    def hash_phone(self, phone: str) -> str:
        # SHA-256(规范化手机号) → hex，用于唯一约束/查找
```

#### RedisClient Redis 客户端
[redis.py:9-127](file:///e:/python-code/ClayWords/backend/app/core/redis.py#L9-L127)

封装 KV、Pub/Sub、Streams、Consumer Groups、Sets、Lua Scripting。

#### MinIOClient 存储客户端
[storage.py:13-117](file:///e:/python-code/ClayWords/backend/app/core/storage.py#L13-L117)

预签名 URL 生成、对象 CRUD、直传支持、服务端字节上传。

### 8.2 服务层关键函数

#### dispatch_to_studio 智能派单
[dispatcher.py:79-174](file:///e:/python-code/ClayWords/backend/app/services/dispatch/dispatcher.py#L79-L174)

```python
async def dispatch_to_studio(
    db: AsyncSession,
    order_id: str,
    option_id: str,
    session_id: str
) -> DispatchResult:
    """
    核心派单逻辑:
    1. 获取设计方案信息
    2. SQL 硬约束过滤可用工作室 (current_load < capacity, rating >= 4.0, LIMIT 50)
    3. 四维评分排序
    4. 原子 CAS 占位: UPDATE Studio SET current_load+1 WHERE current_load < capacity
    5. 成功则关联订单，失败尝试下一个
    6. 全部失败 → fallback 中央兜底工作室或标记人工派单
    """
```

#### score_studio 四维评分
[scoring.py:194-231](file:///e:/python-code/ClayWords/backend/app/services/dispatch/scoring.py#L194-L231)

```python
def score_studio(
    studio: StudioInfo,
    params: DesignParams,
    weights: dict = DEFAULT_WEIGHTS,
    target_locations: list[str] = None
) -> ScoreBreakdown:
    """
    硬约束前置: rating < 4.0 或无容量 → 直接返回 0 分
    加权总分 = craft*0.35 + capacity*0.25 + geo*0.15 + rating*0.25
    """
```

#### update_order_status 订单状态更新
[order_service.py:45-91](file:///e:/python-code/ClayWords/backend/app/services/order/order_service.py#L45-L91)

```python
async def update_order_status(
    db: AsyncSession,
    order_id: str,
    new_status: OrderStatus,
    operator: str = "system",
    reason: str = "",
    extra_data: dict = None,
) -> TransitionResult:
    """带状态机校验的订单状态更新，自动写入 order_logs"""
```

### 8.3 Worker 处理函数

#### process_design_gen 设计生成任务
[worker/main.py:42-168](file:///e:/python-code/ClayWords/worker/main.py#L42-L168)

```python
async def process_design_gen(
    ctx: dict,
    session_id: str,
    design_params: dict,
    task_id: str
) -> dict:
    """
    ARQ 任务函数:
    - 阶段进度报告 (parsing → template_match → gen_inference → craft_check → post_process → done)
    - 并行执行三条流水线 (template/generative/hybrid)
    - 结果存入 Redis (1小时过期)
    - 通过 Pub/Sub 实时推送进度
    """
```

---

## 9. 依赖关系

### 9.1 Python 依赖 ([requirements.txt](file:///e:/python-code/ClayWords/backend/requirements.txt))

| 依赖 | 版本 | 用途 |
|------|------|------|
| fastapi | ≥0.115.0 | Web 框架 |
| uvicorn[standard] | ≥0.30.0 | ASGI 服务器 |
| pydantic / pydantic-settings | ≥2.0.0 | 数据校验/配置 |
| sqlalchemy[asyncio] | ≥2.0.0 | ORM (异步) |
| asyncpg | ≥0.29.0 | PostgreSQL 异步驱动 |
| alembic | ≥1.13.0 | 数据库迁移 |
| redis | ≥5.0.0 | Redis 客户端 |
| arq | ≥0.26.0 | 异步任务队列 |
| structlog | ≥24.0.0 | 结构化日志 |
| python-jose[cryptography] | ≥3.3.0 | JWT |
| passlib[bcrypt] | ≥1.7.0 | 密码哈希 |
| python-multipart | ≥0.0.9 | 文件上传 |
| httpx | ≥0.27.0 | HTTP 客户端 (调用外部API) |
| boto3 / minio | ≥1.34.0 / ≥7.2.0 | S3/MinIO 客户端 |
| numpy | ≥1.26.0 | 工艺校验数值计算 |
| pytest / pytest-asyncio / pytest-cov | - | 测试框架 |

### 9.2 前端依赖 ([package.json](file:///e:/python-code/ClayWords/frontend/package.json))

| 依赖 | 版本 | 用途 |
|------|------|------|
| vue | ^3.4.0 | 前端框架 |
| vue-router | ^4.2.0 | 路由 |
| pinia | ^2.1.0 | 状态管理 |
| element-plus | ^2.5.0 | UI 组件库 |
| axios | ^1.6.0 | HTTP 客户端 |
| three | ^0.170.0 | 3D 渲染 |
| @types/three | ^0.170.0 | Three.js 类型 |
| typescript | ^5.3.0 | 类型系统 |
| vite | ^5.4.0 | 构建工具 |
| @vitejs/plugin-vue | ^5.0.0 | Vue 插件 |
| vue-tsc | ^2.0.0 | Vue 类型检查 |
| eslint | ^8.57.0 | 代码检查 |
| playwright | ^1.61.0 | E2E 测试 |

### 9.3 外部服务依赖

| 服务 | 用途 | 可选/必需 |
|------|------|-----------|
| PostgreSQL 16 + pgvector | 主数据存储 + 向量检索 | 必需 |
| Redis 7 | 缓存、任务队列、Pub/Sub、限流、JWT 黑名单 | 必需 |
| MinIO | 对象存储 (3D模型、图片、文件) | 必需 |
| ClamAV | 文件病毒扫描 | 生产必需 |
| Prometheus + Grafana + Alertmanager | 监控告警 | 生产推荐 |
| 支付宝 | 支付 | 生产必需 |
| 混元3D API | 3D 模型生成 | 可选 (Mock模式可运行) |
| 通义千问/OpenAI | LLM 需求解析 | 可选 |

### 9.4 模块依赖图 (后端)

```
API 层 (api/*.py)
    ↓ 依赖
服务层 (services/*)
    ├── order_service → state_machine
    ├── dispatcher → scoring → policy
    ├── payment_service
    ├── hunyuan3d/client
    ├── logistics/registry
    └── alerting_service
    ↓ 依赖
核心层 (core/*)
    ├── config
    ├── crypto
    ├── redis
    ├── storage
    ├── rate_limit
    ├── metrics
    ├── clamav
    └── logging_middleware
    ↓ 依赖
数据层 (db/, models/)
    ├── session (AsyncEngine)
    └── entities (SQLAlchemy models)
```

---

## 10. 运行与部署指南

### 10.1 环境要求

| 组件 | 最低版本 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 16 + pgvector 0.8.2 |
| Redis | 7+ |
| MinIO | 最新稳定版 |
| Docker / Docker Compose | 20+ |
| Kubernetes (生产) | 1.27+ |
| Helm | 3+ |

### 10.2 本地开发启动

#### 方式一: Docker Compose (推荐)

```bash
# 1. 启动基础设施 (PostgreSQL + Redis + MinIO + ClamAV + 监控)
make up
# 或: docker compose -f infra/docker-compose.yml up -d

# 2. 等待服务健康 (约 30 秒，ClamAV 需 5-30 分钟初始化病毒库)

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入必要的 API Key (或保持默认使用 Mock)

# 4. 数据库迁移
cd backend
alembic upgrade head

# 5. 种子数据 (可选)
cd ..
make db.seed

# 6. 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 7. 启动前端 (新终端)
cd frontend
npm install
npm run dev  # http://localhost:5173
```

#### 方式二: 手动安装依赖

```bash
# 后端
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 10.3 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | 用户界面 |
| 后端 API | http://localhost:8000 | API 根路径 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| ReDoc | http://localhost:8000/redoc | 替代文档 |
| MinIO Console | http://localhost:9001 | 对象存储管理 (claywords/claywords_secret) |
| Prometheus | http://localhost:9090 | 指标查询 |
| Grafana | http://localhost:3000 | 监控仪表盘 (admin/admin) |
| Alertmanager | http://localhost:9093 | 告警管理 |

### 10.4 常用 Makefile 命令

| 命令 | 说明 |
|------|------|
| `make up` | 启动基础设施容器 |
| `make down` | 停止基础设施容器 |
| `make logs` | 查看容器日志 |
| `make test` | 运行后端单元测试 |
| `make lint` | 代码检查 (ruff + eslint) |
| `make db.migrate` | 执行数据库迁移 |
| `make db.seed` | 写入种子数据 |
| `make clean` | 清理容器卷 + 缓存 |

### 10.5 Kubernetes 生产部署 (Helm)

```bash
cd helm/claywords

# 安装
helm install claywords . -n claywords --create-namespace \
  -f values-production.yaml

# 升级
helm upgrade claywords . -n claywords -f values-production.yaml

# 查看状态
kubectl get pods -n claywords
kubectl get svc -n claywords
```

**生产部署检查清单**:
- [ ] 替换所有 `dev_*_change_in_production` 占位密钥
- [ ] 设置 `ENVIRONMENT=production`
- [ ] 配置 `MINIO_SECURE=true` (HTTPS)
- [ ] 配置支付宝密钥和 HTTPS 回调 URL
- [ ] 设置 `CENTRAL_STUDIO_ID` (兜底工作室)
- [ ] 启用 ClamAV (`CLAMAV_ENABLED=true`)
- [ ] 配置数据库持久化存储
- [ ] 配置 Redis 持久化 (AOF)
- [ ] 设置 Ingress TLS 证书
- [ ] 配置备份策略

---

## 11. 测试体系

### 11.1 测试文件清单 ([backend/tests/](file:///e:/python-code/ClayWords/backend/tests/))

| 测试文件 | 覆盖范围 |
|----------|----------|
| test_auth_profile.py | 认证 + 个人资料 |
| test_jwt_blacklist.py | JWT 黑名单 |
| test_crypto.py | 加密/解密/哈希 |
| test_order_service.py | 订单服务 CRUD |
| test_order_state_machine.py | 状态机转换 |
| test_dispatch_scoring.py | 四维评分算法 |
| test_payment.py / test_payment_service.py | 支付流程 |
| test_logistics_provider.py | 物流 Provider |
| test_hunyuan3d_worker.py | 混元3D Worker |
| test_uploads_scan.py | 上传 + 病毒扫描 |
| test_clamav.py | ClamAV 集成 |
| test_rate_limit.py | 限流中间件 |
| test_logging_middleware.py | 日志中间件 |
| test_metrics.py | Prometheus 指标 |
| test_alerting.py | 告警服务 |
| test_admin_api.py | 管理后台 API |
| test_smoke.py | 冒烟测试 |
| test_module_imports.py | 模块导入检查 |
| test_craft_check.py | 工艺校验 |

### 11.2 运行测试

```bash
# 后端全量测试
cd backend
pytest tests/ -v --cov=app

# 运行单个测试文件
pytest tests/test_order_state_machine.py -v

# 带覆盖率报告
pytest tests/ -v --cov=app --cov-report=html
```

### 11.3 前端构建验证

```bash
cd frontend
npm run build   # 类型检查 + 构建
npm run preview # 预览构建产物
```

---

## 12. 监控与运维

### 12.1 Prometheus 指标

**中间件指标** ([metrics.py](file:///e:/python-code/ClayWords/backend/app/core/metrics.py)):

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数 (按 method/path/status) |
| `http_request_duration_seconds` | Histogram | 请求耗时分布 |
| `orders_total` | Counter | 订单总数 (按状态) |
| `dispatch_total` | Counter | 派单次数 (按结果) |
| `studio_load` | Gauge | 工作室当前负载 |
| `hunyuan3d_tasks_total` | Counter | 混元3D 任务数 |

### 12.2 Grafana 仪表盘

预置仪表盘: [claywords-overview.json](file:///e:/python-code/ClayWords/infra/grafana/provisioning/dashboards/claywords-overview.json)

包含面板:
- 请求 QPS + 延迟 P50/P95/P99
- 错误率 (4xx/5xx)
- 订单状态分布
- 派单成功率
- 工作室负载
- 活跃任务数
- Redis/PostgreSQL 连接池状态

### 12.3 SLO 告警规则

[slo.yml](file:///e:/python-code/ClayWords/infra/prometheus/rules/slo.yml)

| 告警 | 条件 | 级别 |
|------|------|------|
| APIErrorRateHigh | 5xx 错误率 > 5% 持续 5 分钟 | P1 |
| APILatencyHigh | P95 延迟 > 2s 持续 5 分钟 | P2 |
| DatabaseConnectionsHigh | 连接池使用率 > 80% | P2 |
| RedisDisconnected | Redis 连接失败 | P1 |
| WorkerBacklogHigh | 任务队列积压 > 100 | P2 |
| ClamAVDown | ClamAV 服务不可达 | P1 |

### 12.4 日志规范

使用 structlog JSON 格式输出，包含字段:
- `timestamp`: ISO 8601 时间戳
- `level`: 日志级别
- `event`: 事件名称
- `trace_id`: 请求追踪 ID (X-Request-ID)
- `path` / `method`: HTTP 请求信息
- 其他业务上下文字段

### 12.5 备份恢复

**PostgreSQL 备份**:
```bash
./scripts/backup_pg.sh   # 每日全量备份
./scripts/restore_pg.sh <backup_file>  # 恢复
```

**Redis 备份**:
```bash
./scripts/backup_redis.sh  # RDB + AOF 备份
```

---

## 13. 优化建议与方案

基于代码分析，以下是按优先级分类的优化建议：

### 13.1 高优先级 (P0) - 生产必须项

| 问题 | 影响 | 建议方案 | 相关文件 |
|------|------|----------|----------|
| **JWT 黑名单内存问题** | 大规模用户时 Redis 内存占用高 | 1. 使用 Redis SET + TTL 自动过期<br>2. 黑名单只存 JTI (jwt id)，不存完整 token<br>3. 定期清理过期条目 | [redis.py](file:///e:/python-code/ClayWords/backend/app/core/redis.py) 黑名单相关 |
| **Worker 结果只存 Redis** | Redis 重启/内存淘汰导致任务结果丢失 | 1. 任务结果双写 PostgreSQL `tasks` 表<br>2. Redis 作为缓存层，DB 作为持久层<br>3. 前端轮询时先查 Redis，miss 则回源 DB | [worker/main.py](file:///e:/python-code/ClayWords/worker/main.py#L136-L153) |
| **SSE 连接无认证** | 未授权用户可订阅他人任务进度 | 1. SSE 连接时验证 Cookie/Token<br>2. 校验 task_id 归属权<br>3. 按 user_id 隔离 channel | [api/sse.py](file:///e:/python-code/ClayWords/backend/app/api/sse.py) |
| **大对象一次性读入内存** | 扫描大 GLB 文件可能 OOM | 1. 实现 ClamAV INSTREAM 分块扫描<br>2. 限制单文件大小 (当前 MAX_MODEL_SIZE 已有)<br>3. 上传时校验 Content-Length | [storage.py:95-109](file:///e:/python-code/ClayWords/backend/app/core/storage.py#L95-L109) |
| **MinIO 公网 URL 暴露** | 预签名 URL 泄露可被恶意访问 | 1. 缩短预签名 URL 有效期 (当前1小时)<br>2. 敏感资源使用临时 GET URL 而非 public_url<br>3. 启用 Bucket Policy 限制来源 | [storage.py](file:///e:/python-code/ClayWords/backend/app/core/storage.py) |

### 13.2 中优先级 (P1) - 性能与可维护性

#### 13.2.1 内存优化

| 问题 | 当前状况 | 优化方案 |
|------|----------|----------|
| **DB 会话未及时释放** | SSE 长连接持有 DB 会话可能耗尽连接池 | 1. SSE 端点不注入 DB session，需要时手动获取短会话<br>2. 监控连接池等待时间指标<br>3. 连接池大小按副本数/并发量调优 |
| **Redis 结果无淘汰策略** | 任务结果 `ex=3600` 但 keyspace 可能持续增长 | 1. 配置 Redis maxmemory-policy (allkeys-lru)<br>2. 对任务结果设置更短 TTL (如 30 分钟)<br>3. 成功归档的结果主动 DEL |
| **图片/GLB 未压缩** | MinIO 存储原始文件占用空间 | 1. 上传时自动生成缩略图 (已有 post_process 阶段)<br>2. GLB 文件启用 Draco 几何压缩<br>3. 图片使用 WebP 格式 |
| **numpy 数组未释放** | craft_check 处理大模型可能内存泄漏 | 1. 使用 `with` 语句管理 numpy 数组生命周期<br>2. 大对象显式 `del` + `gc.collect()`<br>3. 处理完立即卸载 trimesh 场景 |

#### 13.2.2 计算优化

| 问题 | 当前状况 | 优化方案 |
|------|----------|----------|
| **工作室查询 N+1** | 订单列表查询可能触发多次工作室查询 | 1. 使用 `selectinload`/`joinedload` 预加载关联<br>2. 列表接口只返回必要字段，避免加载大 JSON<br>3. 实现批量查询接口 |
| **派单评分每次全量计算** | 高并发下每次派单都要遍历 50 个工作室评分 | 1. 工作室评分缓存到 Redis (工作室信息变更时失效)<br>2. 可用工作室维护 Redis ZSET (按评分排序)<br>3. 派单时直接 ZPOP 或原子 CAS |
| **pgvector 检索未优化** | 模板向量检索每次全表扫描 | 1. 为 embedding 列创建 IVFFlat/HNSW 索引<br>2. 设置合适的 lists 参数 (建议 `rows/1000`)<br>3. 查询时使用 `vector_cosine_ops` 操作符类 |
| **AES 加密无缓存** | 每次加解密都重新派生密钥 | 1. `CryptoService` 单例已缓存 key/aesgcm，保持现状<br>2. 避免在热路径重复创建 CryptoService 实例 |

```sql
-- pgvector 索引建议
CREATE INDEX idx_design_templates_embedding 
ON design_templates 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

#### 13.2.3 并行/异步优化

| 问题 | 当前状况 | 优化方案 |
|------|----------|----------|
| **流水线串行执行** | Worker 三条流水线通过线程池并行，但进度报告阻塞 | 1. 使用 `asyncio.gather` 替代手动 run_in_executor<br>2. 每条流水线独立报告进度<br>3. 实现流水线超时熔断 (如 AI 生成 60s 无响应跳过) |
| **SSE 广播无扇出** | 每个 SSE 连接独立订阅 Redis Pub/Sub | 1. 实现本地 Pub/Sub 扇出: 一个 Redis 订阅 → 多个本地连接<br>2. 使用 asyncio.Queue 做进程内广播<br>3. 相同 task_id 复用同一 Redis 订阅 |
| **数据库事务粒度过大** | 派单等长流程在单个事务中 | 1. 拆分事务: 占位 → 业务逻辑 → 提交 → 异步后处理<br>2. 派单占位使用短事务 + 乐观锁<br>3. 非关键路径 (日志、metrics) 异步写入 |
| **HTTP 客户端无连接池** | httpx 每次创建新客户端 | 1. 全局共享 httpx.AsyncClient 实例<br>2. 配置连接池 limits (max_connections)<br>3. 复用 HTTP Keep-Alive |

#### 13.2.4 代码结构优化

| 问题 | 当前状况 | 优化方案 |
|------|----------|----------|
| **Pydantic Schema 分散** | API 直接返回 ORM 对象或手动构造 dict | 1. 统一使用 Pydantic ResponseModel<br>2. 请求/响应 Schema 集中到 schemas/ 目录<br>3. 使用 `model_config = {"from_attributes": True}` |
| **循环依赖风险** | services 之间互相 import | 1. 引入事件总线 (Event Bus) 解耦服务<br>2. 将共享接口下沉到 core/<br>3. 使用 TYPE_CHECKING 延迟导入 |
| **魔法数字散落** | 状态字符串、权重值硬编码 | 1. 使用 Enum 类定义所有状态/常量<br>2. 权重等配置移到 Settings 或配置文件<br>3. 定义状态转换矩阵而非硬编码 if-else |
| **错误处理不统一** | 部分地方直接 raise HTTPException，部分返回 dict | 1. 定义业务异常基类 + 全局异常处理器<br>2. 使用统一的错误码规范<br>3. 错误响应包含 trace_id + 可理解的 message |

### 13.3 低优先级 (P2) - 长期演进

#### 13.3.1 架构演进建议

1. **引入 CQRS 模式**: 读写分离，订单查询走只读副本或 Redis 缓存
2. **引入事件驱动**: 订单状态变更发布 Domain Event，解耦支付/物流/通知
3. **API 版本化**: URL 前缀 `/api/v1` 已有，确保 v2 兼容性策略
4. **OpenTelemetry 接入**: 替换当前 metrics/日志，实现统一 Trace
5. **gRPC 内部通信**: 后端 ↔ Worker 使用 gRPC 替代 Redis 队列，获得类型安全和流式控制

#### 13.3.2 数据层优化

1. **读写分离**: PostgreSQL 主从复制，查询走从库
2. **分表策略**: orders/order_logs 按时间分表 (如按月)
3. **引入缓存层**: 工作室信息、模板列表等热点数据缓存到 Redis
4. **多租户隔离**: 未来若支持平台多工作室独立域名，增加 tenant_id

#### 13.3.3 前端优化

1. **组件按需引入**: Element Plus 使用 unplugin-auto-import 按需引入，减少包体积
2. **3D 模型懒加载**: Three.js 和 GLB 模型使用动态 import() 拆分 chunk
3. **SSE 自动重连**: 实现指数退避重连 + Last-Event-ID 断点续传
4. **虚拟滚动**: 订单列表数据量大时使用虚拟滚动
5. **Service Worker**: 静态资源缓存 + 离线提示

#### 13.3.4 安全加固

1. **CSP 严格模式**: 配置严格的 Content-Security-Policy
2. **JWT 短令牌 + Refresh Rotation**: Access Token 缩短到 15 分钟，Refresh Token 轮换
3. **敏感操作二次验证**: 支付/地址修改等操作要求重新验证
4. **审计日志持久化**: 所有管理操作写入不可变日志
5. **依赖漏洞扫描**: CI 集成 safety/bandit/semgrep 自动扫描

### 13.4 具体代码优化示例

#### 优化 1: httpx 客户端复用

```python
# 优化前: 每次调用都创建新客户端
async def call_hunyuan3d(payload):
    async with httpx.AsyncClient() as client:  # 每次新建 TCP 连接
        resp = await client.post(url, json=payload)
        return resp.json()

# 优化后: 全局复用连接池
class HTTPClientManager:
    _instance = None
    _client: httpx.AsyncClient = None
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return cls._client
```

#### 优化 2: SSE 连接鉴权 + 扇出优化

```python
# 优化后: 单 Redis 订阅扇出到多 SSE 连接
class SSEManager:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._redis_task: asyncio.Task = None
    
    async def subscribe(self, task_id: str, user_id: str) -> asyncio.Queue:
        # 校验权限: 确认 task_id 属于 user_id
        await self._verify_task_ownership(task_id, user_id)
        
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[task_id].add(queue)
        
        # 该 task_id 首次订阅时才订阅 Redis
        if len(self._subscribers[task_id]) == 1:
            await self._start_redis_subscription(task_id)
        
        return queue
    
    async def _redis_listener(self, task_id: str):
        """单个 Redis 订阅扇出给该任务的所有本地连接"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task:{task_id}:progress")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    # 扇出到所有本地订阅者
                    queues = self._subscribers.get(task_id, set())
                    for q in list(queues):
                        try:
                            q.put_nowait(message["data"])
                        except asyncio.QueueFull:
                            pass  # 慢消费者丢弃消息
        finally:
            await pubsub.unsubscribe(f"task:{task_id}:progress")
```

#### 优化 3: 工作室评分缓存

```python
# 优化后: 工作室基础信息缓存，派单时只做增量计算
async def get_ranked_studios_cached(db, params: DesignParams) -> list[tuple[StudioInfo, ScoreBreakdown]]:
    """带缓存的工作室排名"""
    cache_key = "studios:available"
    
    # 1. 尝试从缓存获取可用工作室列表
    cached = await redis_client.get(cache_key)
    if cached:
        studios = [StudioInfo(**s) for s in json.loads(cached)]
    else:
        studios = await get_all_available_studios(db)
        # 缓存 30 秒，工作室信息变更时主动失效
        await redis_client.set(
            cache_key, 
            json.dumps([asdict(s) for s in studios]), 
            ex=30
        )
    
    # 2. 内存中评分排序 (轻量计算，无需缓存)
    return rank_studios(studios, params)
```

#### 优化 4: 数据库预加载关联

```python
# 优化前: N+1 查询
async def list_orders(db, user_id):
    result = await db.execute(select(Order).where(Order.user_id == user_id))
    orders = list(result.scalars().all())
    for order in orders:
        # 每次访问 order.studio 都触发新查询!
        studio_name = order.studio.name if order.studio else None

# 优化后: 预加载
async def list_orders(db, user_id):
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(
            selectinload(Order.studio),  # 预加载工作室
            selectinload(Order.logs)     # 预加载日志
        )
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

### 13.5 优化实施路线图

| 阶段 | 时间 | 内容 |
|------|------|------|
| **第一周** | P0 紧急修复 | SSE 鉴权、结果双写 DB、httpx 连接池复用、ClamAV 流式扫描 |
| **第二周** | P1 性能优化 | N+1 查询修复、工作室评分缓存、pgvector 索引、SSE 扇出优化 |
| **第三-四周** | P1 架构优化 | 统一异常处理、Schema 规范化、全局事件总线、流水线超时熔断 |
| **长期** | P2 演进 | CQRS、读写分离、OpenTelemetry、前端包体积优化、安全加固 |

---

## 附录

### A. 环境变量完整列表

参考 [.env.example](file:///e:/python-code/ClayWords/.env.example) 和 [config.py](file:///e:/python-code/ClayWords/backend/app/core/config.py)。

### B. 数据库迁移版本

| 版本 | 说明 |
|------|------|
| c845aee3c751_001 | 初始 Schema |
| 86ad82ebb698_002 | 添加 uploads 表 |
| a1b2c3d4e5f6_003 | 添加用户角色 |
| b5e7f8a9c0d1_004 | 时区感知时间戳 |
| c0d1e2f3a4b5_005 | 添加用户昵称 |
| d1e2f3a4b5c6_006 | 添加用户社交绑定 |

### C. 相关文档索引

| 文档 | 路径 |
|------|------|
| 项目分析报告 | [docs/01-项目分析报告-2026-06-23.md](file:///e:/python-code/ClayWords/docs/01-项目分析报告-2026-06-23.md) |
| 技术方案 v1.3 | [docs/11-技术方案v1.3.md](file:///e:/python-code/ClayWords/docs/11-技术方案v1.3.md) |
| 安全自检 OWASP | [docs/31-安全自检-OWASP-Top10.md](file:///e:/python-code/ClayWords/docs/31-安全自检-OWASP-Top10.md) |
| 生产部署检查清单 | [docs/21-生产部署检查清单.md](file:///e:/python-code/ClayWords/docs/21-生产部署检查清单.md) |
| 备份恢复手册 | [docs/22-备份恢复手册.md](file:///e:/python-code/ClayWords/docs/22-备份恢复手册.md) |
| 监控仪表盘 | [docs/24-业务监控仪表盘.md](file:///e:/python-code/ClayWords/docs/24-业务监控仪表盘.md) |
| 代码分析演进方案 | [docs/50-全面代码分析与演进方案-2026-06-24.md](file:///e:/python-code/ClayWords/docs/50-全面代码分析与演进方案-2026-06-24.md) |

---

*本 Code Wiki 由代码分析自动生成，最后更新于 2026-06-24*
