.PHONY: help install install-dev test lint format clean docker docker-gpu docker-compose k8s helm

help:
	@echo "Embedding Service - Available Commands"
	@echo "========================================"
	@echo "install              Install production dependencies"
	@echo "install-dev          Install development dependencies"
	@echo "test                 Run unit tests"
	@echo "test-cov             Run tests with coverage"
	@echo "lint                 Run linters (black, flake8, mypy)"
	@echo "format               Format code with black"
	@echo "clean                Clean build artifacts"
	@echo "docker               Build CPU Docker image"
	@echo "docker-gpu           Build GPU Docker image"
	@echo "docker-compose       Start services with Docker Compose"
	@echo "k8s                  Deploy to Kubernetes"
	@echo "helm                 Deploy with Helm"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8 mypy

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	black --check src/ tests/
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf build/ dist/ *.egg-info/

docker:
	docker build -t embedding-service:latest .

docker-gpu:
	docker build -f Dockerfile.gpu -t embedding-service:gpu .

docker-compose:
	docker-compose up -d

docker-compose-down:
	docker-compose down

k8s:
	kubectl apply -f k8s/

k8s-delete:
	kubectl delete -f k8s/

helm:
	helm install embedding-service helm/

helm-upgrade:
	helm upgrade embedding-service helm/

helm-delete:
	helm delete embedding-service

logs:
	kubectl logs -f deployment/embedding-service -n sentiment-analyzer

shell:
	python -i -c "from src.config import config; from src.service import EmbeddingService"

.DEFAULT_GOAL := help

