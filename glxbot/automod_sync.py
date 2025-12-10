import discord

from .config import (
    AUTOMOD_MAX_RULES,
    AUTOMOD_KEYWORD_RULES,
    AUTOMOD_MENTION_LIMIT,
)
from .state import STATS, log, AUTOMOD_CAPACITY_WARNED_GUILDS
from .security import log_event, get_log_channel


async def sync_automod(bot: discord.Client, guild: discord.Guild, features: dict):
    """Synchronize GLX's AutoMod rules with Discord's native AutoMod.

    Very defensive to avoid spam: if limits are reached we log ONCE per guild
    then stay silent afterwards (no console spam).
    """
    if not features.get("automod", True):
        log.info("[GLX] AutoMod disabled by config; skipping for %s", guild.name)
        return

    http = getattr(bot, "http", None)
    if http is None:
        log.warning("[GLX] HTTP client not available; cannot sync AutoMod for %s", guild.name)
        return

    get_rules = getattr(http, "get_auto_moderation_rules", None)
    create_rule = getattr(http, "create_auto_moderation_rule", None)

    if create_rule is None:
        log.warning("[GLX] AutoMod HTTP methods not available; cannot sync AutoMod for %s", guild.name)
        return

    existing_data = []
    if get_rules is not None:
        try:
            existing_data = await get_rules(guild.id)
        except Exception as e:
            log.warning("[GLX] Failed to fetch AutoMod rules in %s: %s", guild.name, e)

    existing_names = set()
    current_count = 0
    if isinstance(existing_data, list):
        current_count = len(existing_data)
        for r in existing_data:
            name = None
            if isinstance(r, dict):
                name = r.get("name")
            else:
                name = getattr(r, "name", None)
            if isinstance(name, str):
                existing_names.add(name)

    limit = AUTOMOD_MAX_RULES
    if current_count >= limit:
        if guild.id not in AUTOMOD_CAPACITY_WARNED_GUILDS:
            AUTOMOD_CAPACITY_WARNED_GUILDS.add(guild.id)
            log.info(
                "[GLX] AutoMod rule count already at limit (%s) for %s; no additional GLX rules will be created.",
                limit,
                guild.name,
            )
        return

    log_channel = await get_log_channel(guild)
    log_channel_id = log_channel.id if log_channel else None

    base_actions = [
        {
            "type": 1,
            "metadata": {
                "custom_message": "GLX Protection blocked this message."
            },
        }
    ]
    if log_channel_id is not None:
        base_actions.append(
            {
                "type": 2,
                "metadata": {"channel_id": log_channel_id},
            }
        )

    created = 0

    async def create_if_missing(name, trigger_type, trigger_metadata):
        nonlocal current_count, created
        if current_count >= limit:
            return
        if name in existing_names:
            return

        payload = {
            "name": name,
            "event_type": 1,
            "trigger_type": trigger_type,
            "trigger_metadata": trigger_metadata,
            "actions": base_actions,
            "enabled": True,
            "exempt_roles": [],
            "exempt_channels": [],
        }

        try:
            await create_rule(guild.id, payload)
        except discord.HTTPException as e:
            message = str(e)
            if "AUTO_MODERATION_MAX_RULES_OF_TYPE_EXCEEDED" in message or "MAX_AUTO_MODERATION_RULES" in message:
                if guild.id not in AUTOMOD_CAPACITY_WARNED_GUILDS:
                    AUTOMOD_CAPACITY_WARNED_GUILDS.add(guild.id)
                    log.info(
                        "[GLX] AutoMod per-type/total limit reached in %s; further GLX rules will be skipped.",
                        guild.name,
                    )
                return
            else:
                log.debug(
                    "[GLX] HTTP error while creating AutoMod rule %s in %s: %s",
                    name,
                    guild.name,
                    e,
                )
        except Exception as e:
            log.debug(
                "[GLX] Failed to create AutoMod rule %s in %s: %s",
                name,
                guild.name,
                e,
            )
        else:
            existing_names.add(name)
            current_count += 1
            created += 1
            STATS["automod_rules_created"] += 1

    await create_if_missing("GLX-SPAM", 3, {})
    await create_if_missing(
        "GLX-MENTION-SPAM",
        5,
        {"mention_total_limit": AUTOMOD_MENTION_LIMIT},
    )
    await create_if_missing(
        "GLX-PRESETS",
        4,
        {"presets": [1, 2, 3], "allow_list": []},
    )

    remaining_slots = max(limit - current_count, 0)
    kw_to_create = min(AUTOMOD_KEYWORD_RULES, remaining_slots)

    for i in range(1, kw_to_create + 1):
        name = f"GLX-KW-{i}"
        if name in existing_names:
            continue
        keywords = [
            f"glxkw-{i}-alpha",
            f"glxkw-{i}-bravo",
            f"glxkw-{i}-charlie",
        ]
        await create_if_missing(
            name,
            1,
            {"keyword_filter": keywords},
        )

    if created:
        log.info(
            "[GLX] Synced %s AutoMod rule(s) in %s (names tracked: %s).",
            created,
            guild.name,
            len(existing_names),
        )
        await log_event(
            guild,
            "AutoMod Sync",
            f"Created {created} GLX AutoMod rule(s).\n"
            f"Configured cap: {limit} • Tracked names: {len(existing_names)}.",
            colour=discord.Color.dark_gold(),
        )
