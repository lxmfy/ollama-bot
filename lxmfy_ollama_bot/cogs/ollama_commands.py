from lxmfy import Command


class OllamaCommands:
    def __init__(self, bot):
        self.bot = bot
        self.storage_key_states = "chat_states"
        self.storage_key_convs = "conversations"
        self.load_states()

    def load_states(self):
        """Load chat states and conversations from storage"""
        self.chat_states = self.bot.storage.get(self.storage_key_states, {})
        if hasattr(self.bot, "save_chat_history") and self.bot.save_chat_history:
            self.conversations = self.bot.storage.get(self.storage_key_convs, {})
        else:
            self.conversations = {}

    def save_states(self):
        """Save chat states and conversations to storage"""
        self.bot.storage.set(self.storage_key_states, self.chat_states)
        if hasattr(self.bot, "save_chat_history") and self.bot.save_chat_history:
            self.bot.storage.set(self.storage_key_convs, self.conversations)

    def update_chat_state(self, sender, increment_count=True):
        """Update chat state for a user"""
        if sender not in self.chat_states:
            self.chat_states[sender] = {
                "chat_mode": False,
                "message_count": 0,
                "address": sender,
                "waiting_response": False,
            }

        if increment_count:
            self.chat_states[sender]["message_count"] += 1

        self.save_states()

    def handle_response(self, ctx, response):
        """Handle API response and send to user"""
        sender = ctx.sender
        if "error" in response:
            ctx.reply(f"Error: {response['error']}")
            return

        if "response" in response:
            message = response["response"]
        elif "message" in response:
            message = response["message"]["content"]
        else:
            message = "Unexpected response format"

        if sender in self.conversations:
            self.conversations[sender].append({"role": "assistant", "content": message})
            self.save_states()

        if sender in self.chat_states:
            self.chat_states[sender]["waiting_response"] = False
            self.save_states()

        ctx.reply(message)

    @Command(name="ask", description="Ask Ollama a question")
    def ask(self, ctx):
        try:

            def callback(response):
                self.handle_response(ctx, response)

            if hasattr(self.bot, "debug") and self.bot.debug:
                ctx.reply("Processing your request...")

            self.bot.ollama.generate(ctx.content, callback=callback)
        except Exception as e:
            ctx.reply(f"Error: {str(e)}")

    @Command(name="chat", description="Start or continue a chat conversation")
    def chat(self, ctx):
        sender = ctx.sender

        if sender in self.chat_states and self.chat_states[sender]["waiting_response"]:
            ctx.reply("Still processing your last request, please wait...")
            return

        if sender not in self.chat_states:
            self.update_chat_state(sender, increment_count=False)

        self.chat_states[sender]["chat_mode"] = True
        self.chat_states[sender]["waiting_response"] = True
        self.save_states()

        if sender not in self.conversations:
            self.conversations[sender] = []
            self.save_states()

        content = ctx.content.replace("chat", "", 1).strip()
        if not content:
            ctx.reply("Please provide a message for the chat!")
            self.chat_states[sender]["waiting_response"] = False
            self.save_states()
            return

        self._handle_chat_message(ctx, content)

    def _handle_chat_message(self, ctx, content):
        """Handle chat messages and update state"""
        sender = ctx.sender

        if sender not in self.conversations:
            self.conversations[sender] = []

        self.conversations[sender].append({"role": "user", "content": content})
        self.save_states()

        try:

            def callback(response):
                self.handle_response(ctx, response)

            if hasattr(self.bot, "debug") and self.bot.debug:
                ctx.reply("Processing your message...")

            self.bot.ollama.chat(self.conversations[sender], callback=callback)

            self.update_chat_state(sender)
        except Exception as e:
            ctx.reply(f"Error: {str(e)}")
            if self.conversations[sender]:
                self.conversations[sender].pop()
                self.save_states()
            self.chat_states[sender]["waiting_response"] = False
            self.save_states()

    @Command(name="reset", description="Reset your chat conversation")
    def reset(self, ctx):
        sender = ctx.sender
        if sender in self.conversations:
            del self.conversations[sender]
            if sender in self.chat_states:
                self.chat_states[sender]["chat_mode"] = False
                self.chat_states[sender]["waiting_response"] = False
            if hasattr(self.bot, "save_chat_history") and self.bot.save_chat_history:
                self.save_states()
            ctx.reply("Chat conversation has been reset!")
        else:
            ctx.reply("No active conversation to reset.")

    def process_message(self, ctx):
        """Process non-command messages for users in chat mode"""
        sender = ctx.sender
        if sender in self.chat_states and self.chat_states[sender]["chat_mode"]:
            if self.chat_states[sender]["waiting_response"]:
                ctx.reply("Still processing your last request, please wait...")
                return True
            self._handle_chat_message(ctx, ctx.content)
            return True
        return False

    def get_commands(self):
        """Get all commands registered to this cog"""
        commands = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_command"):
                commands.append(attr._command)
        return commands


def setup(bot):
    cog = OllamaCommands(bot)
    bot.add_cog(cog)

    @bot.received
    def handle_message(msg):
        if hasattr(msg, "content") and not msg.content.startswith("/"):
            ctx = type(
                "Context",
                (),
                {"sender": msg.sender, "content": msg.content, "reply": msg.reply},
            )
            cog.process_message(ctx)
