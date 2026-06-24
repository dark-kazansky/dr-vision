# Dr-Vision Makefile
# Development commands for the monolith architecture.

.PHONY: help up down logs ps build lint test health dev migrate migrate-status migrate-history migrate-create migrate-rollback migrate-reset

COMPOSE = docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Infrastructure ───────────────────────────────────────────────────────────

up: ## Start all services (backend + frontend + infra)
	$(COMPOSE) up -d

up-infra: ## Start infrastructure only (postgres, minio)
	$(COMPOSE) up -d postgres minio

down: ## Stop all containers
	$(COMPOSE) down

ps: ## Show running containers
	$(COMPOSE) ps

logs: ## Follow logs from all containers
	$(COMPOSE) logs -f

logs-backend: ## Follow backend logs
	$(COMPOSE) logs -f backend

build: ## Build all Docker images
	$(COMPOSE) build

# ─── Development ──────────────────────────────────────────────────────────────

dev: ## Start backend + frontend for local development
	@chmod +x quick_start.sh && ./quick_start.sh

lint: ## Run backend linter (ruff)
	cd backend && ruff check .

test: ## Run backend tests
	cd backend && pytest -x --tb=short

test-frontend: ## Run frontend tests
	cd frontend && npx vitest --run

typecheck: ## Run frontend type check
	cd frontend && npx vue-tsc --noEmit

verify: ## Run full verification pipeline
	@chmod +x verify.sh && ./verify.sh

# ─── Health Checks ────────────────────────────────────────────────────────────

health: ## Check if services are responding
	@echo "Backend:";  curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Frontend:"; curl -s -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:3000 2>/dev/null || echo "  DOWN"

# ─── Database Migrations ──────────────────────────────────────────────────────

migrate: ## Apply all pending migrations (alembic upgrade head)
	cd backend && alembic upgrade head

migrate-status: ## Show current migration status
	cd backend && alembic current

migrate-history: ## Show migration history
	cd backend && alembic history

migrate-create: ## Create new migration (usage: make migrate-create MSG="add column")
	cd backend && alembic revision -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-reset: ## Rollback ALL migrations (destructive!)
	cd backend && alembic downgrade base

# ─── Deployment ───────────────────────────────────────────────────────────────

pack: ## Create deployment tarball
	@chmod +x pack_deploy.sh && ./pack_deploy.sh

deploy: ## Package and deploy to remote server
	@chmod +x auto_deploy.sh && ./auto_deploy.sh
