import os
import discord

PREFIX = os.getenv("GLX_PREFIX", "!")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or "PUT_YOUR_BOT_TOKEN_HERE"

GLX_WEB_HOST = os.getenv("GLX_WEB_HOST", "0.0.0.0")
GLX_WEB_PORT = int(os.getenv("GLX_WEB_PORT", "8000"))

GAME_STATUS = os.getenv(
    "GLX_GAME_STATUS",
    "GLX Protection • Guarding your community",
)

LOG_CHANNEL_NAME = os.getenv("GLX_LOG_CHANNEL_NAME", "glx-logs")

ANTISPAM_ENABLED_DEFAULT = os.getenv("GLX_ANTISPAM_ENABLED", "true").lower() == "true"
ANTIRAID_ENABLED_DEFAULT = os.getenv("GLX_ANTIRAID_ENABLED", "true").lower() == "true"
AUTOMOD_ENABLED_DEFAULT = os.getenv("GLX_AUTOMOD_ENABLED", "true").lower() == "true"
ANTIINVITES_ENABLED_DEFAULT = os.getenv("GLX_ANTIINVITES_ENABLED", "true").lower() == "true"
ANTIMENTIONS_ENABLED_DEFAULT = os.getenv("GLX_ANTIMENTIONS_ENABLED", "true").lower() == "true"
GLX_NUKE_ENABLED_DEFAULT = os.getenv("GLX_NUKE_ENABLED", "false").lower() == "true"

SPAM_WINDOW_SECONDS = int(os.getenv("GLX_SPAM_WINDOW_SECONDS", "7"))
SPAM_MAX_MESSAGES = int(os.getenv("GLX_SPAM_MAX_MESSAGES", "7"))

AUTO_MUTE_SECONDS = int(os.getenv("GLX_AUTOMUTE_SECONDS", str(10 * 60)))

RAID_WINDOW_SECONDS = int(os.getenv("GLX_RAID_WINDOW_SECONDS", "10"))
RAID_JOIN_THRESHOLD = int(os.getenv("GLX_RAID_JOIN_THRESHOLD", "6"))
RAID_LOCK_MINUTES = int(os.getenv("GLX_RAID_LOCK_MINUTES", "10"))

MENTION_THRESHOLD = int(os.getenv("GLX_MENTION_THRESHOLD", "8"))

AUTOMOD_MAX_RULES = int(os.getenv("GLX_AUTOMOD_MAX_RULES", "80"))
AUTOMOD_KEYWORD_RULES = int(os.getenv("GLX_AUTOMOD_KEYWORD_RULES", "60"))
AUTOMOD_MENTION_LIMIT = int(os.getenv("GLX_AUTOMOD_MENTION_LIMIT", "6"))

WARN_THRESHOLD = int(os.getenv("GLX_WARN_THRESHOLD", "5"))
WARN_MUTE_MINUTES = int(os.getenv("GLX_WARN_MUTE_MINUTES", "90"))

OWNER_ID = int(os.getenv("GLX_OWNER_ID", "0") or 0)

INVITE_PATTERNS = (
    "discord.gg/",
    "discord.com/invite/",
    "discordapp.com/invite/",
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
if hasattr(intents, "auto_moderation_configuration"):
    intents.auto_moderation_configuration = True
if hasattr(intents, "auto_moderation_execution"):
    intents.auto_moderation_execution = True
