from datetime import datetime, timedelta
from typing import Optional

import discord

from .config import LOG_CHANNEL_NAME
from .state import (
    log,
    START_TIME,
    STATS,
    GUILD_STATS,
)


def human_delta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def uptime_str() -> str:
    return human_delta(datetime.utcnow() - START_TIME)


def format_seconds(sec: int) -> str:
    if sec < 60:
        return f"{sec}s"
    if sec % 60 == 0:
        m = sec // 60
        return f"{m}m"
    m, s = divmod(sec, 60)
    return f"{m}m {s}s"


def is_whitelisted(member: discord.Member, whitelist: set) -> bool:
    if member.guild_permissions.administrator:
        return True
    return member.id in whitelist


async def get_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    existing = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if existing:
        return existing
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                read_message_history=False,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=True,
            ),
        }
        ch = await guild.create_text_channel(
            LOG_CHANNEL_NAME,
            overwrites=overwrites,
            reason="GLX Protection • create log channel",
        )
        return ch
    except Exception as e:
        log.warning("Failed to create log channel in %s: %s", guild.name, e)
        return None


async def log_event(guild: discord.Guild, title: str, description: str, colour=None):
    ch = await get_log_channel(guild)
    if not ch:
        return
    embed = discord.Embed(
        title="GLX • " + title,
        description=description,
        colour=colour or discord.Color.red(),
        timestamp=datetime.utcnow(),
    )
    try:
        await ch.send(embed=embed)
    except Exception:
        pass


async def timeout_member(member: discord.Member, minutes: float, reason: str) -> bool:
    until = datetime.utcnow() + timedelta(minutes=minutes)
    try:
        await member.timeout(until=until, reason=reason)
        return True
    except AttributeError as e:
        log.warning("Timeout not supported on this library: %s", e)
        return False
    except Exception as e:
        log.warning("Failed to timeout %s in %s: %s", member.id, member.guild.name, e)
        return False


async def set_raid_lock(guild: discord.Guild, enabled: bool, reason: str) -> int:
    changed = 0
    for channel in guild.text_channels:
        try:
            overwrites = channel.overwrites_for(guild.default_role)
            if enabled:
                if overwrites.send_messages is False:
                    continue
                overwrites.send_messages = False
            else:
                if overwrites.send_messages is None:
                    continue
                overwrites.send_messages = None
            await channel.set_permissions(
                guild.default_role,
                overwrite=overwrites,
                reason=reason,
            )
            changed += 1
        except Exception:
            continue
    if enabled and changed:
        STATS["raid_locks"] += 1
        GUILD_STATS[guild.id]["raid_locks"] += 1
    return changed
