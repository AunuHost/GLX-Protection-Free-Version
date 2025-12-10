
from datetime import datetime, timedelta
import asyncio

import discord
from discord.ext import commands

from .config import PREFIX, WARN_THRESHOLD
from .state import STATS, GUILD_STATS, SUGGESTION_CHANNELS, WELCOME_CHANNELS, WELCOME_MESSAGES, DEFAULT_WELCOME_TEMPLATE
from .discipline import get_warn_count


def register_community_commands(bot: commands.Bot):
    @bot.command(name="help")
    async def help_command(ctx: commands.Context):
        embed = discord.Embed(
            title="GLX Protection Commands",
            colour=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed.description = (
            "Security and community assistant for Discord servers.\n"
            f"Prefix: `{PREFIX}`"
        )
        embed.add_field(
            name="General",
            value=(
                f"`{PREFIX}help` show this message\n"
                f"`{PREFIX}ping` show latency\n"
                f"`{PREFIX}glx` show bot overview\n"
                f"`{PREFIX}serverinfo` show information about this server\n"
                f"`{PREFIX}userinfo [user]` show information about a user\n"
                f"`{PREFIX}avatar [user]` show avatar of a user\n"
            ),
            inline=False,
        )
        embed.add_field(
            name="Moderation",
            value=(
                f"`{PREFIX}mute @user [minutes] [reason]`\n"
                f"`{PREFIX}unmute @user`\n"
                f"`{PREFIX}warn @user [reason]` auto timeout after {WARN_THRESHOLD} warns\n"
                f"`{PREFIX}warnings [@user]` check warn count\n"
                f"`{PREFIX}clearwarns @user` reset warns\n"
                f"`{PREFIX}ban @user [reason]`\n"
                f"`{PREFIX}kick @user [reason]`\n"
                f"`{PREFIX}clear [amount]`\n"
                f"`{PREFIX}unban name#0000`\n"
                f"`{PREFIX}slowmode seconds [#channel]` set channel slowmode\n"
                f"`{PREFIX}say [#channel] text` send a message as the bot"
            ),
            inline=False,
        )
        embed.add_field(
            name="Protection",
            value=(
                f"`{PREFIX}raidlock on|off` global raid lock\n"
                f"`{PREFIX}lock [#channel]` lock a channel\n"
                f"`{PREFIX}unlock [#channel]` unlock a channel\n"
                f"`{PREFIX}glxstats` security statistics\n"
                f"`{PREFIX}togglespam` toggle anti spam\n"
                f"`{PREFIX}toggleinvites` toggle anti invites\n"
                f"`{PREFIX}togglementions` toggle anti mentions\n"
                f"`{PREFIX}togglenuke` toggle nuke command"
            ),
            inline=False,
        )
        embed.add_field(
            name="Community",
            value=(
                f"`{PREFIX}setsuggest #channel` set suggestion channel\n"
                f"`{PREFIX}suggest your idea` send suggestion\n"
                f"`{PREFIX}poll question | Option 1 | Option 2` quick poll\n"
                f"`{PREFIX}setwelcome #channel` set welcome channel\n"
                f"`{PREFIX}setwelcomemsg text` set welcome template\n"
                f"`{PREFIX}remindme 10m take a break` personal reminder"
            ),
            inline=False,
        )
        embed.add_field(
            name="Whitelist and Web",
            value=(
                f"`{PREFIX}glxwhitelist @member` add to whitelist\n"
                f"`{PREFIX}glxunwhitelist @member` remove from whitelist\n"
                f"`{PREFIX}generate [pattern]` generate user web key\n"
                f"`{PREFIX}genadmin [pattern]` generate admin web key (bot owner only)"
            ),
            inline=False,
        )
        embed.set_footer(text="GLX Protection • Created by AunuXdev (Creator/Developer)")
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(name="ping")
    async def ping(ctx: commands.Context):
        ms = round(bot.latency * 1000)
        await ctx.reply(f"GLX Protection latency: {ms}ms", mention_author=False)

    @bot.command(name="setsuggest")
    @commands.has_permissions(manage_guild=True)
    async def setsuggest(ctx: commands.Context, channel: discord.TextChannel):
        SUGGESTION_CHANNELS[ctx.guild.id] = channel.id
        await ctx.reply(
            f"Suggestion channel set to {channel.mention}. Members can use `{PREFIX}suggest`.",
            mention_author=False,
        )

    @bot.command(name="suggest")
    async def suggest(ctx: commands.Context, *, idea: str):
        gid = ctx.guild.id
        ch_id = SUGGESTION_CHANNELS.get(gid)
        if not ch_id:
            await ctx.reply(
                "Suggestion channel is not configured. Ask an administrator to run "
                f"`{PREFIX}setsuggest #channel`.",
                mention_author=False,
            )
            return
        channel = ctx.guild.get_channel(ch_id)
        if channel is None:
            await ctx.reply(
                "Suggestion channel cannot be found. Ask an administrator to configure it again.",
                mention_author=False,
            )
            return
        STATS["suggestions"] += 1
        GUILD_STATS[ctx.guild.id]["suggestions"] += 1
        embed = discord.Embed(
            title="New Suggestion",
            description=idea,
            colour=discord.Color.gold(),
            timestamp=datetime.utcnow(),
        )
        avatar_url = getattr(ctx.author.display_avatar, "url", None)
        if avatar_url:
            embed.set_author(name=str(ctx.author), icon_url=avatar_url)
        else:
            embed.set_author(name=str(ctx.author))
        embed.set_footer(text=f"GLX Suggestion • {ctx.guild.name}")
        msg = await channel.send(embed=embed)
        try:
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
        except Exception:
            pass
        await ctx.reply("Your suggestion has been submitted.", mention_author=False)

    @bot.command(name="poll")
    @commands.has_permissions(manage_messages=True)
    async def poll(ctx: commands.Context, *, text: str):
        parts = [p.strip() for p in text.split("|") if p.strip()]
        if len(parts) < 2:
            await ctx.reply(
                f"Usage: `{PREFIX}poll question | Option 1 | Option 2 [| Option 3 ...]`",
                mention_author=False,
            )
            return
        question = parts[0]
        options = parts[1:]
        if len(options) > 10:
            await ctx.reply("Maximum 10 options are allowed.", mention_author=False)
            return
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = []
        for index, option in enumerate(options):
            lines.append(f"{emojis[index]} {option}")
        embed = discord.Embed(
            title="Poll",
            description=question + "\n\n" + "\n".join(lines),
            colour=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text=f"Poll created by {ctx.author}")
        msg = await ctx.send(embed=embed)
        for index in range(len(options)):
            try:
                await msg.add_reaction(emojis[index])
            except Exception:
                pass
        STATS["polls"] += 1
        GUILD_STATS[ctx.guild.id]["polls"] += 1
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @bot.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def setwelcome(ctx: commands.Context, channel: discord.TextChannel):
        WELCOME_CHANNELS[ctx.guild.id] = channel.id
        await ctx.reply(
            f"Welcome channel set to {channel.mention}. New members will be greeted there.",
            mention_author=False,
        )

    @bot.command(name="setwelcomemsg")
    @commands.has_permissions(manage_guild=True)
    async def setwelcomemsg(ctx: commands.Context, *, template: str):
        WELCOME_MESSAGES[ctx.guild.id] = template
        preview = template.replace("{member}", ctx.author.mention).replace("{server}", ctx.guild.name)
        await ctx.reply(
            "Welcome message template updated.\n"
            f"Preview: {preview}",
            mention_author=False,
        )

    @bot.command(name="serverinfo")
    async def serverinfo(ctx: commands.Context):
        guild = ctx.guild
        if guild is None:
            await ctx.reply("This command can only be used inside a server.", mention_author=False)
            return
        total_members = guild.member_count or len(guild.members)
        bot_members = 0
        if guild.members:
            for member in guild.members:
                if member.bot:
                    bot_members += 1
        human_members = total_members - bot_members
        created = guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        embed = discord.Embed(
            title=f"Server Info • {guild.name}",
            colour=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        if guild.owner:
            embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Created At", value=created, inline=False)
        embed.add_field(name="Members", value=str(total_members), inline=True)
        embed.add_field(name="Humans", value=str(human_members), inline=True)
        embed.add_field(name="Bots", value=str(bot_members), inline=True)
        if guild.premium_tier:
            embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)
        icon_url = getattr(guild.icon, "url", None)
        if icon_url:
            embed.set_thumbnail(url=icon_url)
        embed.set_footer(text="GLX Protection • Server Overview")
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(name="userinfo")
    async def userinfo(ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        guild = ctx.guild
        warn_count = get_warn_count(guild.id, member.id)
        embed = discord.Embed(
            title=f"User Info • {member}",
            colour=discord.Color.teal(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        if member.joined_at:
            embed.add_field(
                name="Joined Server",
                value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                inline=False,
            )
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False,
        )
        roles = [role.mention for role in member.roles if role != guild.default_role]
        if roles:
            roles_str = ", ".join(roles)
        else:
            roles_str = "No roles"
        embed.add_field(name="Roles", value=roles_str, inline=False)
        embed.add_field(
            name="Warns",
            value=f"{warn_count}/{WARN_THRESHOLD}",
            inline=True,
        )
        avatar_url = getattr(member.display_avatar, "url", None)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="GLX Protection • User Profile")
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(name="avatar", aliases=["av"])
    async def avatar(ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        avatar_url = getattr(member.display_avatar, "url", None)
        if not avatar_url:
            await ctx.reply("Avatar is not available.", mention_author=False)
            return
        embed = discord.Embed(
            title=f"Avatar • {member}",
            colour=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text="GLX Protection • Avatar Viewer")
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(name="say")
    @commands.has_permissions(moderate_members=True)
    async def say(ctx: commands.Context, channel: discord.TextChannel = None, *, text: str):
        target = channel or ctx.channel
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await target.send(text)

    @bot.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        if seconds < 0:
            await ctx.reply("Slowmode value cannot be negative.", mention_author=False)
            return
        if seconds > 21600:
            await ctx.reply("Slowmode cannot be higher than 21600 seconds (6 hours).", mention_author=False)
            return
        try:
            await target.edit(slowmode_delay=seconds, reason=f"Slowmode updated by {ctx.author}")
        except Exception as e:
            await ctx.reply(f"Failed to update slowmode: `{e}`", mention_author=False)
            return
        if seconds == 0:
            await ctx.reply(f"Slowmode disabled for {target.mention}.", mention_author=False)
        else:
            await ctx.reply(f"Slowmode set to {seconds} seconds for {target.mention}.", mention_author=False)

    def parse_time_string(text: str) -> int:
        s = text.strip().lower()
        if not s:
            return 0
        unit = s[-1]
        value_part = s[:-1]
        if unit.isdigit():
            try:
                minutes = int(s)
                return minutes * 60
            except ValueError:
                return 0
        try:
            value = float(value_part)
        except ValueError:
            return 0
        if unit == "s":
            return int(value)
        if unit == "m":
            return int(value * 60)
        if unit == "h":
            return int(value * 3600)
        return 0

    @bot.command(name="remindme")
    async def remindme(ctx: commands.Context, time_string: str, *, text: str):
        seconds = parse_time_string(time_string)
        if seconds <= 0:
            await ctx.reply(
                "Invalid time format. Examples: `10s`, `5m`, `2h`, or just number of minutes.",
                mention_author=False,
            )
            return
        if seconds > 86400:
            await ctx.reply("Maximum reminder delay is 24 hours.", mention_author=False)
            return
        await ctx.reply(
            f"Reminder set in {time_string}. I will remind you: {text}",
            mention_author=False,
        )

        async def do_reminder():
            try:
                await asyncio.sleep(seconds)
                try:
                    await ctx.author.send(f"Reminder from {ctx.guild.name}: {text}")
                except Exception:
                    try:
                        await ctx.reply(f"Reminder: {text}", mention_author=False)
                    except Exception:
                        pass
            except Exception:
                pass

        ctx.bot.loop.create_task(do_reminder())
