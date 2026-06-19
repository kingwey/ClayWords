# 陶语 (ClayWords)

AI 创造力大赛 · 初赛项目 · 对话式陶瓷定制 Web 应用

## 项目简介

陶语是一个对话式陶瓷定制 Web 应用，用户通过自然语言描述想要的陶瓷摆件，AI 自动生成可烧制的 3D 造型方案，并直连景德镇/德化等产区的陶瓷工作室完成烧制配送。

## 技术栈

- **前端**: Vue 3 + Element Plus + Three.js
- **后端**: FastAPI + PostgreSQL + Redis + MinIO
- **GPU Worker**: PyTorch + trimesh + Open3D
- **部署**: Docker + Compose

## 快速启动

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 启动基础设施
make up

# 运行后端
cd backend && uvicorn app.main:app --reload

# 运行前端
cd frontend && npm install && npm run dev
```

## 目录结构

```
frontend/       # Vue 3 前端项目
backend/        # FastAPI 后端项目
worker/         # GPU Worker (3D 生成)
infra/          # Docker Compose 配置
scripts/        # 工具脚本
docs/           # 技术文档
```

## 相关文档

- [技术方案](./docs/陶语-技术方案.md)
- [初赛演示技术方案](./docs/陶语-初赛演示技术方案.md)
- [开发任务清单](./docs/陶语-开发任务清单.md)
