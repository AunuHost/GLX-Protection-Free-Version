from datetime import datetime

import discord
from discord.ext import commands

from .config import PREFIX, OWNER_ID
from .auth import create_user_key, create_admin_key


def register_access_commands(bot: commands.Bot):
    @bot.command(name="generate", aliases=["genaccess", "gen"])
    @commands.has_permissions(administrator=True)
    async def generate(ctx: commands.Context, *, pattern: str = None):
        """Generate user web key (code + PIN) for this guild only."""
        if ctx.guild is None:
            return await ctx.reply("Use this command inside a server.", mention_author=False)

        record = create_user_key(ctx.guild, ctx.author, pattern)

        await ctx.reply(
            "New GLX USER web key generated.\n"
            f"Code: `{record['display_code']}`\n"
            f"2FA PIN: `{record['pin']}`\n"
            "Use this code and PIN on the web dashboard login page.\n"
            "This key is scoped only to this server.",
            mention_author=False,
        )

    @bot.command(name="genadmin", aliases=["generateadmin"])
    async def genadmin(ctx: commands.Context, *, pattern: str = None):
        """Generate ADMIN web key (can see all servers & admin panel)."""
        if ctx.author.id != OWNER_ID:
            return await ctx.reply("Only the configured bot owner can generate an admin panel key.", mention_author=False)
        record = create_admin_key(ctx.author, pattern)
        await ctx.reply(
            "New GLX ADMIN web key generated.\n"
            f"Code: `{record['display_code']}`\n"
            f"2FA PIN: `{record['pin']}`\n"
            "Use this code and PIN on the web dashboard login page to unlock the global admin panel.",
            mention_author=False,
        )
