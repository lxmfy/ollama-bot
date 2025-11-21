.PHONY: help install run lint format clean docker-build docker-run docker-pull

help:
	@echo "Available targets:"
	@echo "  make install      - Install dependencies using poetry"
	@echo "  make run          - Run the bot using poetry"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make clean        - Clean up cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make docker-pull  - Pull latest Docker image"

install:
	poetry install

run:
	poetry run lxmfy-ollama-bot

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true

docker-build:
	docker build -t ghcr.io/lxmfy/ollama-bot:latest .

docker-run:
	docker run -d \
		--name ollama-bot \
		--restart unless-stopped \
		--network host \
		-v $(PWD)/.env:/app/.env \
		ghcr.io/lxmfy/ollama-bot:latest

docker-pull:
	docker pull ghcr.io/lxmfy/ollama-bot:latest

