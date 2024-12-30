import os
import argparse
from dotenv import load_dotenv
from lxmfy import LXMFBot
import requests
from queue import Queue
from threading import Thread
import time
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Ollama Bot")
    parser.add_argument("--env", type=str, help="Path to env file")
    parser.add_argument(
        "--no-chat-history", action="store_true", help="Disable chat history"
    )
    parser.add_argument("--api-url", type=str, help="Ollama API URL")
    parser.add_argument("--model", type=str, help="Ollama model name")
    parser.add_argument(
        "--admins", type=str, help="Comma-separated list of admin LXMF hashes"
    )
    return parser.parse_args()


args = parse_args()

if args.env:
    load_dotenv(args.env)
else:
    load_dotenv()

OLLAMA_API_URL = args.api_url or os.getenv(
    "OLLAMA_API_URL", "http://localhost:11434"
)
MODEL = args.model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
SAVE_CHAT_HISTORY = not args.no_chat_history
LXMF_ADMINS = (
    args.admins.split(",") if args.admins else os.getenv("LXMF_ADMINS", "").split(",")
)


class OllamaAPI:
    def __init__(self, api_url, timeout=30, queue_size=10):
        self.api_url = api_url
        self.timeout = timeout
        self.request_queue = Queue(maxsize=queue_size)
        self.response_queue = {}
        self._start_worker()

    def _start_worker(self):
        """Start the worker thread to process requests"""

        def worker():
            while True:
                try:
                    request_id, endpoint, data, callback = self.request_queue.get()
                    try:
                        response = requests.post(
                            f"{self.api_url}/api/{endpoint}",
                            json=data,
                            timeout=self.timeout,
                        )
                        result = response.json()
                        callback(result)
                    except Exception as e:
                        callback({"error": str(e)})
                    finally:
                        self.request_queue.task_done()
                except Exception:
                    time.sleep(1)

        thread = Thread(target=worker, daemon=True)
        thread.start()

    def _queue_request(self, endpoint, data, callback):
        """Queue a request with a callback"""
        request_id = time.time()
        self.request_queue.put((request_id, endpoint, data, callback))
        return request_id

    def generate(self, prompt, stream=False, callback=None):
        """Queue a generate request"""
        data = {"model": MODEL, "prompt": prompt, "stream": stream}
        if callback:
            return self._queue_request("generate", data, callback)

        # Synchronous fallback
        response = requests.post(
            f"{self.api_url}/api/generate",
            json=data,
            timeout=self.timeout,
        )
        return response.json()

    def chat(self, messages, stream=False, callback=None):
        """Queue a chat request"""
        data = {"model": MODEL, "messages": messages, "stream": stream}
        if callback:
            return self._queue_request("chat", data, callback)

        response = requests.post(
            f"{self.api_url}/api/chat",
            json=data,
            timeout=self.timeout,
        )
        return response.json()


def setup_cogs():
    """Copy package cogs to config/cogs if they don't exist"""
    current_dir = Path(__file__).parent
    package_cogs = current_dir / "cogs"
    config_cogs = Path("config/cogs")

    config_cogs.mkdir(parents=True, exist_ok=True)

    for cog_file in package_cogs.glob("*.py"):
        if not cog_file.name.startswith("_"):
            dest_file = config_cogs / cog_file.name
            if not dest_file.exists():
                dest_file.write_text(cog_file.read_text())
                RNS.log(f"Copied cog {cog_file.name} to config/cogs", RNS.LOG_INFO)


def create_bot():
    setup_cogs()

    bot = LXMFBot(
        name="OllamaBot",
        announce=600,
        admins=LXMF_ADMINS,
        hot_reloading=True,
        command_prefix="",
        rate_limit=5,
        cooldown=5,
        max_warnings=3,
        warning_timeout=300,
    )

    bot.ollama = OllamaAPI(OLLAMA_API_URL, queue_size=10)
    bot.save_chat_history = SAVE_CHAT_HISTORY

    from lxmfy import load_cogs_from_directory

    load_cogs_from_directory(bot)

    return bot


def main():
    bot = create_bot()
    bot.run()


if __name__ == "__main__":
    main()
