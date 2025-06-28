import argparse
import os
import time
from queue import Queue
from threading import Thread

import requests
from dotenv import load_dotenv
from lxmfy import LXMFBot


def parse_args():
    parser = argparse.ArgumentParser(description="Ollama Bot")
    parser.add_argument("--env", type=str, help="Path to env file")
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
MODEL = args.model or os.getenv("OLLAMA_MODEL", "gemma3n:e2b")
SAVE_CHAT_HISTORY = False
LXMF_ADMINS = (
    set(filter(None, args.admins.split(",")))
    if args.admins
    else set(filter(None, os.getenv("LXMF_ADMINS", "").split(",")))
)


class OllamaAPI:
    def __init__(self, api_url, timeout=30, queue_size=10):
        self.api_url = api_url
        self.timeout = timeout
        self.request_queue = Queue(maxsize=queue_size)
        self.response_queue = {}
        self._start_worker()
        self._test_connection()

    def _test_connection(self):
        """Test connection to Ollama API and get available models"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    print(f"✓ Connected to Ollama. {len(models)} model(s) available")
                    if not any(MODEL in m['name'] for m in models):
                        print(f"⚠ Warning: Configured model '{MODEL}' not found in available models")
                else:
                    print("⚠ Connected to Ollama but no models available")
            else:
                print(f"✗ Ollama API returned status {response.status_code}")
        except Exception as e:
            print(f"✗ Failed to connect to Ollama API: {e}")

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


def create_bot():
    bot = LXMFBot(
        name="OllamaBot",
        announce=600,
        admins=LXMF_ADMINS,
        hot_reloading=True,
        command_prefix="/",
        rate_limit=5,
        cooldown=5,
        max_warnings=3,
        warning_timeout=300,
        cogs_enabled=False,
        cogs_dir="",
    )

    bot.ollama = OllamaAPI(OLLAMA_API_URL, queue_size=10)
    bot.save_chat_history = SAVE_CHAT_HISTORY

    @bot.command(name="help")
    def help_command(ctx):
        """Show available commands"""
        help_text = """Available Commands:

=== General ===
/help - Show this help message
/about - Show bot information

=== Chat ===
Send any message without the "/" prefix to chat with the AI model.
The bot will respond using the configured Ollama model."""
        ctx.reply(help_text)

    @bot.command(name="about")
    def about_command(ctx):
        """Show bot information"""
        about_text = f"""OllamaBot v1.0.0

Connected to: {OLLAMA_API_URL}
Model: {MODEL}
Admins: {len(LXMF_ADMINS)} configured

This bot allows you to chat with AI models through Ollama.
Simply send a message without any command prefix to start chatting."""
        ctx.reply(about_text)



    @bot.events.on("message_received")
    def handle_message(event):
        """Handle all incoming messages"""
        lxmf_message = event.data.get("message")
        sender_hash = event.data.get("sender")

        if not lxmf_message or not hasattr(lxmf_message, "content") or not lxmf_message.content:
            return

        try:
            content_str = lxmf_message.content.decode('utf-8').strip()
        except UnicodeDecodeError:
            bot.send(sender_hash, "Error: Message content is not valid UTF-8.")
            return

        if bot.command_prefix and content_str.startswith(bot.command_prefix):
            return

        if not content_str:
            return



        def callback(response):
            """Handle Ollama API response"""
            if "error" in response:
                error_msg = response["error"]
                if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    bot.send(sender_hash, f"Unable to connect to Ollama API. Please check if Ollama is running at {OLLAMA_API_URL}")
                else:
                    bot.send(sender_hash, f"Error: {error_msg}")
            else:
                if "response" in response:
                    text = response["response"]
                elif "message" in response:
                    text = response["message"].get("content", "")
                else:
                    text = "Unexpected response format"

                if text.strip():
                    bot.send(sender_hash, text.strip())
                else:
                    bot.send(sender_hash, "Received empty response from AI model")

        # Send chat message to Ollama
        try:
            bot.ollama.chat([{"role": "user", "content": content_str}], callback=callback)
        except Exception as e:
            bot.send(sender_hash, f"Failed to process message: {str(e)}")

    return bot


def main():
    print("Starting OllamaBot...")
    print(f"Ollama API: {OLLAMA_API_URL}")
    print(f"Model: {MODEL}")
    if LXMF_ADMINS:
        print(f"Admins: {len(LXMF_ADMINS)} configured")

    bot = create_bot()
    bot.run()


if __name__ == "__main__":
    main()
