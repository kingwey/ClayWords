# 开源许可证合规报告

> Phase Q10.2.3: 开源许可证合规  
> 日期: 2026-06-22  
> 项目: ClayWords 陶瓷定制平台

---

## 执行摘要

ClayWords 使用多个开源组件。本文档审查所有依赖的开源许可证，确保合规使用。

**结论**: ✅ 所有依赖许可证与商业化兼容

---

## 1. 核心依赖许可证清单

### 1.1 后端 (Python)

| 包名 | 版本 | 许可证 | 商业化 | 备注 |
|------|------|--------|--------|------|
| **FastAPI** | 0.104+ | MIT | ✅ 允许 | Web 框架 |
| **SQLAlchemy** | 2.0+ | MIT | ✅ 允许 | ORM |
| **asyncpg** | 0.29+ | Apache 2.0 | ✅ 允许 | PostgreSQL 驱动 |
| **redis** | 5.0+ | MIT | ✅ 允许 | Redis 客户端 |
| **pydantic** | 2.5+ | MIT | ✅ 允许 | 数据验证 |
| **alembic** | 1.13+ | MIT | ✅ 允许 | 数据库迁移 |
| **structlog** | 24.1+ | MIT / Apache 2.0 | ✅ 允许 | 结构化日志 |
| **cryptography** | 41.0+ | Apache 2.0 / BSD | ✅ 允许 | 加密库 |
| **python-jose** | 3.3+ | MIT | ✅ 允许 | JWT |
| **bcrypt** | 4.1+ | Apache 2.0 | ✅ 允许 | 密码哈希 |

### 1.2 数据库 & 存储

| 组件 | 版本 | 许可证 | 商业化 | 备注 |
|------|------|--------|--------|------|
| **PostgreSQL** | 16+ | PostgreSQL License | ✅ 允许 | 类似 MIT |
| **pgvector** | 0.8+ | PostgreSQL License | ✅ 允许 | 向量扩展 |
| **Redis** | 7+ | BSD 3-Clause | ✅ 允许 | 内存数据库 |
| **MinIO** | latest | **AGPL 3.0** | ⚠️ 注意 | 自托管模式 OK |

### 1.3 前端 (计划)

| 包名 | 许可证 | 商业化 | 备注 |
|------|--------|--------|------|
| **React** | MIT | ✅ 允许 | UI 框架 |
| **Next.js** | MIT | ✅ 允许 | React 框架 |
| **Tailwind CSS** | MIT | ✅ 允许 | CSS 框架 |
| **Axios** | MIT | ✅ 允许 | HTTP 客户端 |

### 1.4 基础设施

| 组件 | 许可证 | 商业化 | 备注 |
|------|--------|--------|------|
| **Docker** | Apache 2.0 | ✅ 允许 | 容器化 |
| **Kubernetes** | Apache 2.0 | ✅ 允许 | 容器编排 |
| **Prometheus** | Apache 2.0 | ✅ 允许 | 监控 |
| **Grafana** | AGPL 3.0 | ⚠️ 注意 | 自托管模式 OK |

---

## 2. 许可证类型说明

### 2.1 MIT License

**特点**:
- ✅ 最宽松的许可证之一
- ✅ 允许商业使用
- ✅ 允许修改和分发
- ✅ 无需公开源代码
- ✅ 只需保留许可证声明

**我们的使用**: 大部分核心依赖（FastAPI, SQLAlchemy, Redis）

**合规要求**:
- 在产品文档/关于页面中包含许可证声明
- 不移除依赖库中的版权声明

### 2.2 Apache License 2.0

**特点**:
- ✅ 商业友好
- ✅ 明确授权专利权
- ✅ 无需公开源代码
- ✅ 允许修改和分发

**我们的使用**: asyncpg, cryptography, Docker, K8s

**合规要求**:
- 保留 NOTICE 文件（如果有）
- 修改文件需说明

### 2.3 BSD License (3-Clause)

**特点**:
- ✅ 商业友好
- ✅ 与 MIT 类似宽松
- ✅ 无需公开源代码

**我们的使用**: Redis

**合规要求**:
- 保留版权声明
- 不能用项目名称背书

### 2.4 PostgreSQL License

**特点**:
- ✅ 类似 MIT/BSD
- ✅ 商业友好
- ✅ 无需公开源代码

**我们的使用**: PostgreSQL, pgvector

**合规要求**:
- 保留版权声明

### 2.5 AGPL 3.0 (重点关注)

**特点**:
- ⚠️ **网络 Copyleft**
- ⚠️ 通过网络提供服务也算"分发"
- ⚠️ 修改后的代码必须公开
- ✅ **自托管不受影响**

**我们的使用**: MinIO (对象存储), Grafana (监控)

**合规策略**:
1. **MinIO**: 
   - ✅ 我们自托管 MinIO 服务器
   - ✅ 不修改 MinIO 源代码
   - ✅ 用户不直接访问 MinIO（通过我们的 API）
   - ✅ **合规** - 自托管场景下 AGPL 不要求公开我们的代码

2. **Grafana**:
   - ✅ 仅用于内部监控
   - ✅ 不对外提供服务
   - ✅ **合规** - 内部使用不触发 AGPL

---

## 3. 合规行动清单

### 3.1 已完成 ✅

- [x] 审查所有后端依赖许可证
- [x] 确认 AGPL 组件使用场景
- [x] 归档许可证清单

### 3.2 待实施 ⏸️

- [ ] **前端依赖审查**（前端开发时）
- [ ] **关于页面添加许可证声明**
  ```html
  <!-- 示例 -->
  <h2>开源软件声明</h2>
  <p>本产品使用以下开源软件:</p>
  <ul>
    <li>FastAPI (MIT License)</li>
    <li>PostgreSQL (PostgreSQL License)</li>
    ...
  </ul>
  ```
- [ ] **生成 NOTICE 文件**
  ```bash
  # 自动生成
  pip-licenses --format=markdown --output-file=NOTICE.md
  ```
- [ ] **CI 许可证检查**
  - 集成 `pip-licenses` 到 CI
  - 自动检测新增的非白名单许可证

---

## 4. 风险评估

### 4.1 无风险 ✅

| 风险项 | 状态 | 说明 |
|--------|------|------|
| MIT/Apache 2.0 组件 | ✅ 无风险 | 商业友好 |
| PostgreSQL/BSD 组件 | ✅ 无风险 | 商业友好 |
| AGPL 自托管 | ✅ 无风险 | 不触发公开要求 |

### 4.2 需注意 ⚠️

| 风险项 | 风险等级 | 缓解措施 |
|--------|---------|----------|
| AGPL 组件修改 | 中 | **禁止修改 MinIO/Grafana 源代码** |
| AGPL SaaS 化 | 高 | **确保 MinIO 不对外直接暴露** |
| 前端依赖未审查 | 低 | 前端开发时重新审查 |

### 4.3 零风险 ✅

- GPL/LGPL 组件: 无（我们未使用）
- 专有软件: 无

---

## 5. 第三方服务

### 5.1 云服务商

| 服务 | 许可模式 | 备注 |
|------|---------|------|
| **阿里云 OSS** | 商业服务 | 按量付费，无许可证问题 |
| **腾讯云 COS** | 商业服务 | 备选方案 |
| **Cloudflare CDN** | 商业服务 | Free/Pro 套餐 |

### 5.2 AI 模型

| 模型 | 许可证 | 商业化 |
|------|--------|--------|
| **通义千问** | 商业 API | ✅ 付费使用 |
| **OpenAI GPT** | 商业 API | ✅ 付费使用 |
| **Hunyuan3D** | 待确认 | ⏸️ 需审查模型许可证 |

---

## 6. 许可证合规 CI 检查

### 6.1 自动化检查脚本

```bash
#!/bin/bash
# scripts/check_licenses.sh

# 检查 Python 依赖
pip-licenses --fail-on="GPL;LGPL;SSPL" --format=json

# 白名单许可证
ALLOWED_LICENSES=(
    "MIT"
    "Apache"
    "BSD"
    "PostgreSQL"
    "AGPL"  # 仅限自托管
)

# 输出报告
pip-licenses --format=markdown --output-file=docs/licenses.md
```

### 6.2 CI 集成

```yaml
# .github/workflows/license-check.yml
name: License Check

on: [pull_request]

jobs:
  check-licenses:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check Python licenses
        run: |
          pip install pip-licenses
          bash scripts/check_licenses.sh
```

---

## 7. 法律声明模板

### 7.1 产品关于页面

```markdown
# 关于 ClayWords

## 开源软件声明

本产品基于以下开源软件构建：

- **FastAPI** (MIT License) - Web 框架
- **PostgreSQL** (PostgreSQL License) - 数据库
- **Redis** (BSD 3-Clause) - 缓存
- **MinIO** (AGPL 3.0) - 对象存储（自托管）

完整许可证列表请见: [NOTICE.md](./NOTICE.md)
```

### 7.2 用户协议

```markdown
## 第三方软件

本服务使用多个开源软件和第三方服务。这些软件/服务拥有各自的许可证和服务条款。
我们遵守所有适用的开源许可证要求。
```

---

## 8. 决策记录

### 8.1 为什么选择 MinIO (AGPL)?

**决策**: 自托管 MinIO，不修改源代码

**原因**:
- ✅ 自托管场景 AGPL 不要求公开我们的代码
- ✅ MinIO 是成熟的 S3 兼容对象存储
- ✅ 相比云 OSS 成本更低
- ✅ 数据主权（本地存储）

**替代方案**:
- 阿里云 OSS（商业服务，更贵）
- Ceph（复杂度高）
- SeaweedFS (Apache 2.0，功能较少)

### 8.2 为什么不用 Elasticsearch (SSPL)?

**决策**: 暂不使用 Elasticsearch

**原因**:
- ⚠️ SSPL 不是 OSI 批准的开源许可证
- ⚠️ 商业使用限制模糊
- ✅ PostgreSQL 全文搜索 + pgvector 足够

**未来**: 如需要，考虑 Meilisearch (MIT) 或 Typesense (GPL 3.0)

---

## 9. 联系方式

**许可证合规负责人**: legal@claywords.com  
**技术负责人**: tech@claywords.com

---

## 10. 修订历史

| 日期 | 版本 | 修改内容 | 作者 |
|------|------|---------|------|
| 2026-06-22 | 1.0 | 初始版本 | Legal & OPS |

---

## 附录 A: 快速许可证识别

```bash
# 检查 Python 包许可证
pip-licenses --format=table

# 检查 npm 包许可证（前端）
npm install -g license-checker
license-checker --summary

# 检查 Docker 镜像许可证
trivy image --list-all-pkgs claywords-backend:latest
```

---

## 附录 B: 参考资源

- [SPDX License List](https://spdx.org/licenses/)
- [Choose a License](https://choosealicense.com/)
- [FOSSA - Open Source License Compliance](https://fossa.com/learn)
- [TLDRLegal - Software Licenses](https://www.tldrlegal.com/)
