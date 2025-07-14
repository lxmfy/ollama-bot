ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine

LABEL org.opencontainers.image.source="https://github.com/lxmfy/ollama-bot"
LABEL org.opencontainers.image.description="An LXMF bot for interacting with Ollama LLM Models"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="LXMFy"

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY lxmfy_ollama_bot/ lxmfy_ollama_bot/

ENTRYPOINT ["poetry", "run", "python", "lxmfy_ollama_bot/bot.py"]
