.PHONY: help build up down logs test clean restart shell migrate

# Default target
.DEFAULT_GOAL := help

# Colors for output
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help: ## Show this help message
	@echo '${GREEN}Available commands:${RESET}'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  ${YELLOW}%-20s${RESET} %s\n", $$1, $$2}'

## Development Commands

build: ## Build Docker images
	docker-compose build

up: ## Start all services in development mode
	docker-compose up -d
	@echo "${GREEN}Services started! ${RESET}"
	@echo "Webhook Service: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Adminer: http://localhost:8080"
	@echo "RabbitMQ Management: http://localhost:15672"

down: ## Stop all services
	docker-compose down

restart: down up ## Restart all services

logs: ## View logs from all services
	docker-compose logs -f

logs-app: ## View logs from webhook service only
	docker-compose logs -f webhook-service

ps: ## List running containers
	docker-compose ps

shell: ## Open shell in webhook service container
	docker-compose exec webhook-service sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U webhook -d webhook

## Database Commands

migrate: ## Run database migrations
	docker-compose exec webhook-service alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	docker-compose exec webhook-service alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	docker-compose exec webhook-service alembic downgrade -1

migrate-history: ## Show migration history
	docker-compose exec webhook-service alembic history

db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose exec webhook-service alembic downgrade base
	docker-compose exec webhook-service alembic upgrade head

## Testing Commands

test: ## Run tests in Docker
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down

test-watch: ## Run tests with file watching
	docker-compose exec webhook-service pytest-watch tests/

lint: ## Run linter
	docker-compose exec webhook-service ruff check src/ tests/

lint-fix: ## Run linter with auto-fix
	docker-compose exec webhook-service ruff check src/ tests/ --fix

format: ## Format code
	docker-compose exec webhook-service ruff format src/ tests/

coverage: ## Generate test coverage report
	docker-compose exec webhook-service pytest --cov=src --cov-report=html
	@echo "${GREEN}Coverage report: htmlcov/index.html${RESET}"

## Production Commands

prod-build: ## Build production images
	docker-compose -f docker-compose.prod.yml build

prod-up: ## Start production services
	docker-compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker-compose -f docker-compose.prod.yml down

prod-logs: ## View production logs
	docker-compose -f docker-compose.prod.yml logs -f

## Cleanup Commands

clean: ## Remove all containers, volumes, and images
	docker-compose down -v --remove-orphans
	docker-compose -f docker-compose.test.yml down -v --remove-orphans

clean-all: clean ## Remove all including Docker images
	docker system prune -af --volumes

## Utility Commands

health: ## Check health of all services
	@echo "${GREEN}Checking service health...${RESET}"
	@curl -s http://localhost:8000/api/v1/health | jq . || echo "Webhook service not responding"
	@docker-compose exec postgres pg_isready -U webhook || echo "PostgreSQL not ready"
	@docker-compose exec rabbitmq rabbitmq-diagnostics ping || echo "RabbitMQ not ready"

stats: ## Show container resource usage
	docker stats --no-stream

backup-db: ## Backup PostgreSQL database
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U webhook webhook > backups/webhook_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}Database backed up to backups/${RESET}"

restore-db: ## Restore PostgreSQL database (usage: make restore-db FILE=backup.sql)
	docker-compose exec -T postgres psql -U webhook webhook < $(FILE)
