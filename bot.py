import asyncio

from aiohttp import web

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()

from glxbot.config import DISCORD_TOKEN, GLX_WEB_HOST, GLX_WEB_PORT
from glxbot.state import log
from glxbot.core import create_bot
from glxweb.app import create_web_app


async def main():
    if not DISCORD_TOKEN or DISCORD_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise SystemExit("Please set DISCORD_TOKEN in environment or .env")

    bot = create_bot()
    app = create_web_app(bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, GLX_WEB_HOST, GLX_WEB_PORT)
    await site.start()
    log.info("[GLX] Web dashboard running at http://%s:%s", GLX_WEB_HOST, GLX_WEB_PORT)

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
