.PHONY: help build up down restart logs ps clean clean-all backup restore health test

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Sentiment Analyzer v2 - Docker Management$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Build Commands
# ============================================================================

build: ## Build all Docker images
	@echo "$(BLUE)Building all Docker images...$(NC)"
	docker compose build --parallel

build-no-cache: ## Build all images without cache
	@echo "$(BLUE)Building all images without cache...$(NC)"
	docker compose build --no-cache --parallel

build-service: ## Build specific service (usage: make build-service SERVICE=crawler-service)
	@echo "$(BLUE)Building $(SERVICE)...$(NC)"
	docker compose build $(SERVICE)

pull: ## Pull latest base images
	@echo "$(BLUE)Pulling latest base images...$(NC)"
	docker compose pull

# ============================================================================
# Deployment Commands
# ============================================================================

up: ## Start all services
	@echo "$(GREEN)Starting all services...$(NC)"
	docker compose up -d
	@echo "$(GREEN)All services started. Run 'make ps' to check status.$(NC)"

up-infra: ## Start only infrastructure services
	@echo "$(GREEN)Starting infrastructure services...$(NC)"
	docker compose up -d redis qdrant neo4j mlflow-postgres mlflow prometheus grafana jaeger loki
	@echo "$(GREEN)Infrastructure services started.$(NC)"

up-services: ## Start only microservices (requires infrastructure)
	@echo "$(GREEN)Starting microservices...$(NC)"
	docker compose up -d crawler-service ingest-validator-service canonicalizer-normalizer-service \
		ner-entity-linking-service embedding-service clustering-semantic-grouping-service \
		feature-engineering-service labeler-ground-truth-ingest-service trainer-model-registry-service \
		neo4j-loader-graph-service predictor-online-inference-service api-analytics-service
	@echo "$(GREEN)Microservices started.$(NC)"

up-staged: ## Start services in stages (recommended for first deployment)
	@echo "$(GREEN)Starting services in stages...$(NC)"
	@echo "$(BLUE)Stage 1: Infrastructure...$(NC)"
	docker compose up -d redis qdrant neo4j mlflow-postgres mlflow prometheus grafana jaeger loki
	@echo "$(YELLOW)Waiting 30 seconds for infrastructure to be ready...$(NC)"
	@sleep 30
	@echo "$(BLUE)Stage 2: Core services...$(NC)"
	docker compose up -d crawler-service ingest-validator-service canonicalizer-normalizer-service
	@sleep 10
	@echo "$(BLUE)Stage 3: Processing services...$(NC)"
	docker compose up -d ner-entity-linking-service embedding-service clustering-semantic-grouping-service
	@sleep 10
	@echo "$(BLUE)Stage 4: ML services...$(NC)"
	docker compose up -d feature-engineering-service labeler-ground-truth-ingest-service trainer-model-registry-service
	@sleep 10
	@echo "$(BLUE)Stage 5: API services...$(NC)"
	docker compose up -d neo4j-loader-graph-service predictor-online-inference-service api-analytics-service
	@echo "$(GREEN)All services started in stages.$(NC)"

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker compose down
	@echo "$(GREEN)All services stopped.$(NC)"

down-volumes: ## Stop all services and remove volumes (WARNING: deletes data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "$(GREEN)All services and volumes removed.$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(NC)"
	docker compose restart
	@echo "$(GREEN)All services restarted.$(NC)"

restart-service: ## Restart specific service (usage: make restart-service SERVICE=crawler-service)
	@echo "$(YELLOW)Restarting $(SERVICE)...$(NC)"
	docker compose restart $(SERVICE)
	@echo "$(GREEN)$(SERVICE) restarted.$(NC)"

# ============================================================================
# Monitoring Commands
# ============================================================================

logs: ## Show logs for all services
	docker compose logs -f

logs-service: ## Show logs for specific service (usage: make logs-service SERVICE=crawler-service)
	docker compose logs -f $(SERVICE)

ps: ## Show status of all services
	@docker compose ps

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

stats: ## Show resource usage statistics
	@docker stats --no-stream

top: ## Show running processes in containers
	@docker compose top

# ============================================================================
# Development Commands
# ============================================================================

shell: ## Open shell in service container (usage: make shell SERVICE=crawler-service)
	@docker compose exec $(SERVICE) /bin/bash

shell-root: ## Open root shell in service container (usage: make shell-root SERVICE=crawler-service)
	@docker compose exec -u root $(SERVICE) /bin/bash

exec: ## Execute command in service (usage: make exec SERVICE=crawler-service CMD="python --version")
	@docker compose exec $(SERVICE) $(CMD)

# ============================================================================
# Testing Commands
# ============================================================================

test: ## Run tests for all services
	@echo "$(BLUE)Running tests...$(NC)"
	@for service in crawler-service ingest-validator-service canonicalizer-normalizer-service \
		ner-entity-linking-service embedding-service clustering-semantic-grouping-service \
		feature-engineering-service labeler-ground-truth-ingest-service trainer-model-registry-service \
		neo4j-loader-graph-service predictor-online-inference-service api-analytics-service; do \
		echo "$(YELLOW)Testing $$service...$(NC)"; \
		docker compose exec $$service pytest tests/ || true; \
	done

test-service: ## Run tests for specific service (usage: make test-service SERVICE=crawler-service)
	@echo "$(BLUE)Running tests for $(SERVICE)...$(NC)"
	docker compose exec $(SERVICE) pytest tests/ -v

lint: ## Run linting for all services
	@echo "$(BLUE)Running linting...$(NC)"
	@for service in crawler-service ingest-validator-service canonicalizer-normalizer-service \
		ner-entity-linking-service embedding-service clustering-semantic-grouping-service \
		feature-engineering-service labeler-ground-truth-ingest-service trainer-model-registry-service \
		neo4j-loader-graph-service predictor-online-inference-service api-analytics-service; do \
		echo "$(YELLOW)Linting $$service...$(NC)"; \
		docker compose exec $$service ruff check . || true; \
	done

# ============================================================================
# Maintenance Commands
# ============================================================================

backup: ## Backup all volumes
	@echo "$(BLUE)Creating backups...$(NC)"
	@mkdir -p backups
	@echo "$(YELLOW)Backing up Redis...$(NC)"
	@docker run --rm -v sentiment-analyzer-v2_redis_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/redis_backup_$$(date +%Y%m%d_%H%M%S).tar.gz /data
	@echo "$(YELLOW)Backing up Qdrant...$(NC)"
	@docker run --rm -v sentiment-analyzer-v2_qdrant_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/qdrant_backup_$$(date +%Y%m%d_%H%M%S).tar.gz /data
	@echo "$(YELLOW)Backing up Neo4j...$(NC)"
	@docker run --rm -v sentiment-analyzer-v2_neo4j_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/neo4j_backup_$$(date +%Y%m%d_%H%M%S).tar.gz /data
	@echo "$(YELLOW)Backing up MLflow...$(NC)"
	@docker run --rm -v sentiment-analyzer-v2_mlflow_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/mlflow_backup_$$(date +%Y%m%d_%H%M%S).tar.gz /data
	@echo "$(GREEN)Backups completed in ./backups/$(NC)"

clean: ## Remove stopped containers and dangling images
	@echo "$(YELLOW)Cleaning up...$(NC)"
	docker compose down --remove-orphans
	docker image prune -f
	@echo "$(GREEN)Cleanup completed.$(NC)"

clean-all: ## Remove all containers, images, and volumes (WARNING: deletes everything)
	@echo "$(RED)WARNING: This will delete all containers, images, and volumes!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v --rmi all; \
		docker system prune -af --volumes; \
		echo "$(GREEN)All Docker resources cleaned.$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

# ============================================================================
# Utility Commands
# ============================================================================

env: ## Show environment variables
	@docker compose config

validate: ## Validate docker-compose.yml
	@echo "$(BLUE)Validating docker-compose.yml...$(NC)"
	@docker compose config --quiet && echo "$(GREEN)Configuration is valid.$(NC)" || echo "$(RED)Configuration has errors.$(NC)"

update: ## Update all services to latest versions
	@echo "$(BLUE)Updating services...$(NC)"
	docker compose pull
	docker compose build --pull
	docker compose up -d
	@echo "$(GREEN)Services updated.$(NC)"

# ============================================================================
# Quick Access Commands
# ============================================================================

grafana: ## Open Grafana in browser
	@echo "$(BLUE)Opening Grafana...$(NC)"
	@echo "URL: http://localhost:3000"
	@echo "Username: admin"
	@echo "Password: admin_password_2024"

prometheus: ## Open Prometheus in browser
	@echo "$(BLUE)Opening Prometheus...$(NC)"
	@echo "URL: http://localhost:9090"

jaeger: ## Open Jaeger in browser
	@echo "$(BLUE)Opening Jaeger...$(NC)"
	@echo "URL: http://localhost:16686"

neo4j: ## Open Neo4j browser
	@echo "$(BLUE)Opening Neo4j Browser...$(NC)"
	@echo "URL: http://localhost:7474"
	@echo "Username: neo4j"
	@echo "Password: sentiment_password_2024"

mlflow: ## Open MLflow UI
	@echo "$(BLUE)Opening MLflow...$(NC)"
	@echo "URL: http://localhost:5000"

api: ## Open API documentation
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@echo "URL: http://localhost:8011/docs"

# ============================================================================
# Installation Commands
# ============================================================================

install-deps: ## Install required dependencies (Docker, Docker Compose)
	@echo "$(BLUE)Checking dependencies...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker is not installed. Please install Docker first.$(NC)"; exit 1; }
	@command -v docker compose >/dev/null 2>&1 || { echo "$(RED)Docker Compose is not installed. Please install Docker Compose first.$(NC)"; exit 1; }
	@echo "$(GREEN)All dependencies are installed.$(NC)"

setup: ## Initial setup (create .env, directories)
	@echo "$(BLUE)Setting up environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.docker .env; \
		echo "$(GREEN).env file created. Please update with your credentials.$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists.$(NC)"; \
	fi
	@mkdir -p backups monitoring/grafana/dashboards monitoring/grafana/datasources
	@echo "$(GREEN)Setup completed.$(NC)"

init: setup install-deps ## Initialize project (setup + install dependencies)
	@echo "$(GREEN)Project initialized. Run 'make build' to build images.$(NC)"

