from collections import defaultdict
from typing import Dict

import discord

from .config import WARN_THRESHOLD, WARN_MUTE_MINUTES
from .state import STATS, GUILD_STATS, log
from .security import log_event, timeout_member, format_seconds


WARNS: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))


async def add_warn(guild: discord.Guild, member: discord.Member, reason: str, source: str = "AUTO"):
    gdict = WARNS[guild.id]
    gdict[member.id] += 1
    count = gdict[member.id]

    try:
        await log_event(
            guild,
            "Warn Issued",
            f"{member.mention} received a warn (`{source}`).\n"
            f"Reason: {reason}\n"
            f"Total warns: `{count}/{WARN_THRESHOLD}`.",
        )
    except Exception:
        pass

    if count >= WARN_THRESHOLD:
        minutes = WARN_MUTE_MINUTES
        ok = await timeout_member(
            member,
            minutes,
            f"GLX Protection • warn threshold reached ({count})",
        )
        if ok:
            STATS["timeouts"] += 1
            GUILD_STATS[guild.id]["timeouts"] += 1
            try:
                await log_event(
                    guild,
                    "Auto-Mute (Warn Threshold)",
                    f"{member.mention} was auto-muted for "
                    f"**{format_seconds(minutes * 60)}** after reaching "
                    f"`{count}` warnings.",
                )
            except Exception:
                pass


def get_warn_count(guild_id: int, user_id: int) -> int:
    return WARNS[guild_id].get(user_id, 0)


def clear_warns(guild_id: int, user_id: int) -> int:
    gdict = WARNS[guild_id]
    old = gdict.pop(user_id, 0)
    return old
