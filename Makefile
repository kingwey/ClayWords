.PHONY: up down logs test lint db.migrate db.seed clean

# 启动基础设施
up:
	docker compose -f infra/docker-compose.yml up -d
	@echo "Services started. Waiting for health checks..."
	@sleep 5

# 停止基础设施
down:
	docker compose -f infra/docker-compose.yml down

# 查看日志
logs:
	docker compose -f infra/docker-compose.yml logs -f

# 运行测试
test:
	cd backend && pytest tests/ -v

# 代码检查
lint:
	cd backend && ruff check app/
	cd frontend && npx eslint src/

# 数据库迁移
db.migrate:
	cd backend && alembic upgrade head

# 数据库种子
db.seed:
	python scripts/seed_studios.py
	python scripts/seed_users.py
	python scripts/seed_templates.py

# 清理
clean:
	docker compose -f infra/docker-compose.yml down -v
	rm -rf backend/__pycache__ backend/app/__pycache__
	rm -rf frontend/node_modules
