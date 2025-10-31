.PHONY: help build up down restart logs clean test health

# 默认目标
help:
	@echo "视频转文字系统 - 可用命令:"
	@echo ""
	@echo "  make build      - 构建Docker镜像"
	@echo "  make up         - 启动所有服务"
	@echo "  make down       - 停止所有服务"
	@echo "  make restart    - 重启所有服务"
	@echo "  make logs       - 查看日志"
	@echo "  make clean      - 清理容器和数据"
	@echo "  make health     - 健康检查"
	@echo "  make shell-web  - 进入web容器shell"
	@echo "  make shell-worker - 进入worker容器shell"
	@echo ""

# 构建镜像
build:
	@echo "构建Docker镜像..."
	docker-compose build

# 启动服务
up:
	@echo "启动所有服务..."
	docker-compose up -d
	@echo "服务已启动!"
	@echo "Web界面: http://localhost:8000"
	@echo "API文档: http://localhost:8000/docs"
	@echo "监控界面: http://localhost:5555"

# 停止服务
down:
	@echo "停止所有服务..."
	docker-compose down

# 重启服务
restart:
	@echo "重启所有服务..."
	docker-compose restart

# 查看日志
logs:
	docker-compose logs -f

# 查看特定服务日志
logs-web:
	docker-compose logs -f web

logs-worker:
	docker-compose logs -f celery_worker

logs-redis:
	docker-compose logs -f redis

# 清理所有容器和数据
clean:
	@echo "警告: 这将删除所有容器和数据卷!"
	@read -p "确认删除? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose down -v; \
		echo "清理完成!"; \
	else \
		echo "取消操作"; \
	fi

# 健康检查
health:
	@echo "执行健康检查..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "服务未响应"

# 进入web容器shell
shell-web:
	docker-compose exec web /bin/bash

# 进入worker容器shell
shell-worker:
	docker-compose exec celery_worker /bin/bash

# 进入redis容器shell
shell-redis:
	docker-compose exec redis redis-cli

# 查看服务状态
status:
	docker-compose ps

# 完整安装(首次部署)
install: build up
	@echo "等待服务启动..."
	@sleep 10
	@make health
	@echo ""
	@echo "安装完成! 系统已就绪"
	@echo "Web界面: http://localhost:8000"
	@echo "API文档: http://localhost:8000/docs"

# 清理Redis缓存
flush-redis:
	docker-compose exec redis redis-cli FLUSHDB
	@echo "Redis缓存已清理"

# 开发模式(热重载)
dev:
	docker-compose up

# 生产模式
prod: up
	@echo "生产模式已启动"
