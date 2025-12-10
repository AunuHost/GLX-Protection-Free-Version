from discord.ext import commands

from .config import PREFIX, intents
from .events import register_events
from .commands_moderation import register_moderation_commands
from .commands_protection import register_protection_commands
from .commands_community import register_community_commands
from .commands_access import register_access_commands


def create_bot() -> commands.Bot:
    bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
    register_events(bot)
    register_moderation_commands(bot)
    register_protection_commands(bot)
    register_community_commands(bot)
    register_access_commands(bot)
    return bot
