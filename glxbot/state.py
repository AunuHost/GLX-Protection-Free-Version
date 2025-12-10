import logging
from datetime import datetime
from collections import defaultdict, deque

from .config import (
    ANTISPAM_ENABLED_DEFAULT,
    ANTIRAID_ENABLED_DEFAULT,
    AUTOMOD_ENABLED_DEFAULT,
    ANTIINVITES_ENABLED_DEFAULT,
    ANTIMENTIONS_ENABLED_DEFAULT,
    GLX_NUKE_ENABLED_DEFAULT,
)

logging.basicConfig(
    level=logging.INFO,
    format="[GLX] %(levelname)s: %(message)s",
)
log = logging.getLogger("GLX")

BANNER = r"""██████╗ ╚═══██╗ ██████╗    ██████╗          ██████╗  ██████╗ ███████╗
██╔══██╗ ╚══██╔╝██╔═══██╗   ██╔══██╗        ██╔══██╗██╔═══██╗██╔════╝
██████╔╝  ███╔╝ ██║   ██║   ██████╔╝        ██████╔╝██║   ██║█████╗  
██╔══██╗ ██╔══╝  ██║   ██║   ██╔══██╗        ██╔══██╗██║   ██║██╔══╝  
██████╔╝███████╗╚██████╔╝██╗██║  ██║        ██████╔╝╚██████╔╝███████╗
╚═════╝ ╚══════╝ ╚═════╝ ╚═╝╚═╝  ╚═╝        ╚═════╝  ╚═════╝ ╚══════╝

          GLX Protection • Created by AunuXdev
"""

START_TIME = datetime.utcnow()

BASE_STAT_KEYS = [
    "messages_seen",
    "spam_flags",
    "timeouts",
    "joins_seen",
    "raids_detected",
    "raid_locks",
    "bans",
    "kicks",
    "mutes",
    "automod_rules_created",
    "invites_blocked",
    "mentions_flagged",
    "nukes",
    "suggestions",
    "polls",
]

def _empty_stats():
    return {k: 0 for k in BASE_STAT_KEYS}

STATS = _empty_stats()
GUILD_STATS = defaultdict(_empty_stats)

FEATURES = {
    "anti_spam": ANTISPAM_ENABLED_DEFAULT,
    "anti_raid": ANTIRAID_ENABLED_DEFAULT,
    "automod": AUTOMOD_ENABLED_DEFAULT,
    "anti_invites": ANTIINVITES_ENABLED_DEFAULT,
    "anti_mentions": ANTIMENTIONS_ENABLED_DEFAULT,
    "nuke": GLX_NUKE_ENABLED_DEFAULT,
}

user_messages = defaultdict(lambda: deque(maxlen=50))   # spam window per user
guild_joins = defaultdict(lambda: deque(maxlen=128))    # join timestamps per guild
traffic_points = deque(maxlen=5000)                     # timestamps of messages for traffic graph

SUGGESTION_CHANNELS = {}
WELCOME_CHANNELS = {}
WELCOME_MESSAGES = {}
DEFAULT_WELCOME_TEMPLATE = "Welcome {member} to {server}!"

WHITELIST = set()

AUTOMOD_CAPACITY_WARNED_GUILDS = set()
