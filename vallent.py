"""
VALLENT EXS — Discord Moderation Bot
Author  : Niks. (Founder)
Version : 1.0.0

"No mercy. No limits. Full control."

Features:
  - Full moderation suite (kick, ban, timeout, warn, purge, lock, slowmode, etc.)
  - No-prefix command system (owner + premium users)
  - Bot role hierarchy: Founder > Developer > Management > Staff
  - Profile card with badges
  - XP leveling + rank card (image)
  - Giveaway system with winner role auto-assign
  - Ticket system
  - Honeypot anti-spam channel (auto-ban)
  - Premium system with expiry
  - Multi-language support
  - Owner supreme — overrides all permission checks
"""

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import re
import asyncio
import datetime
import logging
import pytz
from collections import defaultdict
from typing import Optional

logging.basicConfig(level=logging.INFO)

from emoji_config import (
    BADGE_FOUNDER, BADGE_DEVELOPER, BADGE_MANAGEMENT, BADGE_STAFF,
    BADGE_PREMIUM, BADGE_NOPREFIX, BADGE_USER, BADGE_MODERATOR, BADGE_SERVER_MANAGER,
    ICON_MODERATION, ICON_ROLE, ICON_INFO, ICON_TICKET, ICON_LEVEL,
    ICON_GIVEAWAY, ICON_ANTISPAM, ICON_LANGUAGE, ICON_OWNER,
    ICON_SUCCESS, ICON_ERROR, ICON_WARNING, ICON_LOADING,
    ICON_PROFILE, ICON_BADGES, ICON_COMMANDS, ICON_PREMIUM_TAG,
    ICON_TICKET_OPEN, ICON_TICKET_CLOSE, ICON_GIVEAWAY_REACT, ICON_WINNER,
    ICON_BOOST, ICON_ANTINUKE,
    e
)
import rank_card
import antinuke


# ══════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════

BOT_NAME      = "VALLENT EXS"
BOT_TAGLINE   = "Nocturne Development."
BOT_VERSION   = "1.0.0"
BOT_PREFIX    = "!vx "
CONFIG_PATH   = "data/config.json"
WIB           = pytz.timezone("Asia/Jakarta")

# Dark red palette
COLOR_PRIMARY = 0x8B0000   # Dark red
COLOR_SUCCESS = 0x22C55E   # Green
COLOR_ERROR   = 0xEF4444   # Red
COLOR_WARNING = 0xF59E0B   # Amber
COLOR_INFO    = 0xDC143C   # Crimson

# Support server invite link — set via env var SUPPORT_INVITE
SUPPORT_INVITE = os.getenv("SUPPORT_INVITE", "")

SPAM_THRESHOLD = 3
SPAM_WINDOW    = 8.0

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

def load_config() -> dict:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        default = {
            "guilds":            {},
            "premium_users":     [],
            "premium_guilds":    [],
            "premium_commands":  [],
            "premium_expiry":    {},
            "no_prefix_users":   [],
            "no_prefix_guilds":  [],
            "no_prefix_expiry":  {},
            "bot_roles":         {},
            "role_sync":         {},
            "votes":             {},
            "payment_methods": {
                "qris":    {"enabled": True, "image_url": "", "info": ""},
                "bank":    {"enabled": True, "bank_name": "", "account_number": "", "account_name": ""},
                "ewallet": {"enabled": True, "type": "", "number": ""},
            }
        }
        save_config(default)
        return default
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("guilds",           {})
    data.setdefault("premium_users",    [])
    data.setdefault("premium_guilds",   [])
    data.setdefault("premium_commands", [])
    data.setdefault("premium_expiry",   {})
    data.setdefault("no_prefix_users",  [])
    data.setdefault("no_prefix_guilds", [])
    data.setdefault("no_prefix_expiry", {})
    data.setdefault("bot_roles",        {})
    data.setdefault("role_sync",        {})
    data.setdefault("votes",            {})
    data.setdefault("support_server_members", [])  # user IDs yang sudah join support server
    data.setdefault("commands_run",           {})  # uid → jumlah command dijalankan
    data.setdefault("xp_boost",                {})  # uid(str) -> {"expiry": iso, "multiplier": float}
    data.setdefault("maintenance", {"enabled": False, "reason": "", "since": None})
    for gid, gc in data.get("guilds", {}).items():
        _init_guild(gc)
    save_config(data)
    return data

def _init_guild(gc: dict):
    gc.setdefault("language",          "en")
    gc.setdefault("main_channel",      None)
    gc.setdefault("announce_channel",  None)
    gc.setdefault("level_channel",     None)
    gc.setdefault("levelup_message",   "{mention} leveled up to **Level {level}**!")
    gc.setdefault("spam_trap_channel", None)
    gc.setdefault("leveling_enabled",  True)
    gc.setdefault("xp_per_message",    [15, 25])
    gc.setdefault("xp_cooldown",       60)
    gc.setdefault("members_xp",        {})
    gc.setdefault("level_roles",       {})
    gc.setdefault("warnings",          {})
    gc.setdefault("boost", {
        "channel":     None,
        "title":       "New Server Boost!",
        "emoji":       e(ICON_BOOST, "🎉"),
        "description": "{mention} just boosted **{server}**! Thanks for the support 💜",
    })
    gc["boost"].setdefault("channel",     None)
    gc["boost"].setdefault("title",       "New Server Boost!")
    gc["boost"].setdefault("emoji",       e(ICON_BOOST, "🎉"))
    gc["boost"].setdefault("description", "{mention} just boosted **{server}**! Thanks for the support 💜")
    gc.setdefault("active_tickets",    {})   # uid(str) -> [{"channel_id","panel_id","opened_at"}, ...]
    gc.setdefault("mod_log_channel",   None)
    gc.setdefault("antinuke", {
        "enabled":     False,
        "log_channel": None,
        "whitelist":   [],
        "punishment":  "strip_roles",
    })
    gc["antinuke"].setdefault("enabled",     False)
    gc["antinuke"].setdefault("log_channel", None)
    gc["antinuke"].setdefault("whitelist",   [])
    gc["antinuke"].setdefault("punishment",  "strip_roles")
    gc.setdefault("ticket", {"panels": {}})
    gc["ticket"].setdefault("panels", {})
    # Migrasi struktur ticket lama (single-config, panels sebagai list) ke multi-panel dict.
    legacy_cat  = gc["ticket"].pop("category",     None) if "category"     in gc["ticket"] else None
    legacy_log  = gc["ticket"].pop("log_channel",  None) if "log_channel"  in gc["ticket"] else None
    legacy_role = gc["ticket"].pop("support_role", None) if "support_role" in gc["ticket"] else None
    legacy_max  = gc["ticket"].pop("max_tickets",  None) if "max_tickets"  in gc["ticket"] else None
    if isinstance(gc["ticket"].get("panels"), list):
        gc["ticket"]["panels"] = {}
    if legacy_cat and "default" not in gc["ticket"]["panels"]:
        gc["ticket"]["panels"]["default"] = {
            "category":     legacy_cat,
            "log_channel":  legacy_log,
            "support_role": legacy_role,
            "max_tickets":  legacy_max or 1,
            "title":        "Support Tickets",
            "description":  "Klik tombol untuk membuka support ticket.",
            "message_id":   None,
            "channel_id":   None,
        }
    for p in gc["ticket"]["panels"].values():
        p.setdefault("category",     None)
        p.setdefault("log_channel",  None)
        p.setdefault("support_role", None)
        p.setdefault("max_tickets",  1)
        p.setdefault("title",        "Support Tickets")
        p.setdefault("description",  "Klik tombol untuk membuka support ticket.")
        p.setdefault("message_id",   None)
        p.setdefault("channel_id",   None)
    # Migrasi active_tickets lama (uid -> single channel_id int) ke format baru (uid -> list).
    for uid, val in list(gc["active_tickets"].items()):
        if isinstance(val, int):
            gc["active_tickets"][uid] = [{"channel_id": val, "panel_id": "default", "opened_at": None}]

def save_config(cfg: dict):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def guild_cfg(cfg: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in cfg["guilds"]:
        cfg["guilds"][gid] = {}
        _init_guild(cfg["guilds"][gid])
        save_config(cfg)
    gc = cfg["guilds"][gid]
    _init_guild(gc)
    return gc

# ══════════════════════════════════════════════════════════════════
# LANGUAGE
# ══════════════════════════════════════════════════════════════════

LANGUAGES = {
    "en": "English", "id": "Indonesian", "de": "German",
    "ar": "Arabic",  "th": "Thai",       "vi": "Vietnamese",
    "ja": "Japanese","ko": "Korean",
}

STRINGS = {
    "en": {
        "no_perm":         "You do not have permission to use this command.",
        "kick_success":    "{user} has been kicked. Reason: {reason}",
        "ban_success":     "{user} has been banned. Reason: {reason}",
        "timeout_success": "{user} has been timed out for {duration} minutes.",
        "warn_success":    "{user} has been warned. Reason: {reason}",
        "role_add":        "Role {role} added to {user}.",
        "role_remove":     "Role {role} removed from {user}.",
        "move_success":    "{user} moved to {channel}.",
        "emoji_add":       "Emoji {name} added.",
        "ticket_open":     "Your ticket has been created: {channel}",
        "ticket_exists":   "You already have an open ticket.",
        "lang_set":        "Language set to {lang}.",
    },
    "id": {
        "no_perm":         "Kamu tidak memiliki izin untuk menggunakan perintah ini.",
        "kick_success":    "{user} telah dikick. Alasan: {reason}",
        "ban_success":     "{user} telah diban. Alasan: {reason}",
        "timeout_success": "{user} telah di-timeout selama {duration} menit.",
        "warn_success":    "{user} telah diperingatkan. Alasan: {reason}",
        "role_add":        "Peran {role} ditambahkan ke {user}.",
        "role_remove":     "Peran {role} dihapus dari {user}.",
        "move_success":    "{user} dipindahkan ke {channel}.",
        "emoji_add":       "Emoji {name} berhasil ditambahkan.",
        "ticket_open":     "Tiket kamu telah dibuat: {channel}",
        "ticket_exists":   "Kamu sudah memiliki tiket yang terbuka.",
        "lang_set":        "Bahasa diatur ke {lang}.",
    },
}

def t(cfg: dict, guild_id: int, key: str, **kwargs) -> str:
    gc   = guild_cfg(cfg, guild_id)
    lang = gc.get("language", "en")
    s    = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
    return s.format(**kwargs)

# ══════════════════════════════════════════════════════════════════
# EMBED HELPERS
# ══════════════════════════════════════════════════════════════════

def _footer(embed: discord.Embed):
    embed.set_footer(text=f"{BOT_NAME} • {BOT_TAGLINE}")
    embed.timestamp = discord.utils.utcnow()
    return embed

def _title_with_icon(icon: str, fallback: str, text: str) -> str:
    ic = e(icon, fallback) if icon else fallback
    return f"{ic} {text}" if ic else text

def base_embed(title: str, description: str = "", color: int = COLOR_PRIMARY) -> discord.Embed:
    return _footer(discord.Embed(title=title, description=description, color=color))

def success_embed(desc: str) -> discord.Embed:
    return base_embed(_title_with_icon(ICON_SUCCESS, "✅", "Success"), desc, COLOR_SUCCESS)

def error_embed(desc: str) -> discord.Embed:
    return base_embed(_title_with_icon(ICON_ERROR, "❌", "Error"), desc, COLOR_ERROR)

def warning_embed(title: str, desc: str) -> discord.Embed:
    return base_embed(_title_with_icon(ICON_WARNING, "⚠️", title), desc, COLOR_WARNING)

def info_embed(title: str, desc: str) -> discord.Embed:
    return base_embed(_title_with_icon(ICON_INFO, "ℹ️", title), desc, COLOR_INFO)

# ══════════════════════════════════════════════════════════════════
# XP / LEVELING
# ══════════════════════════════════════════════════════════════════

def xp_for_level(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100

def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
    return level

def xp_progress(total_xp: int):
    level = 0
    xp    = total_xp
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
    return level, xp, xp_for_level(level)

def get_member_xp(gc: dict, uid: str) -> dict:
    data = gc["members_xp"].setdefault(uid, {"xp": 0, "level": 0, "last_msg_ts": 0.0, "messages": 0})
    data.setdefault("messages", 0)
    return data

async def apply_level_roles(guild: discord.Guild, member: discord.Member, gc: dict, new_level: int) -> list:
    """Kasih semua role reward yang levelnya <= new_level dan belum dimiliki member
    (stacking — sekali dapat, role sebelumnya gak dicabut). Return list role yang
    baru aja diberikan (buat ditampilin di notifikasi level up)."""
    level_roles = gc.get("level_roles", {})
    if not level_roles:
        return []
    granted = []
    for lvl_str, role_id in level_roles.items():
        try:
            lvl = int(lvl_str)
        except ValueError:
            continue
        if lvl > new_level:
            continue
        role = guild.get_role(role_id)
        if not role or role in member.roles:
            continue
        try:
            await member.add_roles(role, reason=f"Level role reward — mencapai level {lvl}")
            granted.append(role)
        except Exception as e:
            logging.error(f"[{BOT_NAME}] Gagal kasih level role {role_id} ke {member.id}: {e}")
    return granted

# ══════════════════════════════════════════════════════════════════
# BOT SETUP
# ══════════════════════════════════════════════════════════════════

intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.guilds          = True

cfg = load_config()

ORIGINAL_CMD_DESCRIPTIONS: dict[str, str] = {}

class VallentTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        data = getattr(interaction, "data", None)
        if not data:
            return True
        # Hanya proses pemanggilan slash command sungguhan — biarkan
        # autocomplete dan tipe interaksi lain lewat tanpa disentuh.
        if interaction.type != discord.InteractionType.application_command or data.get("type", 1) != 1:
            return True

        parts   = [data.get("name", "")]
        options = data.get("options", [])
        while options:
            opt = options[0]
            if opt.get("type") in (1, 2):
                parts.append(opt["name"])
                options = opt.get("options", [])
            else:
                break
        cmd_name  = " ".join(parts)
        is_owner_ = interaction.user.id == bot.owner_id

        # ── Maintenance mode — cuma owner yang bisa lewat ──────────────
        if is_maintenance_on() and not is_owner_:
            m = cfg.get("maintenance", {})
            desc = f"**{BOT_NAME}** lagi maintenance, coba lagi nanti."
            if m.get("reason"):
                desc += f"\n\n**Alasan:** {m['reason']}"
            try:
                await interaction.response.send_message(
                    embed=warning_embed("Under Maintenance", desc), ephemeral=True)
            except discord.InteractionResponded:
                pass
            return False

        # ── Premium-locked command ──────────────────────────────────────
        if cmd_name in cfg.get("premium_commands", []) and not is_owner_ and not user_has_premium(interaction.guild, interaction.user):
            try:
                await interaction.response.send_message(
                    embed=warning_embed(
                        "Premium Required",
                        f"Command `/{cmd_name}` hanya untuk **Premium** users.\n"
                        "Hubungi owner atau kunjungi server support untuk berlangganan."
                    ), ephemeral=True)
            except discord.InteractionResponded:
                pass
            return False

        # ── Command usage counter ───────────────────────────────────────
        cmds_run = cfg.setdefault("commands_run", {})
        uid_str  = str(interaction.user.id)
        cmds_run[uid_str] = cmds_run.get(uid_str, 0) + 1
        save_config(cfg)

        return True

bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
    owner_id=int(os.getenv("OWNER_ID", "0")),
    tree_cls=VallentTree,
)

# ══════════════════════════════════════════════════════════════════
# PREMIUM HELPERS
# ══════════════════════════════════════════════════════════════════

def user_has_premium(guild: Optional[discord.Guild], user: discord.abc.User) -> bool:
    uid        = str(user.id)
    expiry_map = cfg.get("premium_expiry", {})
    if user.id in cfg.get("premium_users", []):
        expiry_str = expiry_map.get(uid)
        if expiry_str:
            try:
                exp = datetime.datetime.fromisoformat(expiry_str)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                if datetime.datetime.now(datetime.timezone.utc) > exp:
                    cfg["premium_users"] = [u for u in cfg["premium_users"] if u != user.id]
                    cfg["premium_expiry"].pop(uid, None)
                    save_config(cfg)
                    return False
            except Exception:
                pass
        return True
    if guild and guild.id in cfg.get("premium_guilds", []):
        return True
    return False

async def check_premium_expiry():
    now        = datetime.datetime.now(datetime.timezone.utc)
    expiry_map = cfg.get("premium_expiry", {})
    revoked    = []
    for uid_str, expiry_str in list(expiry_map.items()):
        try:
            exp = datetime.datetime.fromisoformat(expiry_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.timezone.utc)
            if now > exp:
                uid = int(uid_str)
                cfg["premium_users"] = [u for u in cfg.get("premium_users", []) if u != uid]
                expiry_map.pop(uid_str, None)
                revoked.append(uid)
        except Exception:
            pass
    if revoked:
        save_config(cfg)
        logging.info(f"[Premium] Expired and revoked: {revoked}")
        for uid in revoked:
            try:
                user = bot.get_user(uid) or await bot.fetch_user(uid)
                await user.send(embed=base_embed(
                    "Premium Berakhir",
                    f"Masa aktif Premium kamu di **{BOT_NAME}** sudah habis.\n"
                    "Semua command premium dan akses no-prefix sudah dinonaktifkan.\n"
                    "Hubungi owner kalau mau perpanjang.",
                    color=COLOR_ERROR
                ))
            except Exception:
                pass

def user_has_no_prefix(guild: Optional[discord.Guild], user: discord.abc.User) -> bool:
    """No-prefix aktif untuk: owner, user yang di-grant manual (dengan/tanpa durasi),
    guild yang di-grant, atau siapapun yang lagi Premium (Premium otomatis membuka no-prefix)."""
    if user.id == bot.owner_id:
        return True
    if user.id in cfg.get("no_prefix_users", []):
        uid_str    = str(user.id)
        expiry_str = cfg.get("no_prefix_expiry", {}).get(uid_str)
        if expiry_str:
            try:
                exp = datetime.datetime.fromisoformat(expiry_str)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                if datetime.datetime.now(datetime.timezone.utc) > exp:
                    cfg["no_prefix_users"] = [u for u in cfg["no_prefix_users"] if u != user.id]
                    cfg.get("no_prefix_expiry", {}).pop(uid_str, None)
                    save_config(cfg)
                    return user_has_premium(guild, user)
            except Exception:
                pass
        return True
    if guild and guild.id in cfg.get("no_prefix_guilds", []):
        return True
    return user_has_premium(guild, user)

async def check_no_prefix_expiry():
    now        = datetime.datetime.now(datetime.timezone.utc)
    expiry_map = cfg.get("no_prefix_expiry", {})
    revoked    = []
    for uid_str, expiry_str in list(expiry_map.items()):
        try:
            exp = datetime.datetime.fromisoformat(expiry_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.timezone.utc)
            if now > exp:
                uid = int(uid_str)
                cfg["no_prefix_users"] = [u for u in cfg.get("no_prefix_users", []) if u != uid]
                expiry_map.pop(uid_str, None)
                revoked.append(uid)
        except Exception:
            pass
    if revoked:
        save_config(cfg)
        logging.info(f"[No-Prefix] Expired and revoked: {revoked}")
        for uid in revoked:
            try:
                user = bot.get_user(uid) or await bot.fetch_user(uid)
                await user.send(embed=base_embed(
                    "No-Prefix Berakhir",
                    f"Akses no-prefix kamu di **{BOT_NAME}** sudah habis.\n"
                    "Sekarang command harus pakai prefix `!vx` lagi.\n"
                    "Hubungi owner kalau mau perpanjang.",
                    color=COLOR_ERROR
                ))
            except Exception:
                pass

def is_maintenance_on() -> bool:
    return bool(cfg.get("maintenance", {}).get("enabled", False))

def grant_xp_boost(uid: int, minutes: int = 60, multiplier: float = 1.10):
    """Kasih boost XP sementara — dipakai sebagai insentif join support server.
    Berlaku di SEMUA guild (bukan per-guild) karena ini reward personal, bukan
    setting server."""
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
    cfg.setdefault("xp_boost", {})[str(uid)] = {"expiry": expiry.isoformat(), "multiplier": multiplier}
    save_config(cfg)

def get_xp_multiplier(uid: int) -> float:
    """Return pengali XP aktif untuk user (1.0 kalau gak ada boost / udah expired).
    Expired entry dibersihkan otomatis (lazy cleanup, sama pola kayak premium)."""
    boosts  = cfg.setdefault("xp_boost", {})
    uid_str = str(uid)
    entry   = boosts.get(uid_str)
    if not entry:
        return 1.0
    try:
        exp = datetime.datetime.fromisoformat(entry["expiry"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        if datetime.datetime.now(datetime.timezone.utc) > exp:
            boosts.pop(uid_str, None)
            save_config(cfg)
            return 1.0
        return float(entry.get("multiplier", 1.0))
    except Exception:
        boosts.pop(uid_str, None)
        return 1.0

def xp_boost_remaining(uid: int) -> Optional[datetime.datetime]:
    """Return waktu expiry boost yang masih aktif, atau None kalau gak ada."""
    entry = cfg.get("xp_boost", {}).get(str(uid))
    if not entry:
        return None
    try:
        exp = datetime.datetime.fromisoformat(entry["expiry"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        return exp if exp > datetime.datetime.now(datetime.timezone.utc) else None
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════
# BOT ROLES SYSTEM
# ══════════════════════════════════════════════════════════════════

BOT_ROLE_HIERARCHY = ["staff", "moderator", "server_manager", "management", "developer", "founder"]

BOT_ROLE_BADGES = {
    # Emoji diambil dari emoji_config.py — edit file itu untuk isi ID emoji
    "founder":        {"label": "• FOUNDER",        "color": 0x8B0000, "emoji": BADGE_FOUNDER},
    "developer":      {"label": "• Developer",      "color": 0xDC143C, "emoji": BADGE_DEVELOPER},
    "management":     {"label": "• Management",     "color": 0xB22222, "emoji": BADGE_MANAGEMENT},
    "server_manager": {"label": "• Server Manager", "color": 0xE67E22, "emoji": e(BADGE_SERVER_MANAGER, "🗂️")},
    "moderator":      {"label": "• Moderator",      "color": 0xC97C3D, "emoji": e(BADGE_MODERATOR, "🛡️")},
    "staff":          {"label": "• Staff",          "color": 0xCD5C5C, "emoji": BADGE_STAFF},
    "premium":        {"label": "• Premium",        "color": 0xF59E0B, "emoji": BADGE_PREMIUM},
    "noprefix":       {"label": "• NO PREFIX",      "color": 0x22C55E, "emoji": BADGE_NOPREFIX},
    "user":           {"label": "• User",           "color": 0x6B7280, "emoji": BADGE_USER},
}

def get_support_guild() -> Optional[discord.Guild]:
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    return bot.get_guild(support_server_id) if support_server_id else None

def get_synced_role(uid: int) -> Optional[str]:
    """Cek role Discord asli user di support server, cocokin ke role_sync mapping.
    Dicek dari yang tertinggi (founder) ke terendah (staff) — kalau punya beberapa
    role yang disync, badge tertinggi yang menang."""
    guild = get_support_guild()
    if not guild:
        return None
    member = guild.get_member(uid)
    if not member:
        return None
    role_sync = cfg.get("role_sync", {})
    for tier in reversed(BOT_ROLE_HIERARCHY):  # founder → developer → management → staff
        role_id = role_sync.get(tier)
        if role_id and any(r.id == role_id for r in member.roles):
            return tier
    return None

def get_bot_role(uid: int) -> str:
    if uid == bot.owner_id:
        return "founder"
    synced = get_synced_role(uid)
    if synced:
        return synced
    return cfg.get("bot_roles", {}).get(str(uid), "user")

def get_user_badges(uid: int) -> list:
    """
    Kumpulkan semua badge user.
    Hierarki: founder > developer > management > staff > noprefix > premium > user
    Badge USER hanya didapat kalau user join server support bot.
    Kalau tidak punya badge apapun → list kosong.
    """
    badges  = []
    role    = get_bot_role(uid)
    is_prem = uid in cfg.get("premium_users", [])
    if role != "user":
        badges.append(role)
    if uid in cfg.get("no_prefix_users", []) or is_prem:
        badges.append("noprefix")
    if is_prem:
        badges.append("premium")
    if uid in cfg.get("support_server_members", []):
        badges.append("user")
    # Tidak ada default badge — kalau kosong ya kosong
    return badges

def build_profile_embed(user: discord.abc.User) -> discord.Embed:
    uid        = user.id
    role       = get_bot_role(uid)
    badges     = get_user_badges(uid)
    expiry_map = cfg.get("premium_expiry", {})
    has_prem   = uid in cfg.get("premium_users", [])
    cmds_run   = cfg.get("commands_run", {}).get(str(uid), 0)
    top        = role if role != "user" else (badges[0] if badges else "user")
    color      = BOT_ROLE_BADGES.get(top, BOT_ROLE_BADGES["user"])["color"]

    profile_icon = e(ICON_PROFILE, "🪪")
    embed = discord.Embed(title=f"{profile_icon} {user.display_name}'s Profile".strip(), color=color)
    embed.set_thumbnail(url=user.display_avatar.url)

    # ── ALL BADGES — field sendiri, satu badge per baris ──────────────
    if badges:
        badge_lines = []
        for b in badges:
            info      = BOT_ROLE_BADGES.get(b, BOT_ROLE_BADGES["user"])
            emoji_str = info.get("emoji", "")
            prefix    = (emoji_str + " ") if emoji_str else "\u2022 "
            badge_lines.append(prefix + "**" + info["label"] + "**")
        badges_value = "\n".join(badge_lines)
    else:
        invite = SUPPORT_INVITE
        badges_value = "Belum ada badge."
        if invite:
            badges_value += "\n[Join server support](" + invite + ") untuk dapat badge **USER**!"
        else:
            badges_value += "\nJoin server support untuk dapat badge **USER**!"

    badges_icon = e(ICON_BADGES, "✨")
    embed.add_field(name=f"{badges_icon} __ALL BADGES__".strip(), value=badges_value, inline=False)

    # ── Total Badges & Commands Runned — dua field sejajar ────────────
    embed.add_field(name="Total Badges", value="**" + str(len(badges)) + "**", inline=True)
    embed.add_field(name=f"{e(ICON_COMMANDS, '⚙️')} Commands Runned".strip(), value="**" + str(cmds_run) + "**", inline=True)

    # ── Premium — field sendiri kalau ada ──────────────────────────────
    if has_prem:
        exp_str = expiry_map.get(str(uid))
        prem_value = "Lifetime"
        if exp_str:
            try:
                exp = datetime.datetime.fromisoformat(exp_str)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                prem_value = discord.utils.format_dt(exp, "R")
            except Exception:
                prem_value = "Active"
        embed.add_field(name=f"{e(ICON_PREMIUM_TAG, '💎')} Premium".strip(), value=prem_value, inline=True)

    embed.set_footer(
        text=f"{BOT_NAME} • {BOT_TAGLINE}",
        icon_url=user.display_avatar.url
    )
    return embed


# ══════════════════════════════════════════════════════════════════
# ANTI SPAM — Cross-channel fingerprint tracker
# ══════════════════════════════════════════════════════════════════

spam_tracker:       dict[int, dict[str, dict]] = defaultdict(dict)
spam_cleanup_times: dict[int, float]           = {}

def _spam_fingerprint(message: discord.Message) -> str:
    parts: list[str] = []
    text = message.content.strip().lower()
    if text:
        parts.append(text)
    for att in message.attachments:
        parts.append(f"att:{att.filename.lower()}")
    url_pat = re.compile(r"(https?://[^\s]+|discord\.gg/[^\s]+)", re.IGNORECASE)
    for url in url_pat.findall(message.content):
        parts.append(f"url:{url.lower().split('?')[0].rstrip('/')}")
    for emb in message.embeds:
        if emb.url:
            parts.append(f"url:{emb.url.lower().split('?')[0].rstrip('/')}")
    return "|".join(sorted(set(parts))) or "empty"

# ══════════════════════════════════════════════════════════════════
# OWNER / PERMISSION HELPERS
# ══════════════════════════════════════════════════════════════════

OWNER_ONLY_CMDS = {"maintenance", "noprefix", "botrole", "grantpremium", "premiumlock", "blacklist", "vxleave", "ownerhelp"}

def is_owner():
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.id == bot.owner_id
    return commands.check(predicate)

def is_staff_or_above(uid: int) -> bool:
    role = get_bot_role(uid)
    return role in BOT_ROLE_HIERARCHY

@bot.check
async def global_maintenance_check(ctx: commands.Context) -> bool:
    if ctx.author.id == bot.owner_id or not is_maintenance_on():
        return True
    m    = cfg.get("maintenance", {})
    desc = f"**{BOT_NAME}** lagi maintenance, coba lagi nanti."
    if m.get("reason"):
        desc += f"\n\n**Alasan:** {m['reason']}"
    await ctx.send(embed=warning_embed("Under Maintenance", desc), delete_after=10)
    return False

@bot.check
async def global_prefix_premium_check(ctx: commands.Context) -> bool:
    cmd = ctx.command.qualified_name if ctx.command else None
    if not cmd or cmd in OWNER_ONLY_CMDS:
        return True
    if cmd not in cfg.get("premium_commands", []):
        return True
    if ctx.author.id == bot.owner_id:
        return True
    if user_has_premium(ctx.guild, ctx.author):
        return True
    await ctx.send(embed=warning_embed(
        "Premium Required",
        f"Command `{cmd}` hanya untuk **Premium** users.\n"
        "Hubungi owner untuk berlangganan."
    ))
    return False

# ══════════════════════════════════════════════════════════════════
# MODERATION HELPERS
# ══════════════════════════════════════════════════════════════════

def _is_protected(guild: discord.Guild, member: discord.Member) -> bool:
    """Cek apakah member tidak bisa dimoderasi (owner guild atau role lebih tinggi dari bot)."""
    if member.id == guild.owner_id:
        return True
    if guild.me and member.top_role >= guild.me.top_role:
        return True
    return False

async def do_kick(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.kick_members:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("Tidak bisa kick user ini."))
    try:
        await member.kick(reason=f"{author} | {reason}")
        await reply_fn(embed=success_embed(t(cfg, guild.id, "kick_success", user=member.mention, reason=reason)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk kick."))

async def do_ban(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.ban_members:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("Tidak bisa ban user ini."))
    try:
        await guild.ban(member, reason=f"{author} | {reason}", delete_message_days=0)
        await reply_fn(embed=success_embed(t(cfg, guild.id, "ban_success", user=member.mention, reason=reason)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk ban."))

async def do_timeout(guild, author, member, minutes, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.moderate_members:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("Tidak bisa timeout user ini."))
    try:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{author} | {reason}")
        await reply_fn(embed=success_embed(t(cfg, guild.id, "timeout_success", user=member.mention, duration=minutes)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk timeout."))

async def do_warn(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_messages:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    gc = guild_cfg(cfg, guild.id)
    gc.setdefault("warnings", {}).setdefault(str(member.id), []).append({
        "reason": reason, "warned_by": author.id,
        "timestamp": discord.utils.utcnow().isoformat()
    })
    save_config(cfg)
    try:
        dm = base_embed(f"You were warned in {guild.name}", f"Reason: {reason}", color=COLOR_WARNING)
        await member.send(embed=dm)
    except Exception:
        pass
    await reply_fn(embed=success_embed(t(cfg, guild.id, "warn_success", user=member.mention, reason=reason)))

async def do_addrole(guild, author, member, role, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_roles:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    try:
        await member.add_roles(role, reason=f"By {author}")
        await reply_fn(embed=success_embed(t(cfg, guild.id, "role_add", role=role.name, user=member.mention)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk manage roles."))

async def do_removerole(guild, author, member, role, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_roles:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    try:
        await member.remove_roles(role, reason=f"By {author}")
        await reply_fn(embed=success_embed(t(cfg, guild.id, "role_remove", role=role.name, user=member.mention)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk manage roles."))

async def do_move(guild, author, member, channel, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.move_members:
        return await reply_fn(embed=error_embed(t(cfg, guild.id, "no_perm")))
    try:
        await member.move_to(channel, reason=f"By {author}")
        await reply_fn(embed=success_embed(t(cfg, guild.id, "move_success", user=member.mention, channel=channel.name)))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("Bot tidak punya izin untuk move member."))

async def do_userinfo(guild, member, reply_fn):
    roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"][:10]
    embed = discord.Embed(title=f"{member.display_name}", color=member.color or COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username",  value=str(member),                                              inline=True)
    embed.add_field(name="ID",        value=f"`{member.id}`",                                         inline=True)
    embed.add_field(name="Bot",       value="Yes" if member.bot else "No",                             inline=True)
    embed.add_field(name="Joined",    value=discord.utils.format_dt(member.joined_at, "R") if member.joined_at else "?", inline=True)
    embed.add_field(name="Created",   value=discord.utils.format_dt(member.created_at, "R"),           inline=True)
    embed.add_field(name="Roles",     value=" ".join(roles) if roles else "None",                      inline=False)
    embed.set_footer(text=f"{BOT_NAME} • {guild.name}")
    await reply_fn(embed=embed)

async def do_avatar(member, reply_fn):
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=COLOR_PRIMARY)
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=BOT_NAME)
    await reply_fn(embed=embed)

async def do_ping(reply_fn):
    lat = round(bot.latency * 1000)
    embed = base_embed("Pong!", f"Latency: **{lat}ms**", COLOR_SUCCESS if lat < 100 else COLOR_WARNING)
    await reply_fn(embed=embed)

async def do_addemoji(guild, emoji_or_url: str, name: str):
    import aiohttp, io
    try:
        if emoji_or_url.startswith("<") and ":" in emoji_or_url:
            parts  = emoji_or_url.strip("<>").split(":")
            eid    = parts[-1]
            ext    = "gif" if emoji_or_url.startswith("<a:") else "png"
            url    = f"https://cdn.discordapp.com/emojis/{eid}.{ext}"
            name   = name or parts[-2]
        else:
            url = emoji_or_url
        if not name:
            return {"success": False, "error": "Nama emoji diperlukan."}
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return {"success": False, "error": f"Gagal fetch image: HTTP {r.status}"}
                data = await r.read()
        emoji = await guild.create_custom_emoji(name=name, image=data)
        return {"success": True, "emoji": emoji}
    except discord.Forbidden:
        return {"success": False, "error": "Bot tidak punya izin manage emojis."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ══════════════════════════════════════════════════════════════════
# TICKET HANDLER
# ══════════════════════════════════════════════════════════════════

def _fallback_log_channel(gc: dict) -> Optional[int]:
    """Dipakai honeypot/log umum kalau mod_log_channel belum di-set —
    pinjam log channel dari panel ticket pertama yang punya satu."""
    if gc.get("mod_log_channel"):
        return gc["mod_log_channel"]
    for p in gc["ticket"]["panels"].values():
        if p.get("log_channel"):
            return p["log_channel"]
    return None

def _find_active_ticket(gc: dict, channel_id: int):
    """Cari ticket aktif berdasarkan channel_id.
    Return (uid_str, ticket_dict, panel_dict) atau (None, None, None)."""
    for uid, tickets in gc["active_tickets"].items():
        for tk in tickets:
            if tk.get("channel_id") == channel_id:
                panel = gc["ticket"]["panels"].get(tk.get("panel_id"), {})
                return uid, tk, panel
    return None, None, None

async def handle_open_ticket(interaction: discord.Interaction, panel_id: str):
    gc    = guild_cfg(cfg, interaction.guild.id)
    panel = gc["ticket"]["panels"].get(panel_id)
    uid   = str(interaction.user.id)

    if not panel or not panel.get("category"):
        return await interaction.response.send_message(
            embed=error_embed("Ticket panel ini belum dikonfigurasi dengan benar."), ephemeral=True)

    tickets    = gc["active_tickets"].setdefault(uid, [])
    same_panel = [tk for tk in tickets if tk.get("panel_id") == panel_id and interaction.guild.get_channel(tk.get("channel_id"))]
    max_t      = panel.get("max_tickets", 1)
    if len(same_panel) >= max_t:
        ch  = interaction.guild.get_channel(same_panel[0]["channel_id"]) if same_panel else None
        msg = t(cfg, interaction.guild.id, "ticket_exists") if max_t == 1 else \
            f"Kamu sudah punya {len(same_panel)}/{max_t} ticket terbuka untuk panel **{panel.get('title', panel_id)}**."
        if ch:
            msg += f"\n{ch.mention}"
        return await interaction.response.send_message(embed=error_embed(msg), ephemeral=True)

    category = interaction.guild.get_channel(panel["category"])
    if not category:
        return await interaction.response.send_message(
            embed=error_embed("Ticket category tidak ditemukan."), ephemeral=True)

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:               discord.PermissionOverwrite(view_channel=True, send_messages=True),
        interaction.guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    role_id = panel.get("support_role")
    if role_id:
        role = interaction.guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    ch = await category.create_text_channel(
        name=f"ticket-{interaction.user.name}",
        overwrites=overwrites,
        topic=f"Ticket [{panel_id}] for {interaction.user} ({interaction.user.id})"
    )
    tickets.append({
        "channel_id": ch.id,
        "panel_id":   panel_id,
        "opened_at":  discord.utils.utcnow().isoformat(),
    })
    save_config(cfg)

    welcome_embed = base_embed(
        panel.get("title") or f"Ticket — {interaction.user.display_name}",
        panel.get("description") or "Tim support akan segera membantu. Jelaskan keperluanmu di sini.",
        color=COLOR_PRIMARY
    )
    await ch.send(content=interaction.user.mention, embed=welcome_embed, view=TicketCloseView())

    log_id = panel.get("log_channel")
    if log_id:
        log_ch = interaction.guild.get_channel(log_id)
        if log_ch:
            log_emb = base_embed("Ticket Opened", None, color=COLOR_PRIMARY)
            log_emb.add_field(name="User",    value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            log_emb.add_field(name="Channel", value=ch.mention, inline=True)
            log_emb.add_field(name="Panel",   value=panel.get("title") or panel_id, inline=True)
            try:
                await log_ch.send(embed=log_emb)
            except Exception:
                pass

    await interaction.response.send_message(
        embed=success_embed(t(cfg, interaction.guild.id, "ticket_open", channel=ch.mention)),
        ephemeral=True
    )

async def close_ticket_channel(guild: discord.Guild, channel: discord.abc.GuildChannel,
                                closer: discord.abc.User, reason: str, send_confirmation) -> bool:
    """Logic inti penutupan ticket, dipakai bareng tombol Close dan command `ticket close`.
    Log dikirim ke log channel milik PANEL asal ticket tersebut, bukan log channel global."""
    gc = guild_cfg(cfg, guild.id)
    uid, tk, panel = _find_active_ticket(gc, channel.id)
    if not tk:
        await send_confirmation(embed=error_embed("Channel ini bukan ticket aktif."))
        return False

    is_owner_  = closer.id == bot.owner_id
    can_manage = getattr(closer, "guild_permissions", None) and closer.guild_permissions.manage_channels
    if not (is_owner_ or can_manage or str(closer.id) == uid):
        await send_confirmation(embed=error_embed("Kamu tidak bisa menutup ticket ini."))
        return False

    gc["active_tickets"][uid] = [x for x in gc["active_tickets"][uid] if x.get("channel_id") != channel.id]
    if not gc["active_tickets"][uid]:
        del gc["active_tickets"][uid]
    save_config(cfg)

    reason = reason or "Closed via command."
    await send_confirmation(embed=base_embed(
        "Ticket Closing", f"Ditutup oleh {closer.mention}.\n{reason}\n\nChannel dihapus dalam 5 detik.", color=COLOR_ERROR))

    log_id = panel.get("log_channel")
    if log_id:
        log_ch = guild.get_channel(log_id)
        if log_ch:
            duration_str = "?"
            try:
                opened_dt = datetime.datetime.fromisoformat(tk.get("opened_at"))
                if opened_dt.tzinfo is None:
                    opened_dt = opened_dt.replace(tzinfo=datetime.timezone.utc)
                mins = int((discord.utils.utcnow() - opened_dt).total_seconds() // 60)
                duration_str = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
            except Exception:
                pass
            owner_member = guild.get_member(int(uid))
            log_emb = base_embed("Ticket Closed", None, color=COLOR_ERROR)
            log_emb.add_field(name="Ticket Owner", value=f"{owner_member.mention if owner_member else '<@'+uid+'>'} (`{uid}`)", inline=True)
            log_emb.add_field(name="Closed By",    value=closer.mention, inline=True)
            log_emb.add_field(name="Panel",        value=panel.get("title") or tk.get("panel_id", "?"), inline=True)
            log_emb.add_field(name="Duration",     value=duration_str, inline=True)
            log_emb.add_field(name="Reason",       value=reason, inline=False)
            try:
                await log_ch.send(embed=log_emb)
            except Exception:
                pass

    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"Ticket closed by {closer}")
    except Exception:
        pass
    return True

class TicketCloseView(discord.ui.View):
    """View persisten & statis — satu custom_id untuk semua ticket, aman dipakai
    lintas restart bot lewat bot.add_view() di on_ready."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger,
                        emoji=ICON_TICKET_CLOSE if ICON_TICKET_CLOSE else "🔒",
                        custom_id="vx_ticket_close")
    async def close_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        async def _respond(**kw):
            try:
                await interaction.response.send_message(**kw)
            except discord.InteractionResponded:
                await interaction.followup.send(**kw)
        await close_ticket_channel(interaction.guild, interaction.channel, interaction.user, "Ditutup via tombol.", _respond)

class TicketOpenView(discord.ui.View):
    """Satu instance per panel — custom_id menyimpan panel_id supaya tombol tetap
    tahu panel mana yang harus dibuka, termasuk setelah bot restart."""
    def __init__(self, panel_id: str):
        super().__init__(timeout=None)
        self.panel_id = panel_id
        btn = discord.ui.Button(
            label="Open Ticket", style=discord.ButtonStyle.danger,
            emoji=ICON_TICKET_OPEN if ICON_TICKET_OPEN else "🎫",
            custom_id=f"vx_ticket_open:{panel_id}"
        )
        btn.callback = self._open_callback
        self.add_item(btn)

    async def _open_callback(self, interaction: discord.Interaction):
        await handle_open_ticket(interaction, self.panel_id)

# ══════════════════════════════════════════════════════════════════
# GIVEAWAY SYSTEM
# ══════════════════════════════════════════════════════════════════

import random
active_giveaways: dict[int, dict] = {}

def build_giveaway_embed(gw: dict) -> discord.Embed:
    ends_dt = datetime.datetime.utcfromtimestamp(gw["ends_ts"]).replace(tzinfo=datetime.timezone.utc)
    embed   = discord.Embed(
        title=f"GIVEAWAY — {gw['prize']}",
        description=(
            (gw.get("description", "") + "\n\n" if gw.get("description") else "") +
            f"React dengan 🎉 untuk ikut!\n\n"
            f"**Winners:** {gw['winner_count']}\n"
            f"**Ends:** {discord.utils.format_dt(ends_dt, 'R')}\n"
            f"**Hosted by:** <@{gw['host_id']}>"
        ),
        color=COLOR_ERROR,
        timestamp=ends_dt
    )
    if gw.get("required_role"):
        embed.add_field(name="Required Role", value=f"<@&{gw['required_role']}>", inline=True)
    if gw.get("winner_role_id"):
        embed.add_field(name="Winner Role", value=f"<@&{gw['winner_role_id']}>", inline=True)
    embed.set_footer(text=f"{BOT_NAME} Giveaway • React 🎉 to enter")
    return embed

async def end_giveaway(gw: dict):
    if gw.get("ended"):
        return
    gw["ended"] = True
    active_giveaways.pop(gw["message_id"], None)
    channel = bot.get_channel(gw["channel_id"])
    if not channel:
        return
    try:
        msg = await channel.fetch_message(gw["message_id"])
    except Exception:
        return
    entries = list(set(gw.get("entries", [])))
    if not entries:
        ended_embed = build_giveaway_embed(gw)
        ended_embed.description = "**Giveaway Ended**\n\nTidak ada peserta."
        ended_embed.color = 0x4B5563
        try:
            await msg.edit(embed=ended_embed)
        except Exception:
            pass
        await channel.send(embed=info_embed("Giveaway Ended", f"Tidak ada pemenang untuk **{gw['prize']}**."))
        return
    count   = min(gw["winner_count"], len(entries))
    winners = random.sample(entries, count)
    gw["winners"] = winners
    ended_embed = build_giveaway_embed(gw)
    winner_str  = " ".join(f"<@{w}>" for w in winners)
    ended_embed.description = f"**Giveaway Ended!**\n\n**Winners:** {winner_str}"
    ended_embed.color = 0x4B5563
    try:
        await msg.edit(embed=ended_embed)
    except Exception:
        pass
    role_note = ""
    win_role_id = gw.get("winner_role_id")
    if win_role_id:
        win_role = channel.guild.get_role(win_role_id)
        if win_role:
            assigned = 0
            for wid in winners:
                m = channel.guild.get_member(wid)
                if m:
                    try:
                        await m.add_roles(win_role, reason=f"Giveaway winner: {gw['prize']}")
                        assigned += 1
                    except Exception:
                        pass
            if assigned:
                role_note = f"\nRole {win_role.mention} diberikan ke {assigned} pemenang."
    win_embed = discord.Embed(
        title=f"{e(ICON_WINNER, '🏆')} Giveaway Winners!".strip(),
        description=f"Selamat {winner_str}!\n\n**Prize:** {gw['prize']}{role_note}",
        color=COLOR_SUCCESS,
        timestamp=discord.utils.utcnow()
    )
    win_embed.set_footer(text=f"{BOT_NAME} Giveaway")
    await channel.send(content=winner_str, embed=win_embed)

# ══════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════

@tasks.loop(minutes=10)
async def premium_expiry_task():
    await check_premium_expiry()
    await check_no_prefix_expiry()

@tasks.loop(minutes=30)
async def cleanup_spam_cache():
    now     = discord.utils.utcnow().timestamp()
    to_del  = [uid for uid, t in spam_cleanup_times.items() if now - t > 120]
    for uid in to_del:
        spam_tracker.pop(uid, None)
        spam_cleanup_times.pop(uid, None)

@tasks.loop(minutes=5)
async def rotate_status():
    if is_maintenance_on():
        try:
            await bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.playing, name="Under Maintenance ⚠️"),
                status=discord.Status.dnd
            )
        except Exception:
            pass
        return
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="every move."),
        discord.Activity(type=discord.ActivityType.listening, name="!vx help"),
        discord.Activity(type=discord.ActivityType.playing, name="VALLENT EXS v1.0"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"),
    ]
    import random as _r
    await bot.change_presence(activity=_r.choice(statuses), status=discord.Status.dnd)

async def sync_premium_descriptions():
    """Tempel prefix [💎] di deskripsi slash command yang lagi di-lock ke Premium,
    lalu re-sync ke Discord biar kelihatan di UI slash command."""
    locked  = set(cfg.get("premium_commands", []))
    changed = False
    for cmd in bot.tree.get_commands():
        base   = ORIGINAL_CMD_DESCRIPTIONS.get(cmd.name, cmd.description.removeprefix("[💎] "))
        wanted = f"[💎] {base}" if cmd.name in locked else base
        if cmd.description != wanted:
            cmd.description = wanted
            changed = True
        if hasattr(cmd, "commands"):
            for sub in cmd.commands:
                key      = f"{cmd.name} {sub.name}"
                base_sub = ORIGINAL_CMD_DESCRIPTIONS.get(key, sub.description.removeprefix("[💎] "))
                wanted_sub = f"[💎] {base_sub}" if key in locked else base_sub
                if sub.description != wanted_sub:
                    sub.description = wanted_sub
                    changed = True
    if changed:
        try:
            await bot.tree.sync()
        except Exception as e:
            logging.error(f"[{BOT_NAME}] Gagal sync deskripsi premium: {e}")

# ══════════════════════════════════════════════════════════════════
# BOT EVENTS
# ══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"[{BOT_NAME}] Ready as {bot.user} (ID: {bot.user.id})")
    for cmd in bot.tree.get_commands():
        ORIGINAL_CMD_DESCRIPTIONS[cmd.name] = cmd.description.removeprefix("[💎] ")
        if hasattr(cmd, "commands"):
            for sub in cmd.commands:
                ORIGINAL_CMD_DESCRIPTIONS[f"{cmd.name} {sub.name}"] = sub.description.removeprefix("[💎] ")
    await sync_premium_descriptions()
    try:
        synced = await bot.tree.sync()
        print(f"[{BOT_NAME}] Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"[{BOT_NAME}] Sync error: {e}")

    # Daftarkan ulang persistent views (ticket) supaya tombol tetap hidup setelah restart.
    bot.add_view(TicketCloseView())
    panel_ids = {pid for gcfg in cfg.get("guilds", {}).values() for pid in gcfg.get("ticket", {}).get("panels", {}).keys()}
    for pid in panel_ids:
        bot.add_view(TicketOpenView(pid))

    if not cleanup_spam_cache.is_running():
        cleanup_spam_cache.start()
    if not rotate_status.is_running():
        rotate_status.start()
    if not premium_expiry_task.is_running():
        premium_expiry_task.start()
    print(f"[{BOT_NAME}] Online — {len(bot.guilds)} guild(s).")

@bot.event
async def on_command_completion(ctx: commands.Context):
    """Dipanggil discord.py setiap kali prefix command SUKSES dijalankan.
    Ini sumber kebenaran untuk statistik 'Commands Runned' di profile."""
    uid_str  = str(ctx.author.id)
    cmds_run = cfg.setdefault("commands_run", {})
    cmds_run[uid_str] = cmds_run.get(uid_str, 0) + 1
    save_config(cfg)

@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    """Jantungnya anti-nuke — dipanggil Discord real-time tiap ada audit log
    baru, gak perlu polling. Butuh permission 'View Audit Log' di role bot."""
    guild = entry.guild
    gc    = guild_cfg(cfg, guild.id)
    ac    = gc.get("antinuke", {})
    if not ac.get("enabled"):
        return
    if not entry.user or entry.user.id == bot.user.id:
        return
    if antinuke.is_whitelisted(guild, entry.user.id, bot.owner_id, ac.get("whitelist", [])):
        return

    action = antinuke.classify_entry(entry)
    if not action:
        return

    triggered = False
    if action in antinuke.INSTANT_ACTIONS:
        triggered = True
    else:
        th = antinuke.DEFAULT_THRESHOLDS.get(action)
        if th:
            triggered = antinuke._record_and_check(guild.id, entry.user.id, action, th["count"], th["seconds"])

    if not triggered:
        return

    member = guild.get_member(entry.user.id)
    if not member:
        return

    punishment = ac.get("punishment", "strip_roles")
    result = await antinuke.punish(guild, member, punishment, f"[Anti-Nuke] Terdeteksi: {antinuke.ACTION_LABELS.get(action, action)}")
    antinuke.reset_tracker(guild.id, entry.user.id)

    log_id = ac.get("log_channel")
    log_ch = guild.get_channel(log_id) if log_id else None
    if log_ch:
        emb = discord.Embed(
            title=f"{e(ICON_ANTINUKE, '🛡️')} Anti-Nuke Triggered".strip(),
            description=(
                f"**Pelaku:** {member.mention} (`{member.id}`)\n"
                f"**Terdeteksi:** {antinuke.ACTION_LABELS.get(action, action)}\n"
                f"**Tindakan:** {result}"
            ),
            color=COLOR_ERROR,
            timestamp=discord.utils.utcnow()
        )
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text=BOT_NAME)
        try:
            await log_ch.send(embed=emb)
        except Exception:
            pass
    logging.warning(f"[{BOT_NAME}] Anti-Nuke triggered in {guild.name}: {member} -> {action} -> {result}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    guild_cfg(cfg, guild.id)
    logging.info(f"[{BOT_NAME}] Joined: {guild.name} ({guild.id})")
    bl = cfg.get("blacklisted_guilds", [])
    if guild.id in bl:
        try:
            await guild.leave()
            logging.info(f"[{BOT_NAME}] Left blacklisted guild: {guild.name}")
        except Exception:
            pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.guild:
        return

    # ── Honeypot channel check ────────────────────────────────────────────
    gc_trap  = guild_cfg(cfg, message.guild.id)
    trap_ch  = gc_trap.get("spam_trap_channel")
    if trap_ch and message.channel.id == trap_ch:
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await message.guild.ban(
                message.author,
                reason=f"[{BOT_NAME}] Sent message in honeypot channel.",
                delete_message_days=1
            )
        except discord.Forbidden:
            pass
        log_id = _fallback_log_channel(gc_trap)
        if log_id:
            log_ch = message.guild.get_channel(log_id)
            if log_ch:
                emb = base_embed("Honeypot — Auto Banned", None, color=COLOR_ERROR)
                emb.add_field(name="User",    value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
                emb.add_field(name="Channel", value=f"<#{trap_ch}>", inline=True)
                snippet = (message.content or "")[:200]
                if snippet:
                    emb.add_field(name="Content", value=f"```{snippet}```", inline=False)
                try:
                    await log_ch.send(embed=emb)
                except Exception:
                    pass
        return

    # ── XP system ─────────────────────────────────────────────────────────
    gc = guild_cfg(cfg, message.guild.id)
    if gc.get("leveling_enabled", True):
        import time
        uid  = str(message.author.id)
        data = get_member_xp(gc, uid)
        now  = time.time()
        cd   = gc.get("xp_cooldown", 60)
        if now - data.get("last_msg_ts", 0) >= cd:
            xp_min, xp_max = gc.get("xp_per_message", [15, 25])
            gain           = round(random.randint(xp_min, xp_max) * get_xp_multiplier(message.author.id))
            old_level      = data["level"]
            data["xp"]    += gain
            data["level"]  = level_from_xp(data["xp"])
            data["last_msg_ts"] = now
            data["messages"]    = data.get("messages", 0) + 1
            save_config(cfg)
            if data["level"] > old_level:
                granted_roles = await apply_level_roles(message.guild, message.author, gc, data["level"])
                lvl_ch_id = gc.get("level_channel")
                lvl_ch    = message.guild.get_channel(lvl_ch_id) if lvl_ch_id else message.channel
                if lvl_ch:
                    roles_txt = ("🎁 Unlocked: " + " ".join(r.mention for r in granted_roles)) if granted_roles else ""
                    template  = gc.get("levelup_message") or "{mention} leveled up to **Level {level}**!"
                    content   = (template
                                 .replace("{mention}", message.author.mention)
                                 .replace("{user}",    message.author.name)
                                 .replace("{level}",   str(data["level"]))
                                 .replace("{server}",  message.guild.name)
                                 .replace("{roles}",   roles_txt))
                    try:
                        avatar_url = str(message.author.display_avatar.with_format("png").with_size(256))
                        async with aiohttp.ClientSession() as session:
                            async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                                avatar_bytes = await resp.read()
                        is_prem = user_has_premium(message.guild, message.author)
                        role_names = [r.name for r in granted_roles] if granted_roles else None
                        buf = await asyncio.to_thread(
                            rank_card.render_levelup_card,
                            avatar_bytes, message.author.name, data["level"], is_prem, role_names
                        )
                        file = discord.File(buf, filename="levelup.png")
                        await lvl_ch.send(content=content, file=file)
                    except Exception as e:
                        logging.error(f"[{BOT_NAME}] Gagal render level-up card: {e}")
                        lvl_emb = discord.Embed(description=content, color=COLOR_ERROR)
                        lvl_emb.set_author(name="Level Up!", icon_url=message.author.display_avatar.url)
                        lvl_emb.set_footer(text=BOT_NAME)
                        try:
                            await lvl_ch.send(embed=lvl_emb)
                        except Exception:
                            pass

    # ── Anti cross-channel spam ────────────────────────────────────────────
    uid         = message.author.id
    fingerprint = _spam_fingerprint(message)
    if fingerprint == "empty":
        await bot.process_commands(message)
        return
    now_ts = discord.utils.utcnow().timestamp()
    spam_cleanup_times[uid] = now_ts
    tracker = spam_tracker[uid]
    if fingerprint not in tracker:
        tracker[fingerprint] = {"channels": set(), "messages": [], "first_seen": now_ts}
    entry = tracker[fingerprint]
    if now_ts - entry["first_seen"] > SPAM_WINDOW:
        tracker[fingerprint] = {"channels": {message.channel.id}, "messages": [(message.channel.id, message.id)], "first_seen": now_ts}
        entry = tracker[fingerprint]
    else:
        entry["channels"].add(message.channel.id)
        entry["messages"].append((message.channel.id, message.id))
    if len(entry["channels"]) >= SPAM_THRESHOLD:
        del tracker[fingerprint]
        for ch_id, msg_id in entry["messages"]:
            try:
                ch  = message.guild.get_channel(ch_id)
                msg = await ch.fetch_message(msg_id) if ch else None
                if msg:
                    await msg.delete()
            except Exception:
                pass
        try:
            await message.guild.ban(
                message.author,
                reason=f"[{BOT_NAME}] Cross-channel spam detected.",
                delete_message_days=1
            )
        except discord.Forbidden:
            pass
        return

    # ── Prefix routing + no-prefix ────────────────────────────────────────
    low = message.content.lower().strip()
    if low.startswith("!vx ") or low == "!vx":
        message.content = "!vx " + message.content[len("!vx"):].lstrip()
    elif low.startswith("!v ") or low == "!v":
        message.content = "!vx " + message.content[len("!v"):].lstrip()
    elif not message.content.startswith("!vx "):
        if user_has_no_prefix(message.guild, message.author):
            text  = message.content.strip()
            first = text.split()[0].lower() if text.split() else ""
            known = set()
            for c in bot.commands:
                known.add(c.name)
                known.update(c.aliases)
            if first in known:
                message.content = "!vx " + text

    await bot.process_commands(message)

# ══════════════════════════════════════════════════════════════════
# GIVEAWAY — REACTION HANDLER
# ══════════════════════════════════════════════════════════════════

@bot.event
async def on_member_remove(member: discord.Member):
    """Cabut badge USER saat user leave server support."""
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if member.guild.id != support_server_id:
        return
    support_members = cfg.get("support_server_members", [])
    if member.id in support_members:
        support_members.remove(member.id)
        save_config(cfg)

async def handle_new_boost(member: discord.Member):
    """Kirim notifikasi ke channel yang dikonfigurasi lewat /boostconfig ketika
    seorang member baru mulai boost server ini."""
    gc    = guild_cfg(cfg, member.guild.id)
    bc    = gc.get("boost", {})
    ch_id = bc.get("channel")
    if not ch_id:
        return
    channel = member.guild.get_channel(ch_id)
    if not channel:
        return

    count = member.guild.premium_subscription_count or 0
    def fill(template: str) -> str:
        return (template
                .replace("{mention}", member.mention)
                .replace("{user}",    member.display_name)
                .replace("{server}",  member.guild.name)
                .replace("{count}",   str(count))
                .replace("{tier}",    str(member.guild.premium_tier)))

    title = fill(bc.get("title") or "New Server Boost!")
    emoji_str = bc.get("emoji") or e(ICON_BOOST, "🎉")
    desc  = fill(bc.get("description") or "{mention} just boosted **{server}**! Thanks for the support 💜")

    embed = discord.Embed(
        title=f"{emoji_str} {title}".strip(),
        description=desc,
        color=0xF47FFF,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"{member.guild.name} • Boost #{count}")
    try:
        await channel.send(embed=embed)
    except Exception:
        pass

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # ── Server boost notification — jalan di semua guild yang dikonfigurasi ──
    if not before.premium_since and after.premium_since:
        await handle_new_boost(after)

    # ── Badge role-sync itu live (dihitung langsung dari role Discord tiap kali
    # get_bot_role() dipanggil), jadi gak butuh update apapun di sini. Ini cuma
    # buat kasih DM selamat pas seseorang baru dapat role yang di-sync ke badge
    # — biar mereka sadar badge-nya naik. Cuma berlaku di support server. ────
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if after.guild.id != support_server_id or after.bot:
        return
    if before.roles == after.roles:
        return
    role_sync = cfg.get("role_sync", {})
    if not role_sync:
        return
    before_ids = {r.id for r in before.roles}
    after_ids  = {r.id for r in after.roles}
    gained     = after_ids - before_ids
    for tier in reversed(BOT_ROLE_HIERARCHY):
        role_id = role_sync.get(tier)
        if role_id and role_id in gained:
            info      = BOT_ROLE_BADGES[tier]
            badge_tag = (info["emoji"] + " ") if info.get("emoji") else ""
            try:
                await after.send(embed=base_embed(
                    "Badge Updated!",
                    f"Kamu baru dapat role di **{after.guild.name}** dan sekarang otomatis punya badge "
                    f"{badge_tag}**{info['label']}** di {BOT_NAME}!\nCek profil: `profile`",
                    color=info["color"]
                ))
            except Exception:
                pass
            break

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    GIVEAWAY_EMOJI = ICON_GIVEAWAY_REACT if ICON_GIVEAWAY_REACT else "🎉"
    if str(payload.emoji) != GIVEAWAY_EMOJI:
        return
    gw = active_giveaways.get(payload.message_id)
    if not gw or gw.get("ended"):
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    if payload.user_id in gw["entries"]:
        return
    req_role = gw.get("required_role")
    if req_role and not any(r.id == req_role for r in member.roles):
        return
    gw["entries"].append(payload.user_id)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    GIVEAWAY_EMOJI = ICON_GIVEAWAY_REACT if ICON_GIVEAWAY_REACT else "🎉"
    if str(payload.emoji) != GIVEAWAY_EMOJI:
        return
    gw = active_giveaways.get(payload.message_id)
    if not gw or gw.get("ended"):
        return
    if payload.user_id in gw["entries"]:
        gw["entries"].remove(payload.user_id)

# ══════════════════════════════════════════════════════════════════
# PREFIX COMMANDS — MODERATION
# ══════════════════════════════════════════════════════════════════

@bot.command(name="kick")
async def pfx_kick(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_kick(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="ban")
async def pfx_ban(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_ban(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="unban")
async def pfx_unban(ctx, user_id: str):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.ban_members:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    try:
        uid  = int(user_id.strip("<@!>"))
        await ctx.guild.unban(discord.Object(id=uid), reason=f"By {ctx.author}")
        await ctx.send(embed=success_embed(f"User `{uid}` di-unban."))
    except discord.NotFound:
        await ctx.send(embed=error_embed("User tidak ada di ban list."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("Bot tidak punya izin."))

@bot.command(name="timeout")
async def pfx_timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "No reason provided."):
    await do_timeout(ctx.guild, ctx.author, member, minutes, reason, ctx.send)

@bot.command(name="untimeout")
async def pfx_untimeout(ctx, member: discord.Member):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    try:
        await member.timeout(None, reason=f"By {ctx.author}")
        await ctx.send(embed=success_embed(f"Timeout {member.mention} dilepas."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("Bot tidak punya izin."))

@bot.command(name="warn")
async def pfx_warn(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_warn(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="warnings")
async def pfx_warnings(ctx, member: discord.Member = None):
    target = member or ctx.author
    gc     = guild_cfg(cfg, ctx.guild.id)
    warns  = gc.get("warnings", {}).get(str(target.id), [])
    if not warns:
        return await ctx.send(embed=info_embed(f"Warnings — {target.display_name}", "Tidak ada warning."))
    lines = [
        f"**{i+1}.** {w.get('reason','?')} *(by <@{w.get('warned_by','?')}> — {w.get('timestamp','')[:10]})*"
        for i, w in enumerate(warns)
    ]
    embed = discord.Embed(title=f"Warnings — {target.display_name}", description="\n".join(lines), color=COLOR_WARNING)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text=f"Total: {len(warns)} warning(s) • {BOT_NAME}")
    await ctx.send(embed=embed)

@bot.command(name="unwarn")
async def pfx_unwarn(ctx, member: discord.Member, number: int):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    gc    = guild_cfg(cfg, ctx.guild.id)
    warns = gc.get("warnings", {}).get(str(member.id), [])
    if not warns:
        return await ctx.send(embed=error_embed(f"{member.display_name} tidak punya warning."))
    if not 1 <= number <= len(warns):
        return await ctx.send(embed=error_embed(f"Nomor tidak valid (1–{len(warns)})."))
    removed = warns.pop(number - 1)
    save_config(cfg)
    await ctx.send(embed=success_embed(f"Warning #{number} `{removed.get('reason','?')}` dihapus dari {member.mention}."))

@bot.command(name="clearwarnings")
async def pfx_clearwarnings(ctx, member: discord.Member):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    gc = guild_cfg(cfg, ctx.guild.id)
    gc.setdefault("warnings", {})[str(member.id)] = []
    save_config(cfg)
    await ctx.send(embed=success_embed(f"Semua warning {member.mention} dihapus."))

@bot.command(name="purge")
async def pfx_purge(ctx, amount: int = 10):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")), delete_after=5)
    amount  = max(1, min(100, amount))
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=success_embed(f"Dihapus {max(0, len(deleted)-1)} pesan."))
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except Exception:
        pass

@bot.command(name="lock")
async def pfx_lock(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.send_messages = False
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Locked by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} dikunci."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("Bot tidak punya izin."))

@bot.command(name="unlock")
async def pfx_unlock(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.send_messages = None
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlocked by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} dibuka."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("Bot tidak punya izin."))

@bot.command(name="slowmode")
async def pfx_slowmode(ctx, seconds: int = 0, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    ch = channel or ctx.channel
    seconds = max(0, min(21600, seconds))
    try:
        await ch.edit(slowmode_delay=seconds, reason=f"By {ctx.author}")
        msg = f"Slowmode {ch.mention} dimatikan." if seconds == 0 else f"Slowmode {ch.mention} → **{seconds} detik**."
        await ctx.send(embed=success_embed(msg))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("Bot tidak punya izin."))

# ── ROLE & VOICE ──────────────────────────────────────────────────

@bot.command(name="addrole")
async def pfx_addrole(ctx, member: discord.Member, role: discord.Role):
    await do_addrole(ctx.guild, ctx.author, member, role, ctx.send)

@bot.command(name="removerole")
async def pfx_removerole(ctx, member: discord.Member, role: discord.Role):
    await do_removerole(ctx.guild, ctx.author, member, role, ctx.send)

@bot.command(name="move")
async def pfx_move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    await do_move(ctx.guild, ctx.author, member, channel, ctx.send)

# ── INFO ──────────────────────────────────────────────────────────

@bot.command(name="userinfo")
async def pfx_userinfo(ctx, member: discord.Member = None):
    await do_userinfo(ctx.guild, member or ctx.author, ctx.send)

@bot.command(name="serverinfo")
async def pfx_serverinfo(ctx):
    g = ctx.guild
    embed = discord.Embed(title=g.name, description=g.description or "", color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner",      value=f"<@{g.owner_id}>",                           inline=True)
    embed.add_field(name="Members",    value=f"{g.member_count:,}",                         inline=True)
    embed.add_field(name="Created",    value=g.created_at.strftime("%d %b %Y"),              inline=True)
    embed.add_field(name="Channels",   value=str(len(g.text_channels)),                     inline=True)
    embed.add_field(name="Voice",      value=str(len(g.voice_channels)),                    inline=True)
    embed.add_field(name="Roles",      value=str(len(g.roles)),                             inline=True)
    embed.add_field(name="Emojis",     value=str(len(g.emojis)),                            inline=True)
    embed.add_field(name="Boost Tier", value=str(g.premium_tier),                           inline=True)
    embed.add_field(name="Boosts",     value=str(g.premium_subscription_count or 0),        inline=True)
    embed.set_footer(text=f"{BOT_NAME} • ID: {g.id}")
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def pfx_avatar(ctx, member: discord.Member = None):
    await do_avatar(member or ctx.author, ctx.send)

@bot.command(name="ping")
async def pfx_ping(ctx):
    await do_ping(ctx.send)

@bot.command(name="addemoji")
async def pfx_addemoji(ctx, emoji_or_url: str = "", *, name: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_emojis:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    if not emoji_or_url:
        return await ctx.send(embed=error_embed("Usage: `!vx addemoji <:emoji:id>` atau `!vx addemoji <url> <name>`"))
    result = await do_addemoji(ctx.guild, emoji_or_url, name)
    if result["success"]:
        emoji = result["emoji"]
        await ctx.send(embed=success_embed(f"Emoji **{emoji.name}** ditambahkan! {emoji}"))
    else:
        await ctx.send(embed=error_embed(result["error"]))

# ── PROFILE ───────────────────────────────────────────────────────

@bot.command(name="profile")
async def pfx_profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed  = build_profile_embed(target)
    embed.set_author(name="Profile & Badge Panel", icon_url=target.display_avatar.url)
    # Requested By di footer dengan avatar
    embed.set_footer(
        text=BOT_NAME + "  |  Requested By " + ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

# ── RANK & LEADERBOARD ────────────────────────────────────────────

async def _build_leaderboard_entries(guild: discord.Guild, all_d: list) -> list:
    """Ambil avatar tiap member top-10 secara paralel (bukan satu-satu) biar
    generate leaderboard card gak lemot nunggu 10 request HTTP berurutan."""
    async def fetch_one(idx, uid, data):
        m    = guild.get_member(int(uid))
        name = m.name if m else f"User ({uid[:6]})"
        avatar_url = str((m.display_avatar if m else guild.me.display_avatar).with_format("png").with_size(128))
        avatar_bytes = b""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    avatar_bytes = await resp.read()
        except Exception:
            pass
        return {
            "rank": idx + 1, "avatar_bytes": avatar_bytes, "name": name,
            "level": data.get("level", 0), "xp": data.get("xp", 0),
        }
    tasks = [fetch_one(idx, uid, data) for idx, (uid, data) in enumerate(all_d)]
    return await asyncio.gather(*tasks)

def _support_boost_promo(uid: int):
    """Return (content_text, view) buat promo join support server + XP boost.
    content_text jadi None kalau SUPPORT_INVITE belum di-set / formatnya
    bukan URL valid — biar gak nawarin invite yang gak ada atau bikin
    discord.ui.Button error karena URL-nya rusak."""
    if not SUPPORT_INVITE or not SUPPORT_INVITE.startswith(("http://", "https://")):
        return None, None
    remaining = xp_boost_remaining(uid)
    if remaining:
        content = f"XP Boost **+10%** kamu masih aktif sampai {discord.utils.format_dt(remaining, 'R')}!"
    else:
        content = "**Join support server** dan dapatkan **+10% XP Boost** selama 60 menit!"
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Join Support Server", style=discord.ButtonStyle.link, url=SUPPORT_INVITE))
    return content, view

@bot.command(name="rank")
async def pfx_rank(ctx, member: discord.Member = None):
    import aiohttp
    target      = member or ctx.author
    gc          = guild_cfg(cfg, ctx.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"])
    all_m       = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    rank        = next((i+1 for i, (uid, _) in enumerate(all_m) if uid == str(target.id)), 1)
    is_prem     = user_has_premium(ctx.guild, target)
    avatar_url  = str(target.display_avatar.with_format("png").with_size(256))

    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    avatar_bytes = await resp.read()
            buf = await asyncio.to_thread(
                rank_card.render_rank_card,
                avatar_bytes, target.name, lvl, rank, cx, nx,
                data["xp"], is_prem, data.get("messages", 0)
            )
            file = discord.File(buf, filename="rank.png")
        except Exception:
            logging.exception(f"[{BOT_NAME}] Gagal render rank card")
            file = None

        if file:
            kwargs = {"file": file}
            try:
                content, view = _support_boost_promo(ctx.author.id)
                if content: kwargs["content"] = content
                if view:    kwargs["view"] = view
            except Exception:
                logging.exception(f"[{BOT_NAME}] Gagal build boost promo (rank card tetap dikirim)")
            return await ctx.send(**kwargs)
    # Fallback embed teks kalau render gambar gagal total
    pct   = int((cx / max(nx, 1)) * 100)
    bar   = "▰" * int(pct/100*16) + "▱" * (16-int(pct/100*16))
    embed = discord.Embed(
        description=(
            f"**@{target.name}**\n\n"
            f"**Level: {lvl}** | **XP: {cx:,}/{nx:,}** | **Rank: #{rank}**\n\n"
            f"`{bar}` {pct}%\n\n"
            f"*Total XP: {data['xp']:,} | Messages: {data.get('messages',0):,}*"
        ),
        color=COLOR_PRIMARY, timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Rank Card", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text=BOT_NAME)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def pfx_leaderboard(ctx):
    gc    = guild_cfg(cfg, ctx.guild.id)
    all_d = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
    if not all_d:
        return await ctx.send(embed=info_embed("Leaderboard", "Belum ada data XP."))

    async with ctx.typing():
        try:
            entries = await _build_leaderboard_entries(ctx.guild, all_d)
            buf  = await asyncio.to_thread(rank_card.render_leaderboard_card, ctx.guild.name, entries)
            file = discord.File(buf, filename="leaderboard.png")
            return await ctx.send(file=file)
        except Exception as e:
            logging.error(f"[{BOT_NAME}] Gagal render leaderboard card: {e}")

    # Fallback teks kalau render gambar gagal total
    lines = []
    for idx, (uid, data) in enumerate(all_d):
        m     = ctx.guild.get_member(int(uid))
        name  = m.name if m else f"User ({uid[:6]})"
        medal = ["#1","#2","#3"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"**{medal} {name}** — Level **{data.get('level',0)}** · {data.get('xp',0):,} XP")
    embed = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"{BOT_NAME} · {ctx.guild.name}")
    await ctx.send(embed=embed)

@bot.command(name="level")
async def pfx_level(ctx, sub: str = "", *args):
    sub = sub.lower()
    gc  = guild_cfg(cfg, ctx.guild.id)

    if sub == "rank":
        m = None
        if args:
            try: m = ctx.guild.get_member(int(args[0].strip("<@!>")))
            except Exception: pass
        await pfx_rank(ctx, m)

    elif sub == "leaderboard":
        await pfx_leaderboard(ctx)

    elif sub == "message":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        action = args[0].lower() if args else ""
        if action == "set":
            template = " ".join(args[1:]).strip()
            if not template:
                return await ctx.send(embed=error_embed(
                    "Usage: `level message set <teks>`\n\n"
                    "Placeholder: `{mention}` `{user}` `{level}` `{server}` `{roles}`\n"
                    "Contoh: `level message set {mention} gila lu nyampe **Level {level}**! 🔥 {roles}`"
                ))
            gc["levelup_message"] = template
            save_config(cfg)
            preview = (template
                       .replace("{mention}", ctx.author.mention)
                       .replace("{user}",    ctx.author.name)
                       .replace("{level}",   "27")
                       .replace("{server}",  ctx.guild.name)
                       .replace("{roles}",   "🎁 Unlocked: @Elite"))
            embed = success_embed(f"Deskripsi level-up diupdate.\n\n**Preview:**\n{preview}")
            return await ctx.send(embed=embed)
        elif action == "reset":
            gc["levelup_message"] = "{mention} leveled up to **Level {level}**!"
            save_config(cfg)
            return await ctx.send(embed=success_embed("Deskripsi level-up dikembalikan ke default."))
        elif action == "show":
            return await ctx.send(embed=info_embed("Level-Up Message Template", f"```{gc.get('levelup_message','')}```"))
        else:
            return await ctx.send(embed=info_embed("Level-Up Message", (
                "`level message set <teks>` — ganti deskripsi notifikasi level up\n"
                "`level message show` — lihat template sekarang\n"
                "`level message reset` — balikin ke default\n\n"
                "Placeholder yang bisa dipakai: `{mention}` `{user}` `{level}` `{server}` `{roles}`\n"
                "(`{roles}` otomatis kosong kalau gak ada role reward yang didapat)"
            )))

    elif sub == "toggle":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        current = gc.get("leveling_enabled", True)
        gc["leveling_enabled"] = not current
        save_config(cfg)
        state = "diaktifkan" if gc["leveling_enabled"] else "dimatikan"
        color = COLOR_SUCCESS if gc["leveling_enabled"] else COLOR_ERROR
        await ctx.send(embed=base_embed("Leveling System",
            "Sistem leveling **" + state + "** di server ini.", color=color))

    elif sub == "setchannel":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if not args:
            gc["level_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Level channel dinonaktifkan. Notif dikirim ke channel aktif."))
        ch = None
        if ctx.message.channel_mentions:
            ch = ctx.message.channel_mentions[0]
        elif args[0].isdigit():
            ch = ctx.guild.get_channel(int(args[0]))
        if not ch:
            return await ctx.send(embed=error_embed("Channel tidak ditemukan. Gunakan #mention atau channel ID."))
        gc["level_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed("Level-up notif akan dikirim ke " + ch.mention + "."))

    elif sub == "role":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        level_roles = gc.setdefault("level_roles", {})
        action = args[0].lower() if args else ""

        if action == "set":
            if len(args) < 3 or not args[1].isdigit():
                return await ctx.send(embed=error_embed("Usage: `level role set <level> <@role/role_id>`"))
            lvl = int(args[1])
            role = None
            if ctx.message.role_mentions:
                role = ctx.message.role_mentions[0]
            elif args[2].isdigit():
                role = ctx.guild.get_role(int(args[2]))
            if not role:
                return await ctx.send(embed=error_embed("Role tidak ditemukan."))
            level_roles[str(lvl)] = role.id
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Member yang mencapai **Level {lvl}** sekarang otomatis dapat role {role.mention}."))

        elif action == "remove":
            if len(args) < 2 or not args[1].isdigit():
                return await ctx.send(embed=error_embed("Usage: `level role remove <level>`"))
            lvl = args[1]
            if lvl not in level_roles:
                return await ctx.send(embed=error_embed(f"Belum ada role reward untuk level {lvl}."))
            level_roles.pop(lvl, None)
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Role reward untuk level {lvl} dihapus. Role yang udah dimiliki member gak dicabut."))

        elif action == "list":
            if not level_roles:
                return await ctx.send(embed=info_embed("Level Role Rewards", "Belum ada role reward yang di-set."))
            lines = []
            for lvl in sorted(level_roles, key=lambda x: int(x)):
                role = ctx.guild.get_role(level_roles[lvl])
                lines.append(f"**Level {lvl}** → {role.mention if role else '*(role tidak ditemukan)*'}")
            return await ctx.send(embed=info_embed("Level Role Rewards", "\n".join(lines)))

        else:
            await ctx.send(embed=info_embed("Level Role Rewards", (
                "`level role set <level> <@role>` — kasih role otomatis pas member nyampe level segitu\n"
                "`level role remove <level>` — hapus reward level itu\n"
                "`level role list` — lihat semua reward yang aktif\n\n"
                "Role itu stacking — sekali dapat gak akan dicabut walau nanti reward-nya diubah/dihapus."
            )))

    elif sub == "status":
        enabled  = gc.get("leveling_enabled", True)
        lvl_ch   = ctx.guild.get_channel(gc["level_channel"]) if gc.get("level_channel") else None
        xp_range = gc.get("xp_per_message", [15, 25])
        cooldown = gc.get("xp_cooldown", 60)
        embed = base_embed("Leveling Status", None, COLOR_SUCCESS if enabled else COLOR_ERROR)
        embed.add_field(name="Status",     value="Aktif" if enabled else "Mati",                  inline=True)
        embed.add_field(name="Channel",    value=lvl_ch.mention if lvl_ch else "Current channel",  inline=True)
        embed.add_field(name="XP/Message", value=str(xp_range[0]) + "-" + str(xp_range[1]) + " XP", inline=True)
        embed.add_field(name="Cooldown",   value=str(cooldown) + " detik",                        inline=True)
        await ctx.send(embed=embed)

    else:
        enabled = gc.get("leveling_enabled", True)
        status  = "Aktif" if enabled else "Mati"
        await ctx.send(embed=info_embed("Level System",
            "Status: **" + status + "**\n\n"
            "`level toggle` - nyalain/matiin leveling\n"
            "`level setchannel #channel` - set channel notif\n"
            "`level setchannel` - nonaktifkan channel\n"
            "`level role set/remove/list` - kelola role reward per level\n"
            "`level message set/show/reset` - custom deskripsi notif level up\n"
            "`level status` - lihat konfigurasi\n"
            "`level rank [@user]` - lihat rank\n"
            "`level leaderboard` - top 10"))
@bot.command(name="xp")
async def pfx_xp(ctx, sub: str = "", *args):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    sub  = sub.lower()
    gc   = guild_cfg(cfg, ctx.guild.id)
    VALID = ("add","remove","set","setlevel","reset")
    if sub not in VALID:
        return await ctx.send(embed=info_embed("XP", "`xp add/remove/set @user <amount>` · `xp setlevel @user <lvl>` · `xp reset @user`"))
    if not args:
        return await ctx.send(embed=error_embed(f"Usage: `xp {sub} @user [amount]`"))
    try:
        member = ctx.guild.get_member(int(args[0].strip("<@!>")))
        if not member: return await ctx.send(embed=error_embed("Member tidak ditemukan."))
    except ValueError:
        return await ctx.send(embed=error_embed("Mention atau ID yang valid."))
    data = get_member_xp(gc, str(member.id))
    if sub == "reset":
        gc["members_xp"][str(member.id)] = {"xp":0,"level":0,"last_msg_ts":0.0,"messages":0}
        save_config(cfg)
        return await ctx.send(embed=success_embed(f"XP {member.mention} di-reset."))
    if len(args) < 2:
        return await ctx.send(embed=error_embed(f"Usage: `xp {sub} @user <amount>`"))
    try:
        amount = int(args[1])
    except ValueError:
        return await ctx.send(embed=error_embed("Amount harus angka."))
    if sub == "add":
        data["xp"] = max(0, data["xp"] + amount)
        data["level"] = level_from_xp(data["xp"])
        save_config(cfg)
        await ctx.send(embed=success_embed(f"+{amount} XP ke {member.mention} (Total: {data['xp']:,} · Level {data['level']})"))
    elif sub == "remove":
        data["xp"] = max(0, data["xp"] - amount)
        data["level"] = level_from_xp(data["xp"])
        save_config(cfg)
        await ctx.send(embed=success_embed(f"-{amount} XP dari {member.mention} (Total: {data['xp']:,} · Level {data['level']})"))
    elif sub == "set":
        data["xp"] = max(0, amount)
        data["level"] = level_from_xp(data["xp"])
        save_config(cfg)
        await ctx.send(embed=success_embed(f"XP {member.mention} → {amount:,} (Level {data['level']})"))
    elif sub == "setlevel":
        if not 0 <= amount <= 999: return await ctx.send(embed=error_embed("Level 0–999."))
        total = sum(xp_for_level(lv) for lv in range(amount))
        data["xp"] = total; data["level"] = amount
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Level {member.mention} → **{amount}** ({total:,} XP)"))

# ── TICKET ────────────────────────────────────────────────────────

@bot.command(name="ticket")
async def pfx_ticket(ctx, sub: str = "", *, rest: str = ""):
    sub    = sub.lower()
    gc     = guild_cfg(cfg, ctx.guild.id)
    panels = gc["ticket"]["panels"]

    def is_manager() -> bool:
        return ctx.author.id == bot.owner_id or ctx.author.guild_permissions.manage_guild

    def parse_title_desc(body: str, fallback_title: str, fallback_desc: str):
        if "|" in body:
            title, desc = body.split("|", 1)
            title, desc = title.strip(), desc.strip()
        else:
            title, desc = body.strip(), ""
        return (title or fallback_title), (desc or fallback_desc)

    if sub == "setup":
        if not is_manager():
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        parts = rest.split()
        if len(parts) < 3:
            return await ctx.send(embed=error_embed(
                "Usage: `ticket setup <panel_id> <category_id> <log_id> [role_id] [max]`\n"
                "Contoh: `ticket setup support 123456 654321 999999 3`"))
        panel_id = parts[0].lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,32}", panel_id):
            return await ctx.send(embed=error_embed("Panel ID cuma boleh huruf kecil, angka, `-`, `_` (maks 32 karakter)."))
        try:
            cat_id  = int(parts[1]); log_id = int(parts[2])
            role_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
            max_t   = int(parts[4]) if len(parts) > 4 else 1
        except ValueError:
            return await ctx.send(embed=error_embed("Category ID / Log ID / Role ID harus angka."))
        cat    = ctx.guild.get_channel(cat_id)
        log_ch = ctx.guild.get_channel(log_id)
        if not isinstance(cat, discord.CategoryChannel):
            return await ctx.send(embed=error_embed("Category channel tidak ditemukan."))
        if not log_ch:
            return await ctx.send(embed=error_embed("Log channel tidak ditemukan."))
        panel = panels.setdefault(panel_id, {
            "title": "Support Tickets", "description": "Klik tombol untuk membuka support ticket.",
            "message_id": None, "channel_id": None
        })
        panel.update({
            "category": cat_id, "log_channel": log_id,
            "support_role": role_id, "max_tickets": max(1, min(5, max_t))
        })
        save_config(cfg)
        embed = base_embed(f"Ticket Panel `{panel_id}` Configured", None)
        embed.add_field(name="Category",     value=cat.name,                                inline=True)
        embed.add_field(name="Log Channel",  value=log_ch.mention,                          inline=True)
        embed.add_field(name="Support Role", value=f"<@&{role_id}>" if role_id else "None",  inline=True)
        embed.add_field(name="Max Tickets",  value=str(panel["max_tickets"]),                inline=True)
        embed.set_footer(text=f"Lanjut: ticket panel {panel_id} <title> | <description>")
        await ctx.send(embed=embed)

    elif sub == "panel":
        if not is_manager():
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        parts = rest.split(maxsplit=1)
        if not parts:
            return await ctx.send(embed=error_embed("Usage: `ticket panel <panel_id> <title> | <description>`"))
        panel_id = parts[0].lower()
        panel    = panels.get(panel_id)
        if not panel or not panel.get("category"):
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` belum di-setup. Jalankan `ticket setup` dulu."))
        title, desc = parse_title_desc(parts[1] if len(parts) > 1 else "", panel["title"], panel["description"])
        panel["title"], panel["description"] = title, desc
        msg = await ctx.send(embed=base_embed(title, desc, color=COLOR_PRIMARY), view=TicketOpenView(panel_id))
        panel["message_id"], panel["channel_id"] = msg.id, msg.channel.id
        save_config(cfg)

    elif sub == "edit":
        if not is_manager():
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            return await ctx.send(embed=error_embed("Usage: `ticket edit <panel_id> <title> | <description>`"))
        panel_id = parts[0].lower()
        panel    = panels.get(panel_id)
        if not panel:
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` tidak ditemukan."))
        title, desc = parse_title_desc(parts[1], panel["title"], panel["description"])
        panel["title"], panel["description"] = title, desc
        save_config(cfg)
        edited = False
        if panel.get("message_id") and panel.get("channel_id"):
            ch = ctx.guild.get_channel(panel["channel_id"])
            if ch:
                try:
                    msg = await ch.fetch_message(panel["message_id"])
                    await msg.edit(embed=base_embed(title, desc, color=COLOR_PRIMARY))
                    edited = True
                except Exception:
                    pass
        note = "Panel message ikut ter-update." if edited else "Config tersimpan, tapi panel message lama tidak ditemukan/sudah dihapus — kirim ulang dengan `ticket panel`."
        await ctx.send(embed=success_embed(f"Panel `{panel_id}` diupdate.\n{note}"))

    elif sub == "list":
        if not panels:
            return await ctx.send(embed=info_embed("Ticket Panels", "Belum ada panel yang di-setup."))
        embed = base_embed("Ticket Panels", None)
        for pid, p in panels.items():
            cat = ctx.guild.get_channel(p.get("category"))    if p.get("category")    else None
            log = ctx.guild.get_channel(p.get("log_channel")) if p.get("log_channel") else None
            embed.add_field(
                name=f"`{pid}` — {p.get('title', '?')}",
                value=f"Category: {cat.mention if cat else '—'} · Log: {log.mention if log else '—'} · Max: {p.get('max_tickets', 1)}",
                inline=False
            )
        await ctx.send(embed=embed)

    elif sub == "delete":
        if not is_manager():
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        panel_id = rest.strip().lower()
        if panel_id not in panels:
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` tidak ditemukan."))
        del panels[panel_id]
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Panel `{panel_id}` dihapus. Ticket yang masih terbuka dari panel ini tidak otomatis ditutup."))

    elif sub == "close":
        async def _respond(**kw):
            await ctx.send(**kw)
        await close_ticket_channel(ctx.guild, ctx.channel, ctx.author, rest.strip(), _respond)

    else:
        await ctx.send(embed=info_embed("Ticket", (
            "`ticket setup <panel_id> <cat_id> <log_id> [role_id] [max]`\n"
            "`ticket panel <panel_id> <title> | <description>`\n"
            "`ticket edit <panel_id> <title> | <description>`\n"
            "`ticket list`\n"
            "`ticket delete <panel_id>`\n"
            "`ticket close [reason]`\n\n"
            "Setiap panel punya category, log channel, dan role support sendiri-sendiri — "
            "jadi tiap jenis ticket bisa dipisah log-nya."
        )))

# ── GIVEAWAY ─────────────────────────────────────────────────────

@bot.command(name="giveaway")
async def pfx_giveaway(ctx, sub: str = "", *args):
    sub = sub.lower()
    if sub == "list":
        gws = [gw for gw in active_giveaways.values() if gw.get("guild_id") == ctx.guild.id]
        if not gws: return await ctx.send(embed=info_embed("Giveaways", "Tidak ada giveaway aktif."))
        embed = discord.Embed(title="Active Giveaways", color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
        for gw in gws[:10]:
            ends_dt = datetime.datetime.utcfromtimestamp(gw["ends_ts"]).replace(tzinfo=datetime.timezone.utc)
            ch = bot.get_channel(gw["channel_id"])
            embed.add_field(name=gw["prize"],
                value=f"Channel: {ch.mention if ch else '?'} · Ends: {discord.utils.format_dt(ends_dt,'R')}\nWinners: {gw['winner_count']} · Entries: {len(gw['entries'])} · ID: `{gw['message_id']}`",
                inline=False)
        await ctx.send(embed=embed)
    elif sub == "end":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if not args: return await ctx.send(embed=error_embed("Usage: `giveaway end <message_id>`"))
        try: mid = int(args[0])
        except ValueError: return await ctx.send(embed=error_embed("ID harus angka."))
        gw = active_giveaways.get(mid)
        if not gw or gw["guild_id"] != ctx.guild.id: return await ctx.send(embed=error_embed("Giveaway tidak ditemukan."))
        await ctx.send(embed=info_embed("", f"Mengakhiri **{gw['prize']}**..."))
        await end_giveaway(gw)
    elif sub == "reroll":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if not args: return await ctx.send(embed=error_embed("Usage: `giveaway reroll <message_id> [count]`"))
        try: mid = int(args[0]); count = int(args[1]) if len(args) > 1 else 1
        except ValueError: return await ctx.send(embed=error_embed("ID dan count harus angka."))
        try: msg = await ctx.channel.fetch_message(mid)
        except discord.NotFound: return await ctx.send(embed=error_embed("Pesan tidak ditemukan."))
        entries = []
        target_emoji = ICON_GIVEAWAY_REACT if ICON_GIVEAWAY_REACT else "🎉"
        for reaction in msg.reactions:
            if str(reaction.emoji) == target_emoji or str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot: entries.append(user.id)
                break
        if not entries: return await ctx.send(embed=error_embed("Tidak ada peserta."))
        count   = max(1, min(count, len(entries)))
        winners = random.sample(list(set(entries)), count)
        ws      = " ".join(f"<@{w}>" for w in winners)
        embed   = discord.Embed(title=f"{e(ICON_WINNER, '🏆')} Giveaway Rerolled!".strip(), description=f"Pemenang baru: {ws}", color=COLOR_SUCCESS, timestamp=discord.utils.utcnow())
        embed.set_footer(text=BOT_NAME)
        await ctx.send(content=ws, embed=embed)
    elif sub == "start":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if len(args) < 3:
            return await ctx.send(embed=error_embed("Usage: `giveaway start <durasi> <winners> <prize>`\nOptional: `--role <id>` `--winrole <id>`"))
        dur_str = args[0].lower()
        m_dur   = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", dur_str)
        if not m_dur or not any(m_dur.group(x) for x in (1,2,3)):
            return await ctx.send(embed=error_embed("Format durasi: `1h`, `30m`, `2h30m`, `1d`"))
        dur_secs = int(m_dur.group(1) or 0)*86400 + int(m_dur.group(2) or 0)*3600 + int(m_dur.group(3) or 0)*60
        if not dur_secs or dur_secs > 7*86400:
            return await ctx.send(embed=error_embed("Durasi 1 menit – 7 hari."))
        try:
            winner_count = int(args[1])
            if not 1 <= winner_count <= 20: raise ValueError
        except ValueError:
            return await ctx.send(embed=error_embed("Winners 1–20."))
        rest = list(args[2:]); req_role_id = win_role_id = None; prize_parts = []; i = 0
        while i < len(rest):
            if rest[i] == "--role" and i+1 < len(rest):
                try: req_role_id = int(rest[i+1])
                except ValueError: pass
                i += 2
            elif rest[i] == "--winrole" and i+1 < len(rest):
                try: win_role_id = int(rest[i+1])
                except ValueError: pass
                i += 2
            else:
                prize_parts.append(rest[i]); i += 1
        prize = " ".join(prize_parts).strip()
        if not prize: return await ctx.send(embed=error_embed("Nama hadiah tidak boleh kosong."))
        req_role = ctx.guild.get_role(req_role_id) if req_role_id else None
        win_role = ctx.guild.get_role(win_role_id) if win_role_id else None
        ends_ts  = discord.utils.utcnow().timestamp() + dur_secs
        gw = {"prize": prize, "description": "", "winner_count": winner_count,
              "host_id": ctx.author.id, "channel_id": ctx.channel.id, "guild_id": ctx.guild.id,
              "ends_ts": ends_ts, "entries": [], "winners": [], "ended": False, "message_id": 0,
              "required_role": req_role.id if req_role else None,
              "winner_role_id": win_role.id if win_role else None}
        gw_embed = build_giveaway_embed(gw)
        try:
            msg = await ctx.channel.send(embed=gw_embed)
            await msg.add_reaction(ICON_GIVEAWAY_REACT if ICON_GIVEAWAY_REACT else "🎉")
        except discord.Forbidden:
            return await ctx.send(embed=error_embed("Bot tidak bisa kirim pesan di channel ini."))
        gw["message_id"] = msg.id
        active_giveaways[msg.id] = gw
        async def _timer():
            await asyncio.sleep(dur_secs)
            if msg.id in active_giveaways: await end_giveaway(active_giveaways[msg.id])
        asyncio.create_task(_timer())
        ends_dt = datetime.datetime.utcfromtimestamp(ends_ts).replace(tzinfo=datetime.timezone.utc)
        confirm = success_embed(f"Giveaway dimulai!\n\nPrize: {prize}\nWinners: {winner_count}\nEnds: {discord.utils.format_dt(ends_dt,'R')}")
        if req_role: confirm.add_field(name="Required Role", value=req_role.mention, inline=True)
        if win_role: confirm.add_field(name="Winner Role",   value=win_role.mention, inline=True)
        await ctx.send(embed=confirm)
    else:
        await ctx.send(embed=info_embed("Giveaway",
            "`giveaway start <durasi> <winners> <prize>`\n"
            "  Optional: `--role <id>` `--winrole <id>`\n"
            "`giveaway end <msg_id>` · `giveaway reroll <msg_id>` · `giveaway list`"))

# ── LANGUAGE ─────────────────────────────────────────────────────

@bot.command(name="language")
async def pfx_language(ctx, action: str = "list", lang: str = ""):
    if action.lower() == "set":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if lang not in LANGUAGES:
            return await ctx.send(embed=error_embed(f"Valid codes: {', '.join(LANGUAGES.keys())}"))
        guild_cfg(cfg, ctx.guild.id)["language"] = lang
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Bahasa diatur ke **{LANGUAGES[lang]}**."))
    else:
        cur   = guild_cfg(cfg, ctx.guild.id).get("language", "en")
        lines = "\n".join(f"{'[OK]' if k==cur else '[ ]'} `{k}` — {v}" for k, v in LANGUAGES.items())
        await ctx.send(embed=info_embed("Supported Languages", lines))

# ── ANTISPAM HONEYPOT ─────────────────────────────────────────────

@bot.command(name="antispam")
async def pfx_antispam(ctx, sub: str = "", *, args: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
    gc  = guild_cfg(cfg, ctx.guild.id)
    sub = sub.lower()
    if sub == "setchannel":
        if not args:
            gc["spam_trap_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Honeypot channel dinonaktifkan."))
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else (ctx.guild.get_channel(int(args.strip())) if args.strip().isdigit() else None)
        if not ch: return await ctx.send(embed=error_embed("Channel tidak ditemukan."))
        gc["spam_trap_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=base_embed("Honeypot Aktif", ch.mention + " — siapapun yang kirim pesan di sini langsung di-ban.", color=COLOR_ERROR))
    elif sub == "status":
        trap = gc.get("spam_trap_channel")
        ch   = ctx.guild.get_channel(trap) if trap else None
        await ctx.send(embed=base_embed("Honeypot Status", "Aktif di " + ch.mention if ch else "Tidak aktif.", color=COLOR_ERROR if ch else COLOR_INFO))
    else:
        await ctx.send(embed=info_embed("Antispam Honeypot", "`antispam setchannel #channel`\n`antispam setchannel` (nonaktifkan)\n`antispam status`"))

# ── ANTI-NUKE ────────────────────────────────────────────────────

@bot.command(name="antinuke")
async def pfx_antinuke(ctx, sub: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.administrator:
        return await ctx.send(embed=error_embed("Cuma Administrator atau owner yang bisa atur anti-nuke."))
    gc  = guild_cfg(cfg, ctx.guild.id)
    ac  = gc.setdefault("antinuke", {"enabled": False, "log_channel": None, "whitelist": [], "punishment": "strip_roles"})
    sub = sub.lower()

    if sub == "enable":
        me = ctx.guild.me
        if not me.guild_permissions.view_audit_log:
            return await ctx.send(embed=error_embed("Bot butuh permission **View Audit Log** dulu buat ngaktifin anti-nuke."))
        ac["enabled"] = True
        save_config(cfg)
        await ctx.send(embed=success_embed(
            "Anti-Nuke **AKTIF**.\nDeteksi: mass channel delete/create, mass role delete, mass ban/kick, "
            "mass webhook create, dan pemberian permission Administrator mendadak.\n\n"
            "Jangan lupa: `antinuke logchannel #channel` biar ada laporan kalau ke-trigger."
        ))

    elif sub == "disable":
        ac["enabled"] = False
        save_config(cfg)
        await ctx.send(embed=success_embed("Anti-Nuke dinonaktifkan."))

    elif sub == "logchannel":
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else None
        if not ch:
            ac["log_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Log channel anti-nuke dikosongkan."))
        ac["log_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Laporan anti-nuke bakal dikirim ke {ch.mention}."))

    elif sub == "punishment":
        choice = rest.strip().lower()
        if choice not in ("strip_roles", "kick", "ban"):
            return await ctx.send(embed=error_embed("Pilihan: `strip_roles`, `kick`, atau `ban`."))
        ac["punishment"] = choice
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Tindakan anti-nuke di-set ke **{choice}**."))

    elif sub == "whitelist":
        parts  = rest.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        wl     = ac.setdefault("whitelist", [])
        if action == "add" and ctx.message.mentions:
            u = ctx.message.mentions[0]
            if u.id not in wl:
                wl.append(u.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"{u.mention} sekarang di-whitelist dari anti-nuke."))
        elif action == "remove" and ctx.message.mentions:
            u = ctx.message.mentions[0]
            if u.id in wl:
                wl.remove(u.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"{u.mention} dihapus dari whitelist."))
        elif action == "list":
            lines = [f"<@{uid}>" for uid in wl] or ["*(kosong)*"]
            await ctx.send(embed=info_embed("Anti-Nuke Whitelist", "\n".join(lines)))
        else:
            await ctx.send(embed=info_embed("Anti-Nuke Whitelist", "`antinuke whitelist add @user`\n`antinuke whitelist remove @user`\n`antinuke whitelist list`"))

    elif sub == "status":
        status = "🟢 Aktif" if ac.get("enabled") else "🔴 Tidak aktif"
        log_ch = ctx.guild.get_channel(ac.get("log_channel")) if ac.get("log_channel") else None
        embed = base_embed("Anti-Nuke Status", None, color=COLOR_ERROR if ac.get("enabled") else COLOR_INFO)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Tindakan", value=f"`{ac.get('punishment','strip_roles')}`", inline=True)
        embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "*(belum di-set)*", inline=True)
        embed.add_field(name="Whitelist", value=str(len(ac.get("whitelist", []))) + " user", inline=True)
        embed.add_field(name="Deteksi", value="\n".join(f"• {v}" for v in antinuke.ACTION_LABELS.values()), inline=False)
        await ctx.send(embed=embed)

    else:
        await ctx.send(embed=info_embed("Anti-Nuke", (
            "`antinuke enable` — aktifin proteksi\n"
            "`antinuke disable` — matiin\n"
            "`antinuke logchannel #channel` — channel buat laporan\n"
            "`antinuke punishment strip_roles/kick/ban` — tindakan ke pelaku\n"
            "`antinuke whitelist add/remove/list @user` — orang yang di-skip dari deteksi\n"
            "`antinuke status` — lihat konfigurasi sekarang\n\n"
            "Owner bot dan pemilik server otomatis ke-whitelist, gak perlu ditambahin manual."
        )))

# ── OWNER COMMANDS ────────────────────────────────────────────────

@bot.command(name="maintenance")
@is_owner()
async def pfx_maintenance(ctx, action: str = "", *, reason: str = ""):
    action = action.lower()
    m      = cfg.setdefault("maintenance", {"enabled": False, "reason": "", "since": None})
    if action == "on":
        m["enabled"] = True
        m["reason"]  = reason.strip()
        m["since"]   = discord.utils.utcnow().isoformat()
        save_config(cfg)
        try:
            await bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.playing, name="Under Maintenance ⚠️"),
                status=discord.Status.dnd
            )
        except Exception:
            pass
        desc = f"**{BOT_NAME}** sekarang dalam mode **maintenance**.\nSemua command ditutup untuk semua orang kecuali owner."
        if m["reason"]:
            desc += f"\n\n**Alasan:** {m['reason']}"
        await ctx.send(embed=warning_embed("Maintenance Mode: ON", desc))
    elif action == "off":
        m["enabled"] = False
        m["reason"]  = ""
        m["since"]   = None
        save_config(cfg)
        await ctx.send(embed=success_embed(f"**{BOT_NAME}** sudah normal lagi. Semua command dibuka kembali."))
    elif action == "status":
        if m.get("enabled"):
            since = m.get("since")
            since_txt = discord.utils.format_dt(datetime.datetime.fromisoformat(since), "R") if since else "?"
            desc = f"Status: **AKTIF** — sejak {since_txt}"
            if m.get("reason"):
                desc += f"\n**Alasan:** {m['reason']}"
        else:
            desc = "Status: **Tidak aktif.** Bot berjalan normal."
        await ctx.send(embed=info_embed("Maintenance Status", desc))
    else:
        await ctx.send(embed=info_embed("Maintenance",
            "`maintenance on [alasan]` — kunci semua command kecuali owner\n"
            "`maintenance off` — buka lagi\n"
            "`maintenance status` — cek status sekarang"))

@bot.command(name="premiumlock")
@is_owner()
async def pfx_premiumlock(ctx, action: str = "", *, cmd_name: str = ""):
    action = action.lower()
    locked = cfg.setdefault("premium_commands", [])
    cmd_name = cmd_name.strip().lower()
    if action == "add":
        if not cmd_name:
            return await ctx.send(embed=error_embed("Sebutkan nama command. Contoh: `premiumlock add addemoji`"))
        if cmd_name in OWNER_ONLY_CMDS:
            return await ctx.send(embed=error_embed("Command owner-only tidak bisa dikunci ke Premium."))
        if cmd_name not in locked:
            locked.append(cmd_name)
            save_config(cfg)
        await sync_premium_descriptions()
        await ctx.send(embed=success_embed(f"Command `{cmd_name}` sekarang **Premium only** (prefix & slash)."))
    elif action == "remove":
        if cmd_name in locked:
            locked.remove(cmd_name)
            save_config(cfg)
            await sync_premium_descriptions()
            await ctx.send(embed=success_embed(f"Command `{cmd_name}` dibuka lagi untuk semua orang."))
        else:
            await ctx.send(embed=error_embed(f"Command `{cmd_name}` tidak ada di daftar premium lock."))
    elif action == "list":
        if not locked:
            return await ctx.send(embed=info_embed("Premium Locked Commands", "Belum ada command yang dikunci ke Premium."))
        await ctx.send(embed=info_embed("Premium Locked Commands", "\n".join(f"`{c}`" for c in locked)))
    else:
        await ctx.send(embed=info_embed("Premium Lock",
            "`premiumlock add <command>` — kunci command ke Premium only\n"
            "`premiumlock remove <command>` — buka lagi command\n"
            "`premiumlock list` — lihat semua command yang dikunci\n\n"
            "Nama command pakai nama slash-nya, contoh untuk subcommand: `ticket setup`."))

@bot.command(name="noprefix")
@is_owner()
async def pfx_noprefix(ctx, action: str = "", *, rest: str = ""):
    action     = action.lower()
    np_users   = cfg.setdefault("no_prefix_users",  [])
    np_guilds  = cfg.setdefault("no_prefix_guilds", [])
    np_expiry  = cfg.setdefault("no_prefix_expiry", {})

    if action == "list":
        u_lines = []
        for uid in np_users:
            exp_str = np_expiry.get(str(uid))
            if exp_str:
                try:
                    exp = datetime.datetime.fromisoformat(exp_str)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=datetime.timezone.utc)
                    exp_txt = discord.utils.format_dt(exp, "R")
                except Exception:
                    exp_txt = "?"
            else:
                exp_txt = "Permanent"
            u_lines.append(f"<@{uid}> (`{uid}`) — {exp_txt}")
        u_lines = u_lines or ["*(none)*"]
        g_lines = []
        for gid in np_guilds:
            g = bot.get_guild(gid)
            g_lines.append(f"**{g.name}** (`{gid}`)" if g else f"`{gid}`")
        g_lines = g_lines or ["*(none)*"]
        embed = base_embed("No-Prefix Access List", None)
        embed.add_field(name="Users",  value="\n".join(u_lines), inline=False)
        embed.add_field(name="Guilds", value="\n".join(g_lines), inline=False)
        return await ctx.send(embed=embed)

    if action not in ("grant", "revoke"):
        return await ctx.send(embed=info_embed("No-Prefix", (
            "`noprefix grant @user/guild_id [durasi]`\n"
            "`noprefix revoke @user/guild_id`\n"
            "`noprefix list`\n\n"
            "Durasi cuma berlaku untuk user (bukan guild). Contoh: `7d`, `24h`, `30m`, "
            "atau kosongkan/`permanent` untuk selamanya."
        )))

    parts = rest.split(maxsplit=1)
    if not parts:
        return await ctx.send(embed=error_embed("Masukkan @user atau guild ID."))
    target_tok = parts[0]
    duration   = parts[1].strip().lower() if len(parts) > 1 else ""
    uid_match  = re.match(r"<@!?(\d+)>|(\d{17,20})", target_tok.strip())
    if not uid_match:
        return await ctx.send(embed=error_embed("Target tidak valid."))
    parsed_id = int(uid_match.group(1) or uid_match.group(2))

    g = bot.get_guild(parsed_id)
    if g:
        if action == "grant":
            if parsed_id not in np_guilds: np_guilds.append(parsed_id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"No-prefix diaktifkan untuk server **{g.name}**."))
        else:
            if parsed_id in np_guilds: np_guilds.remove(parsed_id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"No-prefix dicabut dari server **{g.name}**."))
        return

    try:
        user = await bot.fetch_user(parsed_id)
    except Exception:
        return await ctx.send(embed=error_embed("User/Guild tidak ditemukan."))

    if action == "grant":
        expiry_dt = None
        if duration and duration != "permanent":
            m = re.fullmatch(r"(\d+)(d|h|m)", duration)
            if not m:
                return await ctx.send(embed=error_embed("Format durasi: `7d`, `24h`, `30m`, atau `permanent`."))
            amount = int(m.group(1)); unit = m.group(2)
            delta  = {"d": datetime.timedelta(days=amount), "h": datetime.timedelta(hours=amount), "m": datetime.timedelta(minutes=amount)}[unit]
            expiry_dt = datetime.datetime.now(datetime.timezone.utc) + delta
        if parsed_id not in np_users:
            np_users.append(parsed_id)
        if expiry_dt:
            np_expiry[str(parsed_id)] = expiry_dt.isoformat()
        else:
            np_expiry.pop(str(parsed_id), None)
        save_config(cfg)
        dur_display = "Permanent" if not expiry_dt else discord.utils.format_dt(expiry_dt, "R")
        try:
            dm = base_embed(
                "No-Prefix Access Granted!",
                f"Kamu bisa gunain command {BOT_NAME} tanpa prefix!\nCukup ketik nama command langsung.\nExpires: {dur_display}",
                color=COLOR_SUCCESS
            )
            await user.send(embed=dm)
        except Exception:
            pass
        await ctx.send(embed=success_embed(f"No-prefix diaktifkan untuk {user.mention}.\nExpires: {dur_display}"))
    else:
        if parsed_id in np_users: np_users.remove(parsed_id)
        np_expiry.pop(str(parsed_id), None)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"No-prefix dicabut dari {user.mention}."))

@bot.command(name="botrole")
@is_owner()
async def pfx_botrole(ctx, action: str = "", *args):
    action    = action.lower()
    bot_roles = cfg.setdefault("bot_roles", {})
    role_sync = cfg.setdefault("role_sync", {})
    valid_tiers = ("staff", "moderator", "server_manager", "management", "developer")

    if action == "list":
        if not bot_roles: return await ctx.send(embed=info_embed("Bot Roles (Manual)", "Belum ada assignment manual."))
        lines = []
        for uid_str, r in bot_roles.items():
            user = bot.get_user(int(uid_str))
            name = user.display_name if user else f"ID {uid_str}"
            lines.append(f"**{name}** → {r.capitalize()}")
        return await ctx.send(embed=info_embed("Bot Roles (Manual)", "\n".join(lines)))

    if action == "sync":
        sub = args[0].lower() if args else ""
        if sub == "list":
            guild = get_support_guild()
            lines = []
            for tier in valid_tiers:
                role_id = role_sync.get(tier)
                if not role_id:
                    lines.append(f"**{tier.capitalize()}** → *(belum di-set)*")
                    continue
                role = guild.get_role(role_id) if guild else None
                lines.append(f"**{tier.capitalize()}** → {role.mention if role else f'`{role_id}` (role tidak ditemukan)'}")
            note = "" if guild else "\n\n⚠️ `SUPPORT_SERVER_ID` belum di-set di environment, sync tidak akan jalan."
            return await ctx.send(embed=info_embed("Bot Role Sync", "\n".join(lines) + note))
        if sub == "remove":
            tier = args[1].lower() if len(args) > 1 else ""
            if tier not in valid_tiers:
                return await ctx.send(embed=error_embed("Tier valid: `staff`, `moderator`, `server_manager`, `management`, `developer`."))
            role_sync.pop(tier, None)
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Sync role untuk **{tier.capitalize()}** dihapus."))
        # botrole sync <tier> <role_id/mention>
        if len(args) < 2:
            return await ctx.send(embed=info_embed("Bot Role Sync", (
                "`botrole sync <staff/moderator/server_manager/management/developer> <role_id atau @role>` — hubungkan role Discord di support server ke badge\n"
                "`botrole sync remove <tier>` — putuskan hubungan\n"
                "`botrole sync list` — lihat mapping sekarang\n\n"
                "Begitu di-set, siapapun yang punya role itu di support server otomatis dapat badge-nya "
                "di `profile` — gak perlu `botrole set` manual lagi."
            )))
        tier = args[0].lower()
        if tier not in valid_tiers:
            return await ctx.send(embed=error_embed("Tier valid: `staff`, `moderator`, `server_manager`, `management`, `developer`."))
        role_match = re.match(r"<@&(\d+)>|(\d{17,20})", args[1].strip())
        if not role_match:
            return await ctx.send(embed=error_embed("Masukkan role ID atau mention role yang valid."))
        role_id = int(role_match.group(1) or role_match.group(2))
        guild = get_support_guild()
        if not guild:
            return await ctx.send(embed=error_embed("`SUPPORT_SERVER_ID` belum di-set di environment bot."))
        disc_role = guild.get_role(role_id)
        if not disc_role:
            return await ctx.send(embed=error_embed("Role tidak ditemukan di support server."))
        role_sync[tier] = role_id
        save_config(cfg)
        info = BOT_ROLE_BADGES[tier]
        badge_tag = (info["emoji"] + " ") if info.get("emoji") else ""
        return await ctx.send(embed=success_embed(
            f"Role {disc_role.mention} sekarang otomatis kasih badge {badge_tag}**{info['label']}**.\n"
            f"Siapapun member support server yang punya role ini langsung ke-update badge-nya."
        ))

    if not args:
        return await ctx.send(embed=info_embed("Bot Role", (
            "`botrole set @user <staff/moderator/server_manager/management/developer>` — assign manual (untuk yang di luar support server)\n"
            "`botrole remove @user` — cabut manual\n"
            "`botrole list` — lihat assignment manual\n"
            "`botrole sync <tier> <role_id>` — auto-sync dari role Discord di support server"
        )))

    member = None
    for tok in args:
        m = re.match(r"<@!?(\d+)>|(\d{17,20})", tok.strip())
        if m:
            uid = int(m.group(1) or m.group(2))
            member = ctx.guild.get_member(uid)
            break
    if not member:
        return await ctx.send(embed=error_embed("User tidak ditemukan di server ini."))
    role = next((a.lower() for a in args if a.lower() in valid_tiers), "")

    if action == "set":
        if role not in valid_tiers:
            return await ctx.send(embed=error_embed("Role valid: `staff`, `moderator`, `server_manager`, `management`, `developer`"))
        bot_roles[str(member.id)] = role
        save_config(cfg)
        info = BOT_ROLE_BADGES[role]
        badge_tag = (info["emoji"] + " ") if info.get("emoji") else ""
        embed = discord.Embed(title="Bot Role Assigned", description=f"{member.mention} → {badge_tag}**{info['label']}**", color=info["color"], timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            dm = discord.Embed(title="Bot Role Granted!", description=f"Kamu mendapat role {badge_tag}**{info['label']}** di {BOT_NAME}!\nCek profil: `profile`", color=info["color"])
            await member.send(embed=dm)
        except Exception: pass
        await ctx.send(embed=embed)
    elif action == "remove":
        if str(member.id) not in bot_roles: return await ctx.send(embed=error_embed(f"{member.display_name} tidak punya bot role manual."))
        removed = bot_roles.pop(str(member.id))
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Bot role manual **{removed.capitalize()}** dihapus dari {member.mention}."))

@bot.command(name="grantpremium")
@is_owner()
async def pfx_grantpremium(ctx, member: discord.Member = None, duration: str = ""):
    if not member:
        return await ctx.send(embed=info_embed("Grant Premium", "`grantpremium @user <7d/30d/permanent>` · `grantpremium @user revoke`"))
    premium_users  = cfg.setdefault("premium_users",  [])
    premium_expiry = cfg.setdefault("premium_expiry", {})
    if duration.lower() == "revoke":
        if member.id in premium_users: premium_users.remove(member.id)
        premium_expiry.pop(str(member.id), None)
        save_config(cfg)
        try:
            await member.send(embed=base_embed("Premium Ended", f"Premium {BOT_NAME} kamu telah berakhir. Akses command premium dan no-prefix ikut dicabut.", color=COLOR_ERROR))
        except Exception: pass
        return await ctx.send(embed=success_embed(f"Premium dicabut dari {member.mention}."))
    expiry_dt = None
    if duration.lower() != "permanent":
        m = re.fullmatch(r"(\d+)(d|h|m)", duration.lower())
        if not m: return await ctx.send(embed=error_embed("Format: `7d`, `30d`, `24h`, `permanent`"))
        amount = int(m.group(1)); unit = m.group(2)
        delta  = {"d": datetime.timedelta(days=amount), "h": datetime.timedelta(hours=amount), "m": datetime.timedelta(minutes=amount)}[unit]
        expiry_dt = datetime.datetime.now(datetime.timezone.utc) + delta
    if member.id not in premium_users: premium_users.append(member.id)
    if expiry_dt: premium_expiry[str(member.id)] = expiry_dt.isoformat()
    else: premium_expiry.pop(str(member.id), None)
    save_config(cfg)
    dur_display = "Permanent" if not expiry_dt else discord.utils.format_dt(expiry_dt, "R")
    embed = discord.Embed(title="Premium Granted!", description=f"{member.mention} sekarang **Premium**!\nExpires: {dur_display}", color=COLOR_WARNING, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    try:
        dm = discord.Embed(
            title="Premium Activated!",
            description=f"Premium {BOT_NAME} aktif!\nExpires: {dur_display}\n\nSemua command premium terbuka dan **no-prefix otomatis aktif** — cukup ketik nama command tanpa `!vx`.",
            color=COLOR_WARNING
        )
        await member.send(embed=dm)
    except Exception: pass
    await ctx.send(embed=embed)

@bot.command(name="blacklist")
@is_owner()
async def pfx_blacklist(ctx, action: str = "", guild_id: str = ""):
    bl = cfg.setdefault("blacklisted_guilds", [])
    if action == "add":
        try: gid = int(guild_id)
        except ValueError: return await ctx.send(embed=error_embed("Guild ID harus angka."))
        if gid not in bl: bl.append(gid)
        save_config(cfg)
        g = bot.get_guild(gid)
        if g:
            try: await g.leave()
            except Exception: pass
        await ctx.send(embed=success_embed(f"Guild `{gid}` di-blacklist dan bot leave."))
    elif action == "remove":
        try: gid = int(guild_id)
        except ValueError: return await ctx.send(embed=error_embed("Guild ID harus angka."))
        if gid in bl: bl.remove(gid)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Guild `{gid}` di-unblacklist."))
    elif action == "list":
        if not bl: return await ctx.send(embed=info_embed("Blacklist", "Tidak ada guild yang di-blacklist."))
        lines = []
        for gid in bl:
            g = bot.get_guild(gid)
            lines.append(f"**{g.name}** (`{gid}`)" if g else f"`{gid}`")
        await ctx.send(embed=info_embed("Blacklisted Guilds", "\n".join(lines)))
    else:
        await ctx.send(embed=info_embed("Blacklist", "`blacklist add <guild_id>`\n`blacklist remove <guild_id>`\n`blacklist list`"))

@bot.command(name="vxleave")
@is_owner()
async def pfx_vxleave(ctx, guild_id: str = ""):
    if not guild_id:
        await ctx.send(embed=info_embed("Leave Guild", "`vxleave <guild_id>`"))
        return
    try: gid = int(guild_id)
    except ValueError: return await ctx.send(embed=error_embed("Guild ID harus angka."))
    g = bot.get_guild(gid)
    if not g: return await ctx.send(embed=error_embed("Bot tidak ada di guild tersebut."))
    await ctx.send(embed=success_embed(f"Leaving **{g.name}**..."))
    await g.leave()

# ── HELP ─────────────────────────────────────────────────────────

@bot.command(name="help")
async def pfx_help(ctx):
    has_np = user_has_no_prefix(ctx.guild, ctx.author)
    embed = discord.Embed(
        title=f"{BOT_NAME} — Command Reference",
        description=(
            f"*{BOT_TAGLINE}*\n\n"
            f"Prefix: **`!vx`** · **`!v`** (alias)\n"
            + ("✨ **No-prefix aktif** — ketik command langsung!\n" if has_np else "")
            + "\u200b"
        ),
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    def sec(icon_var, name):
        return (icon_var + " " if icon_var else "") + name

    embed.add_field(name=sec(ICON_MODERATION, "Moderation"), value=(
        "`kick` · `ban` · `unban` · `timeout` · `untimeout`\n"
        "`warn` · `warnings` · `unwarn` · `clearwarnings`\n"
        "`purge` · `lock` · `unlock` · `slowmode`"
    ), inline=False)
    embed.add_field(name=sec(ICON_ROLE, "Role & Voice"),
        value="`addrole` · `removerole` · `move`", inline=False)
    embed.add_field(name=sec(ICON_INFO, "Info"),
        value="`userinfo` · `serverinfo` · `avatar` · `ping` · `addemoji` · `profile`", inline=False)
    embed.add_field(name=sec(ICON_TICKET, "Ticket"),
        value="`ticket setup` · `ticket panel` · `ticket edit` · `ticket list` · `ticket delete` · `ticket close`", inline=False)
    embed.add_field(name=sec(ICON_LEVEL, "Level & XP"),
        value="`rank` · `leaderboard` (alias `lb`) · `level toggle/setchannel/status` · `xp`", inline=False)
    embed.add_field(name=sec(ICON_GIVEAWAY, "Giveaway"),
        value="`giveaway start/end/reroll/list`\n`--role <id>` · `--winrole <id>`", inline=False)
    embed.add_field(name=sec(ICON_ANTISPAM, "Antispam"),
        value="`antispam setchannel #ch` · `antispam status`", inline=False)
    embed.add_field(name=sec(ICON_ANTINUKE, "Anti-Nuke"),
        value="`antinuke enable/disable` · `antinuke logchannel` · `antinuke punishment` · `antinuke whitelist` · `antinuke status`", inline=False)
    embed.add_field(name=sec(ICON_BOOST, "Server Boost"),
        value="`/boostconfig` (slash only) — atur channel & tampilan notifikasi boost", inline=False)
    embed.add_field(name=sec(ICON_LANGUAGE, "Language"),
        value="`language list` · `language set <code>`", inline=False)
    # Catatan: section Owner Only SENGAJA tidak pernah ditaruh di sini.
    # !vx help selalu ngirim pesan publik ke channel — kalau owner yang jalanin,
    # command owner-only bakal ikut kebaca semua orang yang ada di channel itu.
    # Command owner ada sendiri di `ownerhelp`, yang dikirim lewat DM.
    embed.set_footer(text=BOT_NAME + " v" + BOT_VERSION + " • " + BOT_TAGLINE)
    await ctx.send(embed=embed)

@bot.command(name="ownerhelp")
@is_owner()
async def pfx_ownerhelp(ctx):
    """Reference command owner-only — selalu dikirim lewat DM biar gak kebaca orang lain di channel."""
    embed = discord.Embed(
        title=f"{e(ICON_OWNER, '👑')} {BOT_NAME} — Owner Command Reference".strip(),
        description="Daftar ini cuma dikirim ke DM kamu, gak pernah ditampilin di channel publik.",
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Maintenance", value="`maintenance on [alasan]` · `maintenance off` · `maintenance status`", inline=False)
    embed.add_field(name="No-Prefix", value="`noprefix grant @user [durasi]` · `noprefix revoke @user` · `noprefix list`\nDurasi: `7d` / `24h` / `30m` / kosongkan untuk permanent.", inline=False)
    embed.add_field(name="Bot Role", value="`botrole set @user <role>` · `botrole remove @user` · `botrole list`\n`botrole sync <tier> <role_id>` — auto badge dari role Discord di support server", inline=False)
    embed.add_field(name="Premium", value="`grantpremium @user <durasi>` · `grantpremium @user revoke`", inline=False)
    embed.add_field(name="Premium Lock", value="`premiumlock add <command>` · `premiumlock remove <command>` · `premiumlock list`", inline=False)
    embed.add_field(name="Blacklist", value="`blacklist add <id>` · `blacklist remove <id>` · `blacklist list`", inline=False)
    embed.add_field(name="Other", value="`vxleave <guild_id>`", inline=False)
    embed.set_footer(text=BOT_NAME + " v" + BOT_VERSION + " • Owner Only")

    try:
        await ctx.author.send(embed=embed)
        ack = success_embed("Command reference udah dikirim ke DM kamu.")
    except discord.Forbidden:
        ack = error_embed("Gagal DM kamu — buka dulu DM dari server/bot ini, terus coba lagi.")
    await ctx.send(embed=ack, delete_after=8)

# ══════════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════

@bot.tree.command(name="rank", description="Lihat rank card XP kamu atau member lain.")
@app_commands.describe(member="Member yang ingin dilihat ranknya")
async def slash_rank(i: discord.Interaction, member: Optional[discord.Member] = None):
    await i.response.defer()
    target      = member or i.user
    gc          = guild_cfg(cfg, i.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"])
    all_m       = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp",0), reverse=True)
    rank        = next((idx+1 for idx,(uid,_) in enumerate(all_m) if uid == str(target.id)), 1)
    is_prem     = user_has_premium(i.guild, target)
    avatar_url  = str(target.display_avatar.with_format("png").with_size(256))

    import aiohttp
    file = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                avatar_bytes = await resp.read()
        buf = await asyncio.to_thread(
            rank_card.render_rank_card,
            avatar_bytes, target.name, lvl, rank, cx, nx,
            data["xp"], is_prem, data.get("messages", 0)
        )
        file = discord.File(buf, filename="rank.png")
    except Exception:
        logging.exception(f"[{BOT_NAME}] Gagal render rank card")

    if file:
        kwargs = {"file": file}
        try:
            content, view = _support_boost_promo(i.user.id)
            if content: kwargs["content"] = content
            if view:    kwargs["view"] = view
        except Exception:
            logging.exception(f"[{BOT_NAME}] Gagal build boost promo (rank card tetap dikirim)")
        return await i.followup.send(**kwargs)

    pct   = int((cx / max(nx,1)) * 100)
    bar   = "▰"*int(pct/100*16) + "▱"*(16-int(pct/100*16))
    embed = discord.Embed(description=f"**@{target.name}**\n\n**Level: {lvl}** | **XP: {cx:,}/{nx:,}** | **Rank: #{rank}**\n\n`{bar}` {pct}%\n\n*Total XP: {data['xp']:,}*", color=COLOR_PRIMARY)
    embed.set_author(name="Rank Card", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)
    await i.followup.send(embed=embed)

@bot.tree.command(name="leaderboard", description="Lihat top 10 XP leaderboard server ini.")
async def slash_leaderboard(i: discord.Interaction):
    gc    = guild_cfg(cfg, i.guild.id)
    all_d = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp",0), reverse=True)[:10]
    if not all_d:
        return await i.response.send_message(embed=info_embed("Leaderboard", "Belum ada data XP."), ephemeral=True)

    await i.response.defer()
    try:
        entries = await _build_leaderboard_entries(i.guild, all_d)
        buf  = await asyncio.to_thread(rank_card.render_leaderboard_card, i.guild.name, entries)
        file = discord.File(buf, filename="leaderboard.png")
        return await i.followup.send(file=file)
    except Exception as e:
        logging.error(f"[{BOT_NAME}] Gagal render leaderboard card: {e}")

    lines = []
    for idx,(uid,data) in enumerate(all_d):
        m     = i.guild.get_member(int(uid))
        name  = m.name if m else f"User ({uid[:6]})"
        medal = ["#1","#2","#3"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"**{medal} {name}** — Level **{data.get('level',0)}** · {data.get('xp',0):,} XP")
    embed = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"{BOT_NAME} · {i.guild.name}")
    await i.followup.send(embed=embed)

@bot.tree.command(name="profile", description="Lihat profile card dan badge kamu atau member lain.")
@app_commands.describe(member="Member yang ingin dilihat profilenya")
async def slash_profile(i: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or i.user
    embed  = build_profile_embed(target)
    embed.set_author(name="Profile & Badge Panel", icon_url=target.display_avatar.url)
    embed.set_footer(
        text=BOT_NAME + "  |  Requested By " + i.user.display_name,
        icon_url=i.user.display_avatar.url
    )
    await i.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Lihat info lengkap tentang member.")
@app_commands.describe(member="Member yang ingin dilihat infonya")
async def slash_userinfo(i: discord.Interaction, member: Optional[discord.Member] = None):
    await do_userinfo(i.guild, member or i.user, i.response.send_message)

@bot.tree.command(name="avatar", description="Lihat avatar member.")
@app_commands.describe(member="Member yang ingin dilihat avatarnya")
async def slash_avatar(i: discord.Interaction, member: Optional[discord.Member] = None):
    await do_avatar(member or i.user, i.response.send_message)

@bot.tree.command(name="serverinfo", description="Lihat info server.")
async def slash_serverinfo(i: discord.Interaction):
    g = i.guild
    embed = discord.Embed(title=g.name, description=g.description or "", color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner",      value=f"<@{g.owner_id}>",                    inline=True)
    embed.add_field(name="Members",    value=f"{g.member_count:,}",                  inline=True)
    embed.add_field(name="Created",    value=g.created_at.strftime("%d %b %Y"),       inline=True)
    embed.add_field(name="Channels",   value=str(len(g.text_channels)),               inline=True)
    embed.add_field(name="Roles",      value=str(len(g.roles)),                       inline=True)
    embed.add_field(name="Boost Tier", value=str(g.premium_tier),                     inline=True)
    embed.set_footer(text=f"{BOT_NAME} • ID: {g.id}")
    await i.response.send_message(embed=embed)

@bot.tree.command(name="boostconfig", description="Atur notifikasi server boost.")
@app_commands.describe(
    channel="Channel buat kirim notifikasi boost",
    title="Judul custom (opsional, default: 'New Server Boost!')",
    emoji="Emoji custom di depan judul (opsional, default: 🎉)",
    description="Deskripsi custom (opsional). Placeholder: {mention} {user} {server} {count} {tier}"
)
async def slash_boostconfig(
    i: discord.Interaction,
    channel: discord.TextChannel,
    title: Optional[str] = None,
    emoji: Optional[str] = None,
    description: Optional[str] = None
):
    if not (i.user.id == bot.owner_id or i.user.guild_permissions.manage_guild):
        return await i.response.send_message(embed=error_embed(t(cfg, i.guild.id, "no_perm")), ephemeral=True)

    gc = guild_cfg(cfg, i.guild.id)
    bc = gc.setdefault("boost", {})
    bc["channel"] = channel.id
    if title       is not None: bc["title"]       = title
    if emoji       is not None: bc["emoji"]       = emoji
    if description is not None: bc["description"] = description
    save_config(cfg)

    def fill(template: str) -> str:
        return (template
                .replace("{mention}", i.user.mention)
                .replace("{user}",    i.user.display_name)
                .replace("{server}",  i.guild.name)
                .replace("{count}",   str(i.guild.premium_subscription_count or 0))
                .replace("{tier}",    str(i.guild.premium_tier)))

    preview = discord.Embed(
        title=f"{bc.get('emoji') or e(ICON_BOOST, '🎉')} {fill(bc.get('title', 'New Server Boost!'))}".strip(),
        description=fill(bc.get("description", "{mention} just boosted **{server}**! Thanks for the support 💜")),
        color=0xF47FFF,
        timestamp=discord.utils.utcnow()
    )
    preview.set_thumbnail(url=i.user.display_avatar.url)
    preview.set_footer(text=f"{i.guild.name} • Preview — begini nanti tampilannya")

    await i.response.send_message(
        embed=success_embed(f"Notifikasi boost sekarang dikirim ke {channel.mention} setiap ada member baru boost."),
        ephemeral=True
    )
    await i.followup.send(embed=preview, ephemeral=True)

@bot.tree.command(name="ping", description="Cek latency bot.")
async def slash_ping(i: discord.Interaction):
    lat = round(bot.latency * 1000)
    await i.response.send_message(embed=base_embed("Pong!", f"Latency: **{lat}ms**", COLOR_SUCCESS if lat < 100 else COLOR_WARNING))

@bot.tree.command(name="help", description="Lihat semua command VALLENT EXS.")
async def slash_help(i: discord.Interaction):
    is_owner_user = (i.user.id == bot.owner_id)
    has_np        = user_has_no_prefix(i.guild, i.user)
    embed = discord.Embed(
        title=f"{BOT_NAME} — Command Reference",
        description=f"*{BOT_TAGLINE}*\n\nPrefix: **`!vx`** · **`!v`**\n" + ("✨ **No-prefix aktif**\n" if has_np else "") + "\u200b",
        color=COLOR_PRIMARY, timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderation", value="`kick` · `ban` · `unban` · `timeout` · `untimeout`\n`warn` · `warnings` · `unwarn` · `clearwarnings`\n`purge` · `lock` · `unlock` · `slowmode`", inline=False)
    embed.add_field(name="Role & Voice", value="`addrole` · `removerole` · `move`", inline=False)
    embed.add_field(name="Info", value="`userinfo` · `serverinfo` · `avatar` · `ping` · `addemoji` · `profile`", inline=False)
    embed.add_field(name="Ticket", value="`ticket setup` · `ticket panel` · `ticket edit` · `ticket list` · `ticket delete` · `ticket close`", inline=False)
    embed.add_field(name="Level & XP", value="`rank` · `leaderboard` (alias `lb`) · `level` · `xp`", inline=False)
    embed.add_field(name="Giveaway", value="`giveaway start/end/reroll/list`", inline=False)
    embed.add_field(name="Antispam", value="`antispam setchannel` · `antispam status`", inline=False)
    embed.add_field(name=f"{e(ICON_ANTINUKE, '🛡️')} Anti-Nuke".strip(), value="`antinuke enable/disable/logchannel/punishment/whitelist/status`", inline=False)
    embed.add_field(name=f"{e(ICON_BOOST, '🎉')} Server Boost".strip(), value="`/boostconfig` — atur channel & tampilan notifikasi boost", inline=False)
    if is_owner_user:
        embed.add_field(name="Owner Only", value=(
            "`maintenance on/off/status`\n"
            "`noprefix grant/revoke/list`\n"
            "`botrole set/remove/list`\n"
            "`grantpremium @user <durasi>/revoke`\n"
            "`premiumlock add/remove/list`\n"
            "`blacklist add/remove/list`\n"
            "`vxleave <guild_id>`"
        ), inline=False)
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} • {BOT_TAGLINE}")
    await i.response.send_message(embed=embed, ephemeral=True)



@bot.event
async def on_member_join(member: discord.Member):
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if member.guild.id != support_server_id or member.bot:
        return
    uid = member.id
    # Grant badge USER saat join support server
    support_members = cfg.setdefault("support_server_members", [])
    if uid not in support_members:
        support_members.append(uid)
        save_config(cfg)
    grant_xp_boost(uid, minutes=60, multiplier=1.10)
    badges = get_user_badges(uid)
    role   = get_bot_role(uid)
    embed  = discord.Embed(
        title="Selamat datang di " + member.guild.name + "!",
        description=(
            "Halo " + member.mention + "!\n\n"
            "Kamu baru saja mendapatkan badge **USER**!\n"
            "Bonus: **+10% XP Boost** aktif selama **60 menit** di semua server yang pakai " + BOT_NAME + "!\n\n"
            "Ketik `profile` untuk lihat badge kamu.\n\nKetik `help` untuk lihat semua command."
        ),
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    badge_lines = []
    for b in badges:
        info      = BOT_ROLE_BADGES.get(b, BOT_ROLE_BADGES["user"])
        emoji_str = info.get("emoji", "")
        prefix    = (emoji_str + " ") if emoji_str else "\u2022 "
        badge_lines.append(prefix + "**" + info["label"] + "**")
    embed.add_field(name=f"{e(ICON_BADGES, '✨')} ALL BADGES".strip(), value="\n".join(badge_lines), inline=True)
    embed.add_field(name="Bot Role", value=role.capitalize(), inline=True)
    embed.set_footer(text=BOT_NAME + " \u2022 " + BOT_TAGLINE)
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        pass
    gc = guild_cfg(cfg, member.guild.id)
    main_ch_id = gc.get("main_channel") or gc.get("announce_channel")
    if main_ch_id:
        ch = member.guild.get_channel(main_ch_id)
        if ch:
            w = discord.Embed(description=member.mention + " bergabung!", color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
            w.set_author(name=str(member), icon_url=member.display_avatar.url)
            w.set_footer(text=BOT_NAME)
            try:
                await ch.send(embed=w)
            except Exception:
                pass

@bot.tree.error
async def on_app_command_error(i: discord.Interaction, error: app_commands.AppCommandError):
    msg = str(error)
    if isinstance(error, app_commands.MissingPermissions):
        msg = t(cfg, i.guild.id if i.guild else 0, "no_perm")
    try:
        await i.response.send_message(embed=error_embed(msg), ephemeral=True)
    except discord.InteractionResponded:
        try:
            await i.followup.send(embed=error_embed(msg), ephemeral=True)
        except Exception:
            pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=error_embed("Kamu tidak punya akses ke command ini."), delete_after=5)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=error_embed(f"Argumen kurang: `{error.param.name}`"), delete_after=5)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(embed=error_embed(f"Argumen tidak valid: {error}"), delete_after=5)
        return
    logging.error(f"[{BOT_NAME}] Command error: {error}")

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    async def main():
        async with bot:
            await bot.start(token)

    asyncio.run(main())
