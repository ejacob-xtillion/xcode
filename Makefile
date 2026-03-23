.PHONY: help build up down restart logs clean test shell start

help:
	@echo "xCode Docker Commands"
	@echo ""
	@echo "  make start     - Smart startup (recommended)"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make clean     - Stop services and remove volumes"
	@echo "  make test      - Run tests in container"
	@echo "  make shell     - Open shell in xcode container"
	@echo "  make xcode     - Run xCode interactively"
	@echo ""

start:
	@./docker-start.sh

build:
	docker-compose build

up:
	docker-compose up -d postgres neo4j xcode-agent
	@echo "⏳ Waiting for services to be healthy (this may take 90s)..."
	@sleep 15
	@echo "✓ Backend services starting! Run 'make xcode' to start interactive mode"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

test:
	docker-compose run --rm xcode python -m pytest tests/ -v

shell:
	docker-compose run --rm xcode /bin/bash

xcode:
	docker-compose run --rm xcode xcode -i

# Quick commands
agent-logs:
	docker-compose logs -f xcode-agent

neo4j-logs:
	docker-compose logs -f neo4j

health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "xCode Agent: Not ready"
	@curl -s http://localhost:7474 > /dev/null && echo "Neo4j: Ready" || echo "Neo4j: Not ready"
