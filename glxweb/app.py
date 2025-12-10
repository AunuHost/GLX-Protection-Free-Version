import time
from datetime import datetime, timedelta

from aiohttp import web

from glxbot.config import PREFIX
from glxbot.state import STATS, GUILD_STATS, traffic_points, FEATURES
from glxbot.security import uptime_str
from glxbot.auth import validate_credentials, get_license_info


def build_traffic_series():
    """Build a simple traffic graph data over the last 5 minutes (message timestamps)."""
    now = time.time()
    window = 5 * 60.0
    start = now - window

    while traffic_points and traffic_points[0] < start - 60:
        traffic_points.popleft()

    start_utc = datetime.utcfromtimestamp(start)
    end_utc = datetime.utcfromtimestamp(now)
    start_jkt = start_utc + timedelta(hours=7)
    end_jkt = end_utc + timedelta(hours=7)

    if not traffic_points:
        return {
            "counts": [],
            "labels": [],
            "window_start_utc": start_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "window_end_utc": end_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "window_start_jakarta": start_jkt.strftime("%Y-%m-%d %H:%M:%S"),
            "window_end_jakarta": end_jkt.strftime("%Y-%m-%d %H:%M:%S"),
        }

    buckets = 30
    step = window / buckets
    counts = [0 for _ in range(buckets)]
    for ts in traffic_points:
        if ts < start:
            continue
        idx = int((ts - start) // step)
        if 0 <= idx < buckets:
            counts[idx] += 1

    labels = []
    for i in range(buckets):
        t = start + i * step
        t_jkt = datetime.utcfromtimestamp(t) + timedelta(hours=7)
        labels.append(t_jkt.strftime("%H:%M"))

    return {
        "counts": counts,
        "labels": labels,
        "window_start_utc": start_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "window_end_utc": end_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "window_start_jakarta": start_jkt.strftime("%Y-%m-%d %H:%M:%S"),
        "window_end_jakarta": end_jkt.strftime("%Y-%m-%d %H:%M:%S"),
    }


def collect_stats(bot, role: str, scope_guild_id=None):
    """Collect stats for dashboard.

    - role == 'user' -> only scope_guild_id (single server view)
    - role == 'admin' -> global view for ALL servers
    - None / invalid -> generic global stats without server detail
    """
    guilds = list(bot.guilds)

    now_utc = datetime.utcnow()
    now_jkt = now_utc + timedelta(hours=7)

    license_info = get_license_info()

    if role == "user" and scope_guild_id is not None:
        target = next((g for g in guilds if g.id == scope_guild_id), None)
        if target:
            members = target.member_count or (len(target.members) if target.members else 0)
            bot_count = 0
            if target.members:
                for m in target.members:
                    if m.bot:
                        bot_count += 1
            guilds_detail = [{
                "id": target.id,
                "name": target.name,
                "members": members,
                "bots": bot_count,
            }]
            stats = GUILD_STATS[target.id]
            data = {
                "uptime": uptime_str(),
                "prefix": PREFIX,
                "guilds": 1,
                "members": members,
                "bots": bot_count,
                "stats": stats,
                "features": FEATURES,
                "traffic": build_traffic_series(),
                "license": license_info,
                "time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "time_jakarta": now_jkt.strftime("%Y-%m-%d %H:%M:%S Asia/Jakarta (UTC+7)"),
                "guilds_detail": guilds_detail,
            }
            return data

    total_members = sum(g.member_count or 0 for g in guilds)
    total_bots = 0
    guilds_detail = []
    for g in guilds:
        bot_count = 0
        if g.members:
            for m in g.members:
                if m.bot:
                    bot_count += 1
        total_bots += bot_count
        members = g.member_count or (len(g.members) if g.members else 0)
        guilds_detail.append({
            "id": g.id,
            "name": g.name,
            "members": members,
            "bots": bot_count,
        })

    data = {
        "uptime": uptime_str(),
        "prefix": PREFIX,
        "guilds": len(guilds),
        "members": total_members,
        "bots": total_bots,
        "stats": STATS,
        "features": FEATURES,
        "traffic": build_traffic_series(),
        "license": license_info,
        "time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "time_jakarta": now_jkt.strftime("%Y-%m-%d %H:%M:%S Asia/Jakarta (UTC+7)"),
        "guilds_detail": guilds_detail,
    }
    return data


def create_web_app(bot):
    routes = web.RouteTableDef()

    index_html_path = (__file__.rsplit("/", 1)[0] or ".") + "/templates/index.html"
    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    @routes.get("/")
    async def index(request):
        return web.Response(text=index_html, content_type="text/html")

    @routes.get("/api/stats")
    async def api_stats(request):
        key = request.query.get("key") or ""
        pin = request.query.get("pin") or ""
        cred = validate_credentials(key, pin)
        role = cred.get("role")
        scope_gid = cred.get("guild_id")
        data = collect_stats(bot, role, scope_gid)
        data["locked"] = not cred.get("valid", False)
        data["role"] = role
        return web.json_response(data)

    @routes.post("/api/toggle")
    async def api_toggle(request):
        key = request.query.get("key") or ""
        pin = request.query.get("pin") or ""
        cred = validate_credentials(key, pin)
        if not cred.get("valid"):
            return web.json_response({"ok": False, "locked": True, "error": "access_denied"}, status=403)
        try:
            payload = await request.json()
            feat_key = payload.get("key")
            value = bool(payload.get("value"))
        except Exception:
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)
        if feat_key not in FEATURES:
            return web.json_response({"ok": False, "error": "unknown_feature"}, status=400)
        FEATURES[feat_key] = value
        return web.json_response({"ok": True, "feature": feat_key, "value": value})

    @routes.post("/api/sync_automod")
    async def api_sync_automod(request):
        from glxbot.automod_sync import sync_automod

        key = request.query.get("key") or ""
        pin = request.query.get("pin") or ""
        cred = validate_credentials(key, pin)
        if not cred.get("valid"):
            return web.json_response({"ok": False, "locked": True, "error": "access_denied"}, status=403)
        if cred.get("role") != "admin":
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)
        if not bot.guilds:
            return web.json_response({"ok": False, "error": "no_guilds"}, status=400)
        for guild in bot.guilds:
            bot.loop.create_task(sync_automod(bot, guild, FEATURES))
        return web.json_response({"ok": True})

    @routes.post("/api/admin/leave_guild")
    async def api_admin_leave_guild(request):
        key = request.query.get("key") or ""
        pin = request.query.get("pin") or ""
        cred = validate_credentials(key, pin)
        if not cred.get("valid"):
            return web.json_response({"ok": False, "locked": True, "error": "access_denied"}, status=403)
        if cred.get("role") != "admin":
            return web.json_response({"ok": False, "error": "admin_only"}, status=403)
        try:
            payload = await request.json()
            gid = int(payload.get("guild_id"))
        except Exception:
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)
        guild = next((g for g in bot.guilds if g.id == gid), None)
        if guild is None:
            return web.json_response({"ok": False, "error": "guild_not_found"}, status=404)
        try:
            await guild.leave()
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)
        return web.json_response({"ok": True})

    app = web.Application()
    app.add_routes(routes)
    return app
