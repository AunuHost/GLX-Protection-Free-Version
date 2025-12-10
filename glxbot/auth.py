from datetime import datetime
import secrets
from typing import Dict, Any, Optional

from .state import log
from .config import OWNER_ID
from .security import human_delta


def normalize_code(s: str) -> str:
    if not s:
        return ""
    return "".join(ch.upper() for ch in s if ch.isalnum())


def _generate_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _random_suffix(length: int = 4) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


ACCESS_KEYS: Dict[str, Dict[str, Any]] = {}


def create_user_key(guild, author, pattern: Optional[str] = None) -> Dict[str, Any]:
    """Generate a 2FA user key bound to a single guild.

    Usage in Discord: !generate
    """
    seg1 = "GLX"
    seg2 = "USER"
    if pattern:
        parts = [p.strip() for p in pattern.split(",") if p.strip()]
        if len(parts) >= 2:
            raw1, raw2 = parts[0], parts[1]
        elif len(parts) == 1:
            raw1, raw2 = parts[0], "USER"
        else:
            raw1, raw2 = "GLX", "USER"
        s1 = "".join(ch for ch in raw1.upper() if ch.isalnum())
        s2 = "".join(ch for ch in raw2.upper() if ch.isalnum())
        seg1 = (s1 or "GLX")[:8]
        seg2 = (s2 or "USER")[:8]
    rand = _random_suffix()
    code = f"{seg1}-{seg2}-{rand}"
    norm = normalize_code(code)
    pin = _generate_pin()
    rec = {
        "display_code": code,
        "type": "user",
        "guild_id": guild.id,
        "guild_name": guild.name,
        "owner_id": author.id,
        "owner_tag": str(author),
        "pin": pin,
        "created_at": datetime.utcnow(),
    }
    ACCESS_KEYS[norm] = rec
    log.info("[GLX] Generated USER web key for %s in guild %s", author, guild.name)
    return rec


def create_admin_key(author, pattern: Optional[str] = None) -> Dict[str, Any]:
    """Generate a 2FA admin key (can see ALL servers + admin panel).

    Only OWNER_ID from .env can call this via !genadmin.
    """
    if OWNER_ID == 0:
        raise PermissionError("OWNER_ID is not configured in environment.")
    if author.id != OWNER_ID:
        raise PermissionError("Only the configured OWNER_ID can generate an admin key.")
    seg1 = "GLX"
    seg2 = "ADMIN"
    if pattern:
        parts = [p.strip() for p in pattern.split(",") if p.strip()]
        if len(parts) >= 2:
            raw1, raw2 = parts[0], parts[1]
        elif len(parts) == 1:
            raw1, raw2 = parts[0], "ADMIN"
        else:
            raw1, raw2 = "GLX", "ADMIN"
        s1 = "".join(ch for ch in raw1.upper() if ch.isalnum())
        s2 = "".join(ch for ch in raw2.upper() if ch.isalnum())
        seg1 = (s1 or "GLX")[:8]
        seg2 = (s2 or "ADMIN")[:8]
    rand = _random_suffix()
    code = f"{seg1}-{seg2}-{rand}"
    norm = normalize_code(code)
    pin = _generate_pin()
    rec = {
        "display_code": code,
        "type": "admin",
        "guild_id": None,
        "guild_name": None,
        "owner_id": author.id,
        "owner_tag": str(author),
        "pin": pin,
        "created_at": datetime.utcnow(),
    }
    ACCESS_KEYS[norm] = rec
    log.info("[GLX] Generated ADMIN web key for %s", author)
    return rec


def validate_credentials(key: str, pin: str) -> Dict[str, Any]:
    """Validate (code + PIN) – if invalid, lock the dashboard (no data)."""
    if not key or not pin:
        return {"valid": False, "locked": True, "role": None, "guild_id": None, "owner_id": None}
    if not ACCESS_KEYS:
        return {"valid": False, "locked": True, "role": None, "guild_id": None, "owner_id": None}
    norm = normalize_code(key)
    rec = ACCESS_KEYS.get(norm)
    if not rec:
        return {"valid": False, "locked": True, "role": None, "guild_id": None, "owner_id": None}
    if pin.strip() != rec.get("pin"):
        return {"valid": False, "locked": True, "role": None, "guild_id": None, "owner_id": None}
    return {
        "valid": True,
        "locked": False,
        "role": rec.get("type"),
        "guild_id": rec.get("guild_id"),
        "owner_id": rec.get("owner_id"),
        "display_code": rec.get("display_code"),
    }


def get_license_info() -> Dict[str, Any]:
    """Summarized info for dashboard (credit + last key info)."""
    if not ACCESS_KEYS:
        return {
            "type": "No web keys",
            "code_active": False,
            "code_masked": None,
            "created_ago": None,
            "created_at": None,
            "created_by": None,
            "guild_name": None,
        }
    items = list(ACCESS_KEYS.values())
    admin_count = sum(1 for r in items if r.get("type") == "admin")
    user_count = sum(1 for r in items if r.get("type") == "user")
    latest = max(items, key=lambda r: r.get("created_at") or datetime.utcnow())
    created_at = latest.get("created_at")
    if created_at:
        age = human_delta(datetime.utcnow() - created_at)
        created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        age = None
        created_at_str = None
    code_str = f"{len(items)} keys (admin {admin_count}, user {user_count})"
    return {
        "type": "Lifetime Multi-Key",
        "code_active": True,
        "code_masked": code_str,
        "created_ago": age,
        "created_at": created_at_str,
        "created_by": latest.get("owner_tag"),
        "guild_name": latest.get("guild_name"),
    }
