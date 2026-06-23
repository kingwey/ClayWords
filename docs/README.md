# ClayWords / 陶语 文档索引

本目录收录 ClayWords(陶语)项目的全部存档文档。已于 2026-06-23 完成清理与重命名:
- 合并 11 份 Phase 完成报告为 [CHANGELOG.md](CHANGELOG.md)
- 删除 6 份被覆盖的总结/任务清单旧版本
- 全部文档统一为 kebab-case 英文小写命名(中文标题保留在文档 H1)

## 一、项目管理

| 文档 | 用途 |
|---|---|
| [next-steps-2026-06-23.md](next-steps-2026-06-23.md) | **当前推进路线**(基于 06-23 实测,修正旧规划) — 优先看这份 |
| [project-analysis.md](project-analysis.md) | 06-22 完成度基线快照(部分判断已被 next-steps 修正) |
| [roadmap-v2.md](roadmap-v2.md) | 任务粒度参考清单(优先级以 next-steps 为准) |
| [mvp-sprint-plan.md](mvp-sprint-plan.md) | MVP 上线路径(同上) |
| [worklog-2026-06-22.md](worklog-2026-06-22.md) | 14h 开发过程的详细工作日志 |
| [CHANGELOG.md](CHANGELOG.md) | Phase Q1~Q10 + P0 完成记录(由 11 份 Phase 报告合并) |

## 二、技术方案与代码报告

| 文档 | 用途 |
|---|---|
| [taoyu-tech-design.md](taoyu-tech-design.md) | 完整技术方案 v1.3,15 章节,架构总览 |
| [code-review-2026-06-22.md](code-review-2026-06-22.md) | 7 个真实 Bug 修复 + 6 项安全/性能优化 + 4 个附录 |
| [claywords-final-report.md](claywords-final-report.md) | 技术债推进 + Hunyuan3D 接入的最终交付摘要 |
| [order-idempotency.md](order-idempotency.md) | `Order.idempotency_key` 与 `IdempotencyKey` 表的职责划分 |
| [craft-vector-similarity.md](craft-vector-similarity.md) | 派单工艺匹配从 substring 改 pgvector 余弦相似度的方案 |
| [hunyuan3d-integration-plan.md](hunyuan3d-integration-plan.md) | 腾讯云混元 3D 接入设计 |
| [hunyuan3d-deployment-guide.md](hunyuan3d-deployment-guide.md) | Hunyuan3D 部署与环境配置 |

## 三、运维手册

| 文档 | 用途 |
|---|---|
| [production-deploy-checklist.md](production-deploy-checklist.md) | 上线前 P0 检查项与部署流程 |
| [backup-recovery-runbook.md](backup-recovery-runbook.md) | RTO ≤ 30min 故障恢复手册 |
| [pg-ha-config.md](pg-ha-config.md) | Postgres WAL 归档 + 流式复制配置 |
| [business-metrics-dashboard.md](business-metrics-dashboard.md) | Grafana 面板与告警规则 |

## 四、安全与合规

| 文档 | 用途 |
|---|---|
| [security-owasp-top10.md](security-owasp-top10.md) | OWASP Top 10 自评(基线 74/100) |
| [license-compliance.md](license-compliance.md) | 第三方依赖开源许可证合规清单 |

## 五、竞赛交付物

| 文档 | 用途 |
|---|---|
| [taoyu-pitch-doc.md](taoyu-pitch-doc.md) | 报名帖 Markdown 源 |
| [taoyu-pitch-doc.html](taoyu-pitch-doc.html) | 报名帖 HTML 单文件版 |
| [taoyu-demo.md](taoyu-demo.md) | 初赛演示版本(含评审黄金路径) |
| [claywords-pitch.html](claywords-pitch.html) | 产品 Pitch 交互页 |
| [videos/claywords-demo.mp4](videos/claywords-demo.mp4) | 演示视频 |

## 六、命名规范

新增文档请遵守:
- **全小写 kebab-case**:`some-topic-name.md`
- **专有名词不分隔**:`hunyuan3d`、`claywords` 整体作为一个词,不写作 `hun-yuan-3d`
- **日期后缀**:`-YYYY-MM-DD` 格式,如 `worklog-2026-06-22.md`
- **版本后缀**:`-vN` 格式(去掉小数点 .0),如 `roadmap-v2.md`
- **中文标题**:保留在文档第一行 `# 标题` 内,文件名仅承担索引职能
- **保留大写**:`README.md`、`CHANGELOG.md`(社区惯例)

## 七、清理记录(2026-06-23)

**合并**:`Phase-Q1~Q10-完成报告.md` + `P0-生产部署配置完成报告.md` → [CHANGELOG.md](CHANGELOG.md)

**删除**(被新版本覆盖):
- 三份重复总结 → [worklog-2026-06-22.md](worklog-2026-06-22.md)
- 旧版任务清单 → [roadmap-v2.md](roadmap-v2.md)
- `陶语-初赛演示技术方案.md` → [taoyu-tech-design.md](taoyu-tech-design.md) 已完整覆盖

**重命名**:全部 18 份中文/混排文件名 → kebab-case 英文小写
