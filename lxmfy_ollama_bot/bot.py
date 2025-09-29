import argparse
import os
import time
from queue import Queue
from threading import Thread

import requests
from dotenv import load_dotenv
from lxmfy import IconAppearance, LXMFBot, pack_icon_appearance_field


def parse_args():
    parser = argparse.ArgumentParser(description="Ollama Bot")
    parser.add_argument("--env", type=str, help="Path to env file")
    parser.add_argument("--name", type=str, help="Bot name")
    parser.add_argument("--api-url", type=str, help="Ollama API URL")
    parser.add_argument("--model", type=str, help="Ollama model name")
    parser.add_argument(
        "--admins", type=str, help="Comma-separated list of admin LXMF hashes",
    )
    return parser.parse_args()


args = parse_args()

if args.env:
    load_dotenv(args.env)
else:
    load_dotenv()

BOT_NAME = args.name or os.getenv("BOT_NAME", "OllamaBot")
OLLAMA_API_URL = args.api_url or os.getenv(
    "OLLAMA_API_URL", "http://localhost:11434",
)
MODEL = args.model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
SAVE_CHAT_HISTORY = False
LXMF_ADMINS = (
    set(filter(None, args.admins.split(",")))
    if args.admins
    else set(filter(None, os.getenv("LXMF_ADMINS", "").split(",")))
)
SIGNATURE_VERIFICATION_ENABLED = os.getenv("SIGNATURE_VERIFICATION_ENABLED", "false").lower() == "true"
REQUIRE_MESSAGE_SIGNATURES = os.getenv("REQUIRE_MESSAGE_SIGNATURES", "false").lower() == "true"
BOT_ICON = os.getenv("BOT_ICON", "robot")
ICON_FG_COLOR = os.getenv("ICON_FG_COLOR", "ffffff")
ICON_BG_COLOR = os.getenv("ICON_BG_COLOR", "2563eb")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")


class OllamaAPI:
    def __init__(self, api_url, timeout=900, queue_size=10):
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
                    if not any(MODEL in m["name"] for m in models):
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
                    time.sleep(1) # Add sleep here to prevent busy-waiting on errors
                finally:
                    self.request_queue.task_done()

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
        name=BOT_NAME,
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
        signature_verification_enabled=SIGNATURE_VERIFICATION_ENABLED,
        require_message_signatures=REQUIRE_MESSAGE_SIGNATURES,
    )

    # Set up bot icon
    try:
        icon_data = IconAppearance(
            icon_name=BOT_ICON,
            fg_color=bytes.fromhex(ICON_FG_COLOR),
            bg_color=bytes.fromhex(ICON_BG_COLOR),
        )
        bot.icon_lxmf_field = pack_icon_appearance_field(icon_data)
    except ValueError as e:
        print(f"Warning: Invalid icon color format: {e}. Using default colors.")
        icon_data = IconAppearance(
            icon_name=BOT_ICON,
            fg_color=b"\xff\xff\xff",  # white
            bg_color=b"\x25\x63\xeb",  # blue
        )
        bot.icon_lxmf_field = pack_icon_appearance_field(icon_data)

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
        ctx.reply(help_text, lxmf_fields=bot.icon_lxmf_field)

    @bot.command(name="about")
    def about_command(ctx):
        """Show bot information"""
        sig_status = "Enabled" if SIGNATURE_VERIFICATION_ENABLED else "Disabled"
        sig_required = "Required" if REQUIRE_MESSAGE_SIGNATURES else "Optional"
        about_text = f"""OllamaBot v1.0.0

Connected to: {OLLAMA_API_URL}
Model: {MODEL}
Admins: {len(LXMF_ADMINS)} configured
Signature Verification: {sig_status}
Message Signatures: {sig_required}
Bot Icon: {BOT_ICON}
Icon Colors: FG={ICON_FG_COLOR}, BG={ICON_BG_COLOR}

This bot allows you to chat with AI models through Ollama.
Simply send a message without any command prefix to start chatting."""
        ctx.reply(about_text, lxmf_fields=bot.icon_lxmf_field)



    @bot.events.on("message_received")
    def handle_message(event):
        """Handle all incoming messages"""
        lxmf_message = event.data.get("message")
        sender_hash = event.data.get("sender")

        if not lxmf_message or not hasattr(lxmf_message, "content") or not lxmf_message.content:
            return

        try:
            content_str = lxmf_message.content.decode("utf-8").strip()
        except UnicodeDecodeError:
            bot.send(sender_hash, "Error: Message content is not valid UTF-8.", lxmf_fields=bot.icon_lxmf_field)
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
                    bot.send(sender_hash, f"Unable to connect to Ollama API. Please check if Ollama is running at {OLLAMA_API_URL}", lxmf_fields=bot.icon_lxmf_field)
                else:
                    bot.send(sender_hash, f"Error: {error_msg}", lxmf_fields=bot.icon_lxmf_field)
            else:
                if "response" in response:
                    text = response["response"]
                elif "message" in response:
                    text = response["message"].get("content", "")
                else:
                    text = "Unexpected response format"

                if text.strip():
                    bot.send(sender_hash, text.strip(), lxmf_fields=bot.icon_lxmf_field)
                else:
                    bot.send(sender_hash, "Received empty response from AI model", lxmf_fields=bot.icon_lxmf_field)

        # Send chat message to Ollama
        try:
            messages = []
            if SYSTEM_PROMPT:
                messages.append({"role": "system", "content": SYSTEM_PROMPT})
            messages.append({"role": "user", "content": content_str})
            bot.ollama.chat(messages, callback=callback)
        except Exception as e:
            bot.send(sender_hash, f"Failed to process message: {e!s}", lxmf_fields=bot.icon_lxmf_field)

    return bot


def main():
    print(f"Starting {BOT_NAME}...")
    print(f"Ollama API: {OLLAMA_API_URL}")
    print(f"Model: {MODEL}")
    if LXMF_ADMINS:
        print(f"Admins: {len(LXMF_ADMINS)} configured")
    print(f"Signature Verification: {'Enabled' if SIGNATURE_VERIFICATION_ENABLED else 'Disabled'}")
    print(f"Require Message Signatures: {'Yes' if REQUIRE_MESSAGE_SIGNATURES else 'No'}")
    print(f"Bot Icon: {BOT_ICON}")
    print(f"Icon Colors: FG={ICON_FG_COLOR}, BG={ICON_BG_COLOR}")

    bot = create_bot()
    bot.run()


if __name__ == "__main__":
    main()
