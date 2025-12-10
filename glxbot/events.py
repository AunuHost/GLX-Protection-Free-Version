import time
from datetime import datetime
import asyncio

import discord
from discord.ext import commands

from .config import (
    PREFIX,
    GAME_STATUS,
    SPAM_WINDOW_SECONDS,
    SPAM_MAX_MESSAGES,
    AUTO_MUTE_SECONDS,
    RAID_WINDOW_SECONDS,
    RAID_JOIN_THRESHOLD,
    RAID_LOCK_MINUTES,
    MENTION_THRESHOLD,
    INVITE_PATTERNS,
)
from .state import (
    log,
    BANNER,
    STATS,
    GUILD_STATS,
    FEATURES,
    user_messages,
    guild_joins,
    traffic_points,
    SUGGESTION_CHANNELS,
    WELCOME_CHANNELS,
    WELCOME_MESSAGES,
    DEFAULT_WELCOME_TEMPLATE,
    WHITELIST,
)
from .security import (
    timeout_member,
    set_raid_lock,
    log_event,
    format_seconds,
    uptime_str,
    is_whitelisted,
)
from .discipline import add_warn
from .automod_sync import sync_automod
from .auth import get_license_info


def register_events(bot: commands.Bot):
    @bot.event
    async def on_ready():
        log.info(BANNER)
        log.info("Logged in as %s (%s)", bot.user, bot.user.id)
        log.info("Prefix: %s", PREFIX)
        activity = discord.Game(GAME_STATUS)
        try:
            await bot.change_presence(
                status=discord.Status.do_not_disturb,
                activity=activity,
            )
        except Exception as e:
            log.warning("Failed to set presence: %s", e)

        for g in bot.guilds:
            log.info("Connected to guild: %s (%s)", g.name, g.id)
            if FEATURES.get("automod", True):
                bot.loop.create_task(sync_automod(bot, g, FEATURES))

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        log.info("Joined new guild: %s (%s)", guild.name, guild.id)
        await log_event(
            guild,
            "GLX Protection Online",
            f"GLX Protection is now guarding **{guild.name}**.\n"
            f"Prefix: `{PREFIX}` • Try `{PREFIX}help`.",
            colour=discord.Color.green(),
        )
        if FEATURES.get("automod", True):
            bot.loop.create_task(sync_automod(bot, guild, FEATURES))

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot or not message.guild:
            return

        STATS["messages_seen"] += 1
        GUILD_STATS[message.guild.id]["messages_seen"] += 1
        traffic_points.append(time.time())

        if is_whitelisted(message.author, WHITELIST):
            await bot.process_commands(message)
            return

        if FEATURES.get("anti_spam", True):
            now = time.time()
            dq = user_messages[message.author.id]
            dq.append(now)
            cutoff = now - SPAM_WINDOW_SECONDS
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= SPAM_MAX_MESSAGES:
                STATS["spam_flags"] += 1
                GUILD_STATS[message.guild.id]["spam_flags"] += 1

                await add_warn(
                    message.guild,
                    message.author,
                    "Auto warn: spam detected by GLX.",
                    source="SPAM",
                )

                try:
                    await message.delete()
                except Exception:
                    pass

                duration_sec = AUTO_MUTE_SECONDS
                ok = await timeout_member(
                    message.author,
                    duration_sec / 60.0,
                    "GLX Protection • spam detected",
                )
                if ok:
                    STATS["timeouts"] += 1
                    GUILD_STATS[message.guild.id]["timeouts"] += 1
                    await log_event(
                        message.guild,
                        "Anti-Spam",
                        f"{message.author.mention} was auto-timed out for "
                        f"{format_seconds(duration_sec)} after sending "
                        f"{len(dq)} messages in {SPAM_WINDOW_SECONDS}s "
                        f"in {message.channel.mention}.",
                    )
                dq.clear()

        if FEATURES.get("anti_invites", True):
            content_lower = message.content.lower()
            if any(p in content_lower for p in INVITE_PATTERNS):
                try:
                    await message.delete()
                except Exception:
                    pass
                STATS["invites_blocked"] += 1
                GUILD_STATS[message.guild.id]["invites_blocked"] += 1

                await add_warn(
                    message.guild,
                    message.author,
                    "Auto warn: invite link blocked by GLX.",
                    source="INVITE",
                )

                await log_event(
                    message.guild,
                    "Anti-Invites",
                    f"Deleted invite link from {message.author.mention} in {message.channel.mention}.",
                    colour=discord.Color.blue(),
                )

        if FEATURES.get("anti_mentions", True):
            mention_count = len(message.mentions) + (1 if message.mention_everyone else 0)
            if mention_count >= MENTION_THRESHOLD:
                try:
                    await message.delete()
                except Exception:
                    pass
                STATS["mentions_flagged"] += 1
                GUILD_STATS[message.guild.id]["mentions_flagged"] += 1

                await add_warn(
                    message.guild,
                    message.author,
                    f"Auto warn: mention flood ({mention_count} mentions) detected by GLX.",
                    source="MENTION",
                )

                duration_sec = AUTO_MUTE_SECONDS
                ok = await timeout_member(
                    message.author,
                    duration_sec / 60.0,
                    "GLX Protection • mention flood detected",
                )
                if ok:
                    STATS["timeouts"] += 1
                    GUILD_STATS[message.guild.id]["timeouts"] += 1
                    await log_event(
                        message.guild,
                        "Anti-Mentions",
                        f"{message.author.mention} was auto-timed out for "
                        f"{format_seconds(duration_sec)} after mentioning "
                        f"{mention_count} users in {message.channel.mention}.",
                        colour=discord.Color.orange(),
                    )

        await bot.process_commands(message)

    @bot.event
    async def on_member_join(member: discord.Member):
        if not member.guild:
            return
        STATS["joins_seen"] += 1
        GUILD_STATS[member.guild.id]["joins_seen"] += 1

        if FEATURES.get("anti_raid", True):
            now = time.time()
            dq = guild_joins[member.guild.id]
            dq.append(now)
            cutoff = now - RAID_WINDOW_SECONDS
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= RAID_JOIN_THRESHOLD:
                STATS["raids_detected"] += 1
                GUILD_STATS[member.guild.id]["raids_detected"] += 1
                changed = await set_raid_lock(
                    member.guild,
                    True,
                    "GLX Protection • suspected join raid",
                )
                await log_event(
                    member.guild,
                    "Raid Lockdown",
                    f"Detected {len(dq)} joins in {RAID_WINDOW_SECONDS}s.\n"
                    f"Raid lockdown enabled on {changed} channels for "
                    f"{RAID_LOCK_MINUTES}m.",
                    colour=discord.Color.orange(),
                )

                async def auto_unlock():
                    await asyncio.sleep(RAID_LOCK_MINUTES * 60)
                    unlocked = await set_raid_lock(
                        member.guild,
                        False,
                        "GLX Protection • auto unlock after raid",
                    )
                    if unlocked:
                        await log_event(
                            member.guild,
                            "Raid Unlock",
                            "Raid window passed. Channels unlocked automatically.",
                            colour=discord.Color.green(),
                        )

                asyncio.create_task(auto_unlock())

        gid = member.guild.id
        ch_id = WELCOME_CHANNELS.get(gid)
        if ch_id:
            channel = member.guild.get_channel(ch_id)
            if channel:
                template = WELCOME_MESSAGES.get(gid, DEFAULT_WELCOME_TEMPLATE)
                text = template.replace("{member}", member.mention).replace("{server}", member.guild.name)
                try:
                    await channel.send(text)
                except Exception:
                    pass
