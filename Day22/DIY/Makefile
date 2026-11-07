.PHONY: help sync generate server test-endpoint clean

help:
	@echo "Day22 DIY: Three-Layer Dashboard Design + FastAPI Demo"
	@echo ""
	@echo "Available commands:"
	@echo "  make sync           - Create/update venv and install dependencies"
	@echo "  make generate       - Generate and validate the three-layer dashboard"
	@echo "  make server         - Run FastAPI server with observability metrics"
	@echo "  make test-endpoint  - Test the /ask endpoint (requires server running in another terminal)"
	@echo "  make clean          - Remove .venv and __pycache__"

sync:
	uv sync

generate:
	uv run python scripts/generate_dashboard.py

server:
	uv run python -m app.main

test-endpoint:
	@echo "Testing /ask endpoint..."
	curl -X POST "http://localhost:8000/ask?question=What+is+AI" -v
	@echo "\n"
	@echo "Testing /health endpoint..."
	curl "http://localhost:8000/health" -v
	@echo "\n"
	@echo "Fetching metrics from /metrics..."
	curl "http://localhost:8000/metrics" | head -30

clean:
	rm -rf .venv __pycache__ app/__pycache__ scripts/__pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
