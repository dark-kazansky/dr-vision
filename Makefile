# Dr-Vision Makefile
# Development commands for the monolith architecture.

.PHONY: help up down logs ps build lint test health dev

COMPOSE = docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Infrastructure ───────────────────────────────────────────────────────────

up: ## Start infrastructure (postgres, minio)
	$(COMPOSE) up -d postgres minio

down: ## Stop all containers
	$(COMPOSE) down

ps: ## Show running containers
	$(COMPOSE) ps

logs: ## Follow logs from all containers
	$(COMPOSE) logs -f

build: ## Build backend Docker image
	$(COMPOSE) build backend

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

# ─── Deployment ───────────────────────────────────────────────────────────────

pack: ## Create deployment tarball
	@chmod +x pack_deploy.sh && ./pack_deploy.sh

deploy: ## Package and deploy to remote server
	@chmod +x auto_deploy.sh && ./auto_deploy.sh
