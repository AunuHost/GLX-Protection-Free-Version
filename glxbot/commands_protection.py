from datetime import datetime

import discord
from discord.ext import commands

from .config import PREFIX
from .state import STATS, GUILD_STATS, FEATURES, WHITELIST
from .security import set_raid_lock, log_event, uptime_str
from .auth import get_license_info


def register_protection_commands(bot: commands.Bot):
    @bot.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(ctx: commands.Context, channel: discord.TextChannel = None):
        ch = channel or ctx.channel
        overwrites = ch.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = False
        try:
            await ch.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites,
                reason=f"Locked by {ctx.author}",
            )
            await ctx.reply(f"[GLX] Locked {ch.mention}.", mention_author=False)
        except Exception as e:
            await ctx.reply(f"Failed to lock: `{e}`", mention_author=False)

    @bot.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(ctx: commands.Context, channel: discord.TextChannel = None):
        ch = channel or ctx.channel
        overwrites = ch.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = None
        try:
            await ch.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites,
                reason=f"Unlocked by {ctx.author}",
            )
            await ctx.reply(f"[GLX] Unlocked {ch.mention}.", mention_author=False)
        except Exception as e:
            await ctx.reply(f"Failed to unlock: `{e}`", mention_author=False)

    @bot.command(name="raidlock")
    @commands.has_permissions(manage_guild=True)
    async def raidlock(ctx: commands.Context, mode: str = "on"):
        mode = mode.lower()
        if mode in ("on", "enable", "enabled"):
            changed = await set_raid_lock(ctx.guild, True, f"Manual raid lock by {ctx.author}")
            await ctx.reply(
                f"[GLX] Raid lock ENABLED on {changed} channels.",
                mention_author=False,
            )
            await log_event(
                ctx.guild,
                "Manual Raid Lock",
                f"Triggered by {ctx.author.mention} on {changed} channels.",
                colour=discord.Color.orange(),
            )
        elif mode in ("off", "disable", "disabled"):
            changed = await set_raid_lock(ctx.guild, False, f"Manual raid unlock by {ctx.author}")
            await ctx.reply(
                f"[GLX] Raid lock DISABLED on {changed} channels.",
                mention_author=False,
            )
            await log_event(
                ctx.guild,
                "Manual Raid Unlock",
                f"Triggered by {ctx.author.mention} on {changed} channels.",
                colour=discord.Color.green(),
            )
        else:
            await ctx.reply(f"Usage: `{PREFIX}raidlock on` or `{PREFIX}raidlock off`", mention_author=False)

    @bot.command(name="togglespam")
    @commands.has_permissions(manage_guild=True)
    async def togglespam(ctx: commands.Context):
        FEATURES["anti_spam"] = not FEATURES.get("anti_spam", True)
        state = "ON" if FEATURES["anti_spam"] else "OFF"
        await ctx.reply(f"[GLX] Anti-Spam is now {state}.", mention_author=False)

    @bot.command(name="toggleinvites")
    @commands.has_permissions(manage_guild=True)
    async def toggleinvites(ctx: commands.Context):
        FEATURES["anti_invites"] = not FEATURES.get("anti_invites", True)
        state = "ON" if FEATURES["anti_invites"] else "OFF"
        await ctx.reply(f"[GLX] Anti-Invites is now {state}.", mention_author=False)

    @bot.command(name="togglementions")
    @commands.has_permissions(manage_guild=True)
    async def togglementions(ctx: commands.Context):
        FEATURES["anti_mentions"] = not FEATURES.get("anti_mentions", True)
        state = "ON" if FEATURES["anti_mentions"] else "OFF"
        await ctx.reply(f"[GLX] Anti-Mentions is now {state}.", mention_author=False)

    @bot.command(name="togglenuke")
    @commands.has_permissions(administrator=True)
    async def togglenuke(ctx: commands.Context):
        FEATURES["nuke"] = not FEATURES.get("nuke", False)
        state = "ON" if FEATURES["nuke"] else "OFF"
        await ctx.reply(f"[GLX] Nuke command is now {state}.", mention_author=False)

    @bot.command(name="nuke")
    @commands.has_permissions(administrator=True)
    async def nuke(ctx: commands.Context, channel: discord.TextChannel = None):
        if not FEATURES.get("nuke", False):
            return await ctx.reply("Nuke is currently disabled. Use `!togglenuke` to enable it.", mention_author=False)
        ch = channel or ctx.channel
        try:
            pos = ch.position
            new_ch = await ch.clone(reason=f"Nuked by {ctx.author} via GLX Protection")
            await ch.delete(reason=f"Nuked by {ctx.author} via GLX Protection")
            await new_ch.edit(position=pos)
            STATS["nukes"] += 1
            GUILD_STATS[ctx.guild.id]["nukes"] += 1
            await new_ch.send("[GLX] This channel has been nuked by GLX Protection.")
        except Exception as e:
            await ctx.reply(f"Failed to nuke channel: `{e}`", mention_author=False)

    @bot.command(name="glxwhitelist")
    @commands.has_permissions(manage_guild=True)
    async def glxwhitelist(ctx: commands.Context, member: discord.Member):
        WHITELIST.add(member.id)
        await ctx.reply(f"[GLX] {member.mention} added to GLX whitelist.", mention_author=False)

    @bot.command(name="glxunwhitelist")
    @commands.has_permissions(manage_guild=True)
    async def glxunwhitelist(ctx: commands.Context, member: discord.Member):
        if member.id in WHITELIST:
            WHITELIST.remove(member.id)
            await ctx.reply(f"[GLX] {member.mention} removed from GLX whitelist.", mention_author=False)
        else:
            await ctx.reply(f"{member.mention} is not in GLX whitelist.", mention_author=False)

    @bot.command(name="glxstats")
    @commands.has_permissions(manage_guild=True)
    async def glxstats(ctx: commands.Context):
        embed = discord.Embed(
            title="GLX Protection • Stats",
            colour=discord.Color.teal(),
            timestamp=datetime.utcnow(),
        )
        stats = GUILD_STATS[ctx.guild.id]
        for k, v in stats.items():
            embed.add_field(name=k.replace("_", " ").title(), value=str(v))
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(name="glx")
    async def glx(ctx: commands.Context):
        guild_count = len(bot.guilds)
        member_count = sum(g.member_count or 0 for g in bot.guilds)
        embed = discord.Embed(
            title="GLX Protection",
            colour=discord.Color.dark_blue(),
            timestamp=datetime.utcnow(),
        )
        embed.description = (
            "Advanced security layer for Discord servers.\n"
            "Anti-spam • Anti-raid • Discord AutoMod • Moderation & community tools."
        )
        embed.add_field(name="Servers Protected", value=str(guild_count))
        embed.add_field(name="Total Members", value=str(member_count))
        embed.add_field(name="Uptime", value=uptime_str(), inline=False)
        li = get_license_info()
        license_line = f"{li['type']}"
        if li["code_masked"]:
            license_line += f" • {li['code_masked']}"
        if li["created_ago"]:
            license_line += f" • generated {li['created_ago']} ago"
        embed.add_field(
            name="Web Login License",
            value=license_line,
            inline=False,
        )
        embed.add_field(
            name="Protection Layer",
            value=(
                f"Anti-Spam: { 'ON' if FEATURES.get('anti_spam', True) else 'OFF' }\n"
                f"Anti-Raid: { 'ON' if FEATURES.get('anti_raid', True) else 'OFF' }\n"
                f"AutoMod: { 'ON' if FEATURES.get('automod', True) else 'OFF' }\n"
                f"Anti-Invites: { 'ON' if FEATURES.get('anti_invites', True) else 'OFF' }\n"
                f"Anti-Mentions: { 'ON' if FEATURES.get('anti_mentions', True) else 'OFF' }\n"
                f"Nuke Cmd: { 'ON' if FEATURES.get('nuke', False) else 'OFF' }"
            ),
            inline=False,
        )
        embed.set_footer(text="GLX Protection • Created by AunuXdev (Creator/Developer)")
        await ctx.reply(embed=embed, mention_author=False)
