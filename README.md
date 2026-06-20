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
# 0. 克隆仓库
git clone https://codeup.aliyun.com/68da5e06ab336f9c842acddc/AI/ClayWords.git
cd ClayWords

# 1. 安装依赖
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2. seed 演示数据（3 个账号 + 4 家工作室 + 31 个模板 + 3 条演示订单）
make db.seed && python scripts/seed_demo_orders.py

# 3. 启动服务
cd backend && uvicorn app.main:app --port 8000   # 后端
cd frontend && npm run dev                          # 前端 :5173
```

**演示账号**（任选其一，验证码任意 6 位）：

- `13800000001` 普通用户
- `13800000002` 工作室主
- `13800000003` 平台管理员

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

- [初赛 Demo 提交](./docs/陶语-初赛demo.md)
- [技术方案](./docs/陶语-技术方案.md)
- [初赛演示技术方案](./docs/陶语-初赛演示技术方案.md)
- [开发任务清单](./docs/陶语-开发任务清单.md)
- [报名材料](./docs/陶语-报名材料.md)

## 仓库

[https://codeup.aliyun.com/68da5e06ab336f9c842acddc/AI/ClayWords.git](https://codeup.aliyun.com/68da5e06ab336f9c842acddc/AI/ClayWords.git)
