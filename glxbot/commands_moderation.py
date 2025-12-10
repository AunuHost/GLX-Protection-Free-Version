from datetime import datetime

import discord
from discord.ext import commands

from .config import PREFIX, WARN_THRESHOLD
from .state import STATS, GUILD_STATS
from .security import timeout_member, format_seconds
from .discipline import add_warn, get_warn_count, clear_warns


def register_moderation_commands(bot: commands.Bot):
    @bot.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(ctx: commands.Context, member: discord.Member, minutes: int = 10, *, reason: str = "Muted by GLX"):
        if member == ctx.author:
            return await ctx.reply("You can't mute yourself.", mention_author=False)
        ok = await timeout_member(member, minutes, f"{reason} • by {ctx.author}")
        if ok:
            STATS["mutes"] += 1
            GUILD_STATS[ctx.guild.id]["mutes"] += 1
            await ctx.reply(
                f"[GLX] {member.mention} muted for {minutes}m. Reason: {reason}",
                mention_author=False,
            )
        else:
            await ctx.reply("Failed to mute member (timeout not supported).", mention_author=False)

    @bot.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(ctx: commands.Context, member: discord.Member):
        try:
            await member.timeout(until=None, reason=f"Unmuted by {ctx.author}")
            await ctx.reply(f"[GLX] {member.mention} unmuted.", mention_author=False)
        except Exception:
            await ctx.reply("Failed to unmute member.", mention_author=False)

    @bot.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "Banned by GLX"):
        if member == ctx.author:
            return await ctx.reply("You can't ban yourself.", mention_author=False)
        try:
            await member.ban(reason=f"{reason} • by {ctx.author}")
            STATS["bans"] += 1
            GUILD_STATS[ctx.guild.id]["bans"] += 1
            await ctx.reply(f"[GLX] {member} banned. Reason: {reason}", mention_author=False)
        except Exception as e:
            await ctx.reply(f"Failed to ban: `{e}`", mention_author=False)

    @bot.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(ctx: commands.Context, tag: str):
        if "#" not in tag:
            return await ctx.reply("Use format: `name#0000`", mention_author=False)
        name, discrim = tag.split("#", 1)
        bans = await ctx.guild.bans()
        target_entry = None
        for entry in bans:
            if entry.user.name == name and entry.user.discriminator == discrim:
                target_entry = entry
                break
        if target_entry is None:
            return await ctx.reply("User not found in ban list.", mention_author=False)
        try:
            await ctx.guild.unban(target_entry.user, reason=f"Unbanned by {ctx.author}")
            await ctx.reply(f"[GLX] Unbanned {target_entry.user} ({target_entry.user.id})", mention_author=False)
        except Exception as e:
            await ctx.reply(f"Failed to unban: `{e}`", mention_author=False)

    @bot.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "Kicked by GLX"):
        if member == ctx.author:
            return await ctx.reply("You can't kick yourself.", mention_author=False)
        try:
            await member.kick(reason=f"{reason} • by {ctx.author}")
            STATS["kicks"] += 1
            GUILD_STATS[ctx.guild.id]["kicks"] += 1
            await ctx.reply(f"[GLX] {member} kicked. Reason: {reason}", mention_author=False)
        except Exception as e:
            await ctx.reply(f"Failed to kick: `{e}`", mention_author=False)

    @bot.command(name="clear", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx: commands.Context, amount: int = 10):
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await ctx.send(
                f"[GLX] Cleared {len(deleted) - 1} messages.",
                delete_after=5,
            )
        except Exception as e:
            await ctx.reply(f"Failed to clear messages: `{e}`", mention_author=False)

    @bot.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        if member == ctx.author:
            return await ctx.reply("You can't warn yourself.", mention_author=False)
        if member.bot:
            return await ctx.reply("You can't warn a bot.", mention_author=False)

        await add_warn(
            ctx.guild,
            member,
            f"Manual warn: {reason} (by {ctx.author})",
            source="MANUAL",
        )

        await ctx.reply(
            f"[GLX] {member.mention} has been warned. Reason: {reason}",
            mention_author=False,
        )

    @bot.command(name="warnings", aliases=["warns"])
    @commands.has_permissions(moderate_members=True)
    async def warnings(ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        count = get_warn_count(ctx.guild.id, member.id)
        await ctx.reply(
            f"{member.mention} currently has {count}/{WARN_THRESHOLD} warnings.",
            mention_author=False,
        )

    @bot.command(name="clearwarns")
    @commands.has_permissions(administrator=True)
    async def clearwarns(ctx: commands.Context, member: discord.Member):
        old = clear_warns(ctx.guild.id, member.id)
        await ctx.reply(
            f"[GLX] Cleared {old} warnings for {member.mention}.",
            mention_author=False,
        )
