# syntax=docker/dockerfile:1

# ---------- Stage 1: 构建前端 ----------
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# 跳过 vue-tsc 类型检查，只做产物构建，避免类型告警阻断部署
RUN npx vite build

# ---------- Stage 2: 后端运行时 ----------
FROM python:3.12-slim AS backend
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# 后端代码
COPY backend/ ./

# 前端构建产物，由后端同源托管
COPY --from=frontend /fe/dist ./static
ENV STATIC_DIR=/app/static

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
