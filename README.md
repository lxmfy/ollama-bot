# ollama-bot

[![DeepSource](https://app.deepsource.com/gh/lxmfy/ollama-bot.svg/?label=active+issues&show_trend=true&token=_bWeecd42tkU5NJyDztbi6DW)](https://app.deepsource.com/gh/lxmfy/ollama-bot/)
[![Build and Publish Docker Image](https://github.com/lxmfy/ollama-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/lxmfy/ollama-bot/actions/workflows/docker.yml)


Interact with Ollama LLMs using LXMFy bot framework.

![showcase](lxmfy-ollama-showcase.png)

## Setup

`git clone https://github.com/lxmfy/ollama-bot.git`

`cd ollama-bot`

`cp .env-example .env`

edit `.env` with your ollama api url, model, and lxmf address.

## Installation and Running

`pipx install git+https://github.com/lxmfy/ollama-bot.git`

`lxmfy-ollama-bot`

### Poetry 

`poetry install`

`poetry run lxmfy-ollama-bot`

## Docker

First, pull the latest image:

`docker pull ghcr.io/lxmfy/ollama-bot:latest`

Then, run the bot, mounting your `.env` file:

```bash
docker run -d \
  --name ollama-bot \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/.env:/app/.env \
  ghcr.io/lxmfy/ollama-bot:latest
```

## Commands 

Command prefix: `/`

`/help` - show help message

`/about` - show bot information

## Chat

Send any message **without** the `/` prefix to chat with the AI model.

The bot will automatically respond using the configured Ollama model.
