from lxmfy import Command


class BasicCommands:
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "debug"):
            self.bot.debug = False
        self.commands = []

    def get_commands(self):
        """Get all commands registered to this cog"""
        commands = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_command"):
                commands.append(attr._command)
        return commands

    @Command(name="hello", description="Says hello")
    def hello(self, ctx):
        ctx.reply(f"Hello {ctx.sender}!")

    @Command(name="about", description="About this bot")
    def about(self, ctx):
        ctx.reply("I'm a bot created with LXMFy!")

    @Command(name="help", description="Show available commands")
    def help(self, ctx):
        commands = []
        for cog in self.bot.cogs.values():
            if hasattr(cog, "get_commands"):
                for cmd in cog.get_commands():
                    commands.append(f"{cmd.name}: {cmd.description}")

        help_text = "Available commands:\n" + "\n".join(commands)
        ctx.reply(help_text)

    @Command(name="debug", description="Toggle debug mode")
    def debug(self, ctx):
        self.bot.debug = not self.bot.debug
        ctx.reply(f"Debug mode: {'enabled' if self.bot.debug else 'disabled'}")


def setup(bot):
    bot.add_cog(BasicCommands(bot))
