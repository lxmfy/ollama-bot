# ollama-bot

Interact with Ollama LLMs

![showcase](lxmfy-ollama-showcase.png)

> [!WARNING]  
> The bot stores chat history by default, to disable use: --no-chat-history.

## Setup

`git clone https://github.com/lxmfy/ollama-bot.git`

`cd ollama-bot`

`cp .env-example .env`

edit `.env` with your ollama api url, model, and lxmf address.

## Installation and Running

`poetry install`

`poetry run bot`

## Commands

`help` - show help.

`about` - show about.

`debug` - toggle debug mode.

`ask <prompt>` - ask the bot a question.

`chat <prompt>` - start a chat session with the bot.