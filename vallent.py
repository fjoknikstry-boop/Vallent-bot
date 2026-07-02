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
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import re
import shlex
import asyncio
import datetime
import logging
import pytz
from collections import defaultdict
from typing import Optional

logging.basicConfig(level=logging.INFO)

from emoji_config import (
    BADGE_FOUNDER, BADGE_DEVELOPER, BADGE_MANAGEMENT, BADGE_STAFF,
    BADGE_PREMIUM, BADGE_NOPREFIX, BADGE_USER,
    ICON_MODERATION, ICON_ROLE, ICON_INFO, ICON_TICKET, ICON_LEVEL,
    ICON_GIVEAWAY, ICON_ANTISPAM, ICON_LANGUAGE, ICON_OWNER,
    ICON_SUCCESS, ICON_ERROR, ICON_PROFILE, ICON_BADGES, ICON_COMMANDS,
    ICON_TICKET_OPEN, ICON_TICKET_CLOSE, ICON_GIVEAWAY_REACT, ICON_WINNER,
    e
)

# ══════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════

BOT_NAME      = "VALLENT EXS"
BOT_TAGLINE   = "No mercy. No limits. Full control."
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
            "bot_roles":         {},
            "votes":             {},
            "maintenance": {"enabled": False, "reason": ""},
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
    data.setdefault("bot_roles",        {})
    data.setdefault("votes",            {})
    data.setdefault("support_server_members", [])  # user IDs yang sudah join support server
    data.setdefault("commands_run",           {})  # uid → jumlah command dijalankan
    data.setdefault("maintenance", {"enabled": False, "reason": ""})
    for gid, gc in data.get("guilds", {}).items():
        _init_guild(gc)
    save_config(data)
    return data

def _init_guild(gc: dict):
    gc.setdefault("language",          "en")
    gc.setdefault("main_channel",      None)
    gc.setdefault("announce_channel",  None)
    gc.setdefault("level_channel",     None)
    gc.setdefault("spam_trap_channel", None)
    gc.setdefault("mod_log_channel",   None)
    gc.setdefault("leveling_enabled",  True)
    gc.setdefault("xp_per_message",    [15, 25])
    gc.setdefault("xp_cooldown",       60)
    gc.setdefault("members_xp",        {})
    gc.setdefault("level_roles",       {})
    gc.setdefault("warnings",          {})
    gc.setdefault("active_tickets",    {})
    gc.setdefault("ticket", {
        "category":     None,
        "log_category": None,
        "support_role": None,
        "max_tickets":  1,
        "panels":       [],
        "counter":      0,
    })
    gc["ticket"].setdefault("category",     None)
    gc["ticket"].setdefault("log_category", None)
    gc["ticket"].setdefault("support_role", None)
    gc["ticket"].setdefault("max_tickets",  1)
    gc["ticket"].setdefault("panels",       [])
    gc["ticket"].setdefault("counter",      0)

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

def base_embed(title: str, description: str = "", color: int = COLOR_PRIMARY) -> discord.Embed:
    return _footer(discord.Embed(title=title, description=description, color=color))

def success_embed(desc: str) -> discord.Embed:
    return base_embed("Success", desc, COLOR_SUCCESS)

def error_embed(desc: str) -> discord.Embed:
    return base_embed("Error", desc, COLOR_ERROR)

def info_embed(title: str, desc: str) -> discord.Embed:
    return base_embed(title, desc, COLOR_INFO)

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
        if interaction.type not in (
            discord.InteractionType.application_command,
            discord.InteractionType.autocomplete,
        ):
            return True
        if data.get("type", 1) != 1:
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
        cmd_name      = " ".join(parts)
        is_owner_user = interaction.user.id == bot.owner_id

        # Maintenance mode — hanya owner yang boleh lewat
        if is_maintenance() and not is_owner_user:
            try:
                await interaction.response.send_message(embed=maintenance_embed(), ephemeral=True)
            except discord.InteractionResponded:
                pass
            return False

        if cmd_name in cfg.get("premium_commands", []) and not is_owner_user and not user_has_premium(interaction.guild, interaction.user):
            try:
                await interaction.response.send_message(
                    embed=base_embed(
                        "Premium Required",
                        f"Command `/{cmd_name}` hanya untuk **Premium** users.\n"
                        "Hubungi owner atau kunjungi server support untuk berlangganan.",
                        color=COLOR_WARNING
                    ), ephemeral=True)
            except discord.InteractionResponded:
                pass
            return False

        track_command_use(interaction.user.id)
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

# ══════════════════════════════════════════════════════════════════
# BOT ROLES SYSTEM
# ══════════════════════════════════════════════════════════════════

BOT_ROLE_HIERARCHY = ["staff", "management", "developer", "founder"]

BOT_ROLE_BADGES = {
    # Emoji diambil dari emoji_config.py — edit file itu untuk isi ID emoji
    "founder":    {"label": "• FOUNDER",    "color": 0x8B0000, "emoji": BADGE_FOUNDER},
    "developer":  {"label": "• DEVELOPER",  "color": 0xDC143C, "emoji": BADGE_DEVELOPER},
    "management": {"label": "• Management", "color": 0xB22222, "emoji": BADGE_MANAGEMENT},
    "staff":      {"label": "• Staff",      "color": 0xCD5C5C, "emoji": BADGE_STAFF},
    "premium":    {"label": "• Premium",    "color": 0xF59E0B, "emoji": BADGE_PREMIUM},
    "noprefix":   {"label": "• NO PREFIX",  "color": 0x22C55E, "emoji": BADGE_NOPREFIX},
    "user":       {"label": "• User",       "color": 0x6B7280, "emoji": BADGE_USER},
}

def get_bot_role(uid: int) -> str:
    if uid == bot.owner_id:
        return "founder"
    return cfg.get("bot_roles", {}).get(str(uid), "user")

def get_user_badges(uid: int) -> list:
    """
    Kumpulkan semua badge user.
    Hierarki: founder > developer > management > staff > noprefix > premium > user
    Badge USER hanya didapat kalau user join server support bot.
    Kalau tidak punya badge apapun → list kosong.
    """
    badges = []
    role   = get_bot_role(uid)
    if role != "user":
        badges.append(role)
    if uid in cfg.get("no_prefix_users", []):
        badges.append("noprefix")
    if uid in cfg.get("premium_users", []):
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
    has_np     = (uid in cfg.get("no_prefix_users", []) or uid == bot.owner_id or has_prem)
    cmds_run   = cfg.get("commands_run", {}).get(str(uid), 0)
    top        = role if role != "user" else (badges[0] if badges else "user")
    color      = BOT_ROLE_BADGES.get(top, BOT_ROLE_BADGES["user"])["color"]

    embed = discord.Embed(title=str(user.display_name) + "'s Profile", color=color)
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

    embed.add_field(name="\u2728 ALL BADGES", value=badges_value, inline=False)

    # ── Total Badges & Commands Runned — dua field sejajar ────────────
    embed.add_field(name="Total Badges", value="**" + str(len(badges)) + "**", inline=True)
    embed.add_field(name="Commands Runned", value="**" + str(cmds_run) + "**", inline=True)

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
        embed.add_field(name="Premium", value=prem_value, inline=True)

    embed.set_footer(
        text=BOT_NAME + " \u2022 ID: " + str(uid),
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

OWNER_ONLY_CMDS = {"maintenance", "noprefix", "botrole", "grantpremium", "premiumlock", "blacklist", "vxleave", "syncsupport"}

def is_owner():
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.id == bot.owner_id
    return commands.check(predicate)

def is_staff_or_above(uid: int) -> bool:
    role = get_bot_role(uid)
    return role in BOT_ROLE_HIERARCHY

# ══════════════════════════════════════════════════════════════════
# MAINTENANCE MODE
# ══════════════════════════════════════════════════════════════════

def is_maintenance() -> bool:
    return bool(cfg.get("maintenance", {}).get("enabled", False))

def maintenance_reason() -> str:
    return cfg.get("maintenance", {}).get("reason") or "Bot sedang dalam perbaikan. Coba lagi nanti."

def maintenance_embed() -> discord.Embed:
    return base_embed(
        "Under Maintenance",
        f"{BOT_NAME} sedang maintenance, semua command dikunci sementara.\n**Alasan:** {maintenance_reason()}",
        color=COLOR_WARNING
    )

# ══════════════════════════════════════════════════════════════════
# COMMAND USAGE TRACKER (Commands Runned)
# ══════════════════════════════════════════════════════════════════

def track_command_use(uid: int) -> None:
    """Catat setiap command yang berhasil dijalankan oleh seorang user."""
    cmds_run  = cfg.setdefault("commands_run", {})
    key       = str(uid)
    cmds_run[key] = cmds_run.get(key, 0) + 1
    save_config(cfg)

@bot.check
async def global_prefix_premium_check(ctx: commands.Context) -> bool:
    cmd = ctx.command.qualified_name if ctx.command else None
    if not cmd:
        return True
    is_owner_user = (ctx.author.id == bot.owner_id)

    # Maintenance mode — hanya owner yang boleh lewat
    if is_maintenance() and cmd not in OWNER_ONLY_CMDS and not is_owner_user:
        await ctx.send(embed=maintenance_embed())
        return False

    if cmd in OWNER_ONLY_CMDS:
        return True
    if cmd not in cfg.get("premium_commands", []):
        return True
    if is_owner_user:
        return True
    if user_has_premium(ctx.guild, ctx.author):
        return True
    await ctx.send(embed=base_embed(
        "Premium Required",
        f"Command `{cmd}` hanya untuk **Premium** users.\n"
        "Hubungi owner untuk berlangganan.",
        color=COLOR_WARNING
    ))
    return False

@bot.event
async def on_command_completion(ctx: commands.Context):
    """Dipanggil setiap command prefix berhasil dijalankan tanpa error."""
    track_command_use(ctx.author.id)

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

class TicketCloseButton(discord.ui.Button):
    """Tombol close ticket persisten — dipasang ulang tiap start via bot.add_view di on_ready."""
    def __init__(self):
        super().__init__(
            label="Close Ticket", style=discord.ButtonStyle.danger,
            emoji=ICON_TICKET_CLOSE if ICON_TICKET_CLOSE else "🔒",
            custom_id="vx_ticket_close"
        )

    async def callback(self, i: discord.Interaction):
        gc  = guild_cfg(cfg, i.guild.id)
        rec = gc["active_tickets"].get(str(i.channel.id))
        if not rec:
            return await i.response.send_message(embed=error_embed("Ticket ini sudah tidak aktif."), ephemeral=True)
        if not (i.user.guild_permissions.manage_channels or rec.get("owner") == i.user.id):
            return await i.response.send_message(embed=error_embed("Kamu tidak bisa menutup ticket ini."), ephemeral=True)
        await i.response.send_message(embed=info_embed("Ticket", "Menutup ticket..."), ephemeral=True)
        await close_ticket(i.guild, i.channel, i.user, "Closed via button.")

class TicketPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())

class TicketOpenButton(discord.ui.Button):
    """Tombol buka ticket di panel — persisten, tetap jalan walau bot restart."""
    def __init__(self, label: str = "Open Ticket"):
        super().__init__(
            label=label, style=discord.ButtonStyle.danger,
            emoji=ICON_TICKET_OPEN if ICON_TICKET_OPEN else "🎫",
            custom_id="vx_ticket_open"
        )

    async def callback(self, i: discord.Interaction):
        await handle_open_ticket(i)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketOpenButton())

async def close_ticket(guild: discord.Guild, channel: discord.TextChannel, closer: discord.abc.User, reason: str):
    """
    Menutup satu ticket: umumkan di channel, kirim ringkasan ke log channel
    milik ticket tsb (log channel TETAP ADA sebagai arsip), lalu hapus channel ticket-nya.
    Dipakai bersama oleh tombol Close dan command `ticket close`.
    """
    gc  = guild_cfg(cfg, guild.id)
    rec = gc["active_tickets"].pop(str(channel.id), None)
    save_config(cfg)

    try:
        await channel.send(embed=base_embed(
            "Ticket Closing",
            f"Ditutup oleh {closer.mention}.\n{reason}\n\nChannel akan dihapus dalam 5 detik.",
            color=COLOR_ERROR
        ))
    except Exception:
        pass

    if rec and rec.get("log_channel"):
        log_ch = guild.get_channel(rec["log_channel"])
        if log_ch:
            summary = base_embed("Ticket Closed", None, color=COLOR_ERROR)
            summary.add_field(name="Ticket",    value=f"#{rec.get('number', '?'):04d}" if isinstance(rec.get("number"), int) else "-", inline=True)
            summary.add_field(name="Owner",     value=f"<@{rec.get('owner')}>", inline=True)
            summary.add_field(name="Closed By", value=closer.mention, inline=True)
            summary.add_field(name="Reason",    value=reason or "-", inline=False)
            try:
                await log_ch.send(embed=summary)
                await log_ch.edit(name=("closed-" + log_ch.name)[:100], reason="Ticket closed — archived")
            except Exception:
                pass

    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"Ticket closed by {closer}")
    except Exception:
        pass

async def handle_open_ticket(interaction: discord.Interaction):
    gc     = guild_cfg(cfg, interaction.guild.id)
    cat_id = gc["ticket"].get("category")
    log_cat_id = gc["ticket"].get("log_category")
    max_t  = gc["ticket"].get("max_tickets", 1)
    uid    = interaction.user.id

    if not cat_id:
        return await interaction.response.send_message(
            embed=error_embed("Ticket system belum dikonfigurasi. Jalankan `ticket setup` dulu."), ephemeral=True)

    user_tickets = [t for t in gc["active_tickets"].values() if t.get("owner") == uid]
    if len(user_tickets) >= max_t:
        return await interaction.response.send_message(
            embed=error_embed(f"Kamu sudah memiliki {len(user_tickets)}/{max_t} ticket terbuka."), ephemeral=True)

    category = interaction.guild.get_channel(cat_id)
    if not category:
        return await interaction.response.send_message(
            embed=error_embed("Ticket category tidak ditemukan."), ephemeral=True)

    gc["ticket"]["counter"] = gc["ticket"].get("counter", 0) + 1
    number = gc["ticket"]["counter"]

    role_id = gc["ticket"].get("support_role")
    role    = interaction.guild.get_role(role_id) if role_id else None

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:               discord.PermissionOverwrite(view_channel=True, send_messages=True),
        interaction.guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    if role:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    ch = await category.create_text_channel(
        name=f"ticket-{number:04d}-{interaction.user.name}",
        overwrites=overwrites,
        topic=f"Ticket #{number} for {interaction.user} ({interaction.user.id})"
    )

    # ── Log channel khusus untuk ticket ini ─────────────────────────────
    log_ch = None
    log_category = interaction.guild.get_channel(log_cat_id) if log_cat_id else None
    if log_category:
        log_overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if role:
            log_overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        try:
            log_ch = await log_category.create_text_channel(
                name=f"log-{number:04d}-{interaction.user.name}",
                overwrites=log_overwrites,
                topic=f"Log arsip untuk ticket #{number} ({interaction.user.id})"
            )
        except Exception:
            log_ch = None

    gc["active_tickets"][str(ch.id)] = {
        "owner":       uid,
        "log_channel": log_ch.id if log_ch else None,
        "number":      number,
    }
    save_config(cfg)

    welcome_embed = base_embed(
        f"Ticket #{number:04d} — {interaction.user.display_name}",
        f"Halo {interaction.user.mention}, tim support akan segera membantu.\nJelaskan keperluanmu di sini.",
        color=COLOR_PRIMARY
    )
    await ch.send(embed=welcome_embed, view=TicketPersistentView())

    if log_ch:
        open_emb = base_embed("Ticket Opened", None, color=COLOR_PRIMARY)
        open_emb.add_field(name="Ticket",  value=f"#{number:04d}", inline=True)
        open_emb.add_field(name="User",    value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        open_emb.add_field(name="Channel", value=ch.mention, inline=True)
        try:
            await log_ch.send(embed=open_emb)
        except Exception:
            pass

    await interaction.response.send_message(
        embed=success_embed(t(cfg, interaction.guild.id, "ticket_open", channel=ch.mention)),
        ephemeral=True
    )

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
        title="Giveaway Winners!",
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

@tasks.loop(minutes=30)
async def cleanup_spam_cache():
    now     = discord.utils.utcnow().timestamp()
    to_del  = [uid for uid, t in spam_cleanup_times.items() if now - t > 120]
    for uid in to_del:
        spam_tracker.pop(uid, None)
        spam_cleanup_times.pop(uid, None)

@tasks.loop(minutes=5)
async def rotate_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="every move."),
        discord.Activity(type=discord.ActivityType.listening, name="!vx help"),
        discord.Activity(type=discord.ActivityType.playing, name="VALLENT EXS v1.0"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"),
    ]
    import random as _r
    await bot.change_presence(activity=_r.choice(statuses), status=discord.Status.dnd)

# ══════════════════════════════════════════════════════════════════
# BOT EVENTS
# ══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"[{BOT_NAME}] Ready as {bot.user} (ID: {bot.user.id})")
    bot.add_view(TicketPanelView())
    bot.add_view(TicketPersistentView())
    for cmd in bot.tree.get_commands():
        ORIGINAL_CMD_DESCRIPTIONS[cmd.name] = cmd.description.removeprefix("[💎] ")
        if hasattr(cmd, "commands"):
            for sub in cmd.commands:
                ORIGINAL_CMD_DESCRIPTIONS[f"{cmd.name} {sub.name}"] = sub.description.removeprefix("[💎] ")
    try:
        synced = await bot.tree.sync()
        print(f"[{BOT_NAME}] Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"[{BOT_NAME}] Sync error: {e}")
    cleanup_spam_cache.start()
    rotate_status.start()
    if not premium_expiry_task.is_running():
        premium_expiry_task.start()
    print(f"[{BOT_NAME}] Online — {len(bot.guilds)} guild(s).")

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
        log_id = gc_trap.get("mod_log_channel")
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

    # ── Ticket message mirroring ke log channel masing-masing ──────────────
    ticket_rec = gc_trap.get("active_tickets", {}).get(str(message.channel.id))
    if ticket_rec and ticket_rec.get("log_channel"):
        log_ch = message.guild.get_channel(ticket_rec["log_channel"])
        if log_ch and (message.content or message.attachments):
            mirror = discord.Embed(
                description=(message.content or "*[lampiran saja]*")[:4000],
                color=COLOR_PRIMARY,
                timestamp=message.created_at
            )
            mirror.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
            if message.attachments:
                mirror.add_field(
                    name="Attachments",
                    value="\n".join(a.url for a in message.attachments)[:1024],
                    inline=False
                )
            try:
                await log_ch.send(embed=mirror)
            except Exception:
                pass

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
            gain           = random.randint(xp_min, xp_max)
            old_level      = data["level"]
            data["xp"]    += gain
            data["level"]  = level_from_xp(data["xp"])
            data["last_msg_ts"] = now
            data["messages"]    = data.get("messages", 0) + 1
            save_config(cfg)
            if data["level"] > old_level:
                lvl_ch_id = gc.get("level_channel")
                lvl_ch    = message.guild.get_channel(lvl_ch_id) if lvl_ch_id else message.channel
                if lvl_ch:
                    lvl_emb = discord.Embed(
                        description=f"{message.author.mention} leveled up to **Level {data['level']}**!",
                        color=COLOR_ERROR
                    )
                    lvl_emb.set_author(name="Level Up!", icon_url=message.author.display_avatar.url)
                    lvl_emb.set_footer(text=BOT_NAME)
                    try:
                        await lvl_ch.send(embed=lvl_emb, delete_after=30)
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
        uid_int   = message.author.id
        gid_int   = message.guild.id
        np_users  = cfg.get("no_prefix_users",  [])
        np_guilds = cfg.get("no_prefix_guilds", [])
        has_np    = (
            uid_int == bot.owner_id
            or uid_int in np_users
            or gid_int in np_guilds
            or user_has_premium(message.guild, message.author)
        )
        if has_np:
            text  = message.content.strip()
            first = text.split()[0].lower() if text.split() else ""
            known = {c.name for c in bot.commands}
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
    if str(payload.emoji) != "🎉":
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
        text=BOT_NAME + " \u2022 ID: " + str(target.id) + "  |  Requested By " + ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

# ── RANK & LEADERBOARD ────────────────────────────────────────────

@bot.command(name="rank")
async def pfx_rank(ctx, member: discord.Member = None):
    import aiohttp, io
    target      = member or ctx.author
    gc          = guild_cfg(cfg, ctx.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"])
    all_m       = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    rank        = next((i+1 for i, (uid, _) in enumerate(all_m) if uid == str(target.id)), 1)
    pct         = int((cx / max(nx, 1)) * 100)
    avatar_url  = str(target.display_avatar.with_format("png").with_size(256))
    is_prem     = user_has_premium(ctx.guild, target)
    bar_color   = "F59E0B" if is_prem else "8B0000"
    api_url     = (
        "https://some-random-api.com/canvas/misc/rank-card"
        f"?username={target.display_name}"
        f"&avatar={avatar_url}"
        f"&currentxp={cx}&neededxp={nx}"
        f"&level={lvl}&rank={rank}"
        f"&barcolor={bar_color}"
    )
    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200 and "image" in resp.content_type:
                        img_bytes = await resp.read()
                        file  = discord.File(io.BytesIO(img_bytes), filename="rank.png")
                        embed = discord.Embed(color=int(bar_color, 16), timestamp=discord.utils.utcnow())
                        embed.set_author(name=f"Rank Card — {target.display_name}", icon_url=target.display_avatar.url)
                        embed.set_image(url="attachment://rank.png")
                        embed.set_footer(text=f"Total XP: {data['xp']:,} · Messages: {data.get('messages',0):,} · {ctx.guild.name}")
                        return await ctx.send(file=file, embed=embed)
        except Exception:
            pass
    # Fallback embed
    bar   = "▰" * int(pct/100*16) + "▱" * (16-int(pct/100*16))
    embed = discord.Embed(
        description=(
            f"**@{target.display_name}**\n\n"
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

@bot.command(name="leaderboard")
async def pfx_leaderboard(ctx):
    gc    = guild_cfg(cfg, ctx.guild.id)
    all_d = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
    if not all_d:
        return await ctx.send(embed=info_embed("Leaderboard", "Belum ada data XP."))
    lines = []
    for idx, (uid, data) in enumerate(all_d):
        m     = ctx.guild.get_member(int(uid))
        name  = m.display_name if m else f"User ({uid[:6]})"
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
    sub = sub.lower()
    gc  = guild_cfg(cfg, ctx.guild.id)

    if sub == "setup":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        args = rest.split()
        if len(args) < 2:
            return await ctx.send(embed=error_embed(
                "Usage: `ticket setup <category_id> <log_category_id> [role_id] [max]`\n"
                "*(log_category_id harus berupa Category, tempat log channel tiap ticket akan otomatis dibuat)*"
            ))
        try:
            cat_id     = int(args[0])
            log_cat_id = int(args[1])
            role_id    = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
            max_t      = int(args[3]) if len(args) > 3 else 1
        except ValueError:
            return await ctx.send(embed=error_embed("ID harus angka."))
        cat     = ctx.guild.get_channel(cat_id)
        log_cat = ctx.guild.get_channel(log_cat_id)
        if not cat or not isinstance(cat, discord.CategoryChannel):
            return await ctx.send(embed=error_embed("Ticket category tidak ditemukan / bukan Category."))
        if not log_cat or not isinstance(log_cat, discord.CategoryChannel):
            return await ctx.send(embed=error_embed("Log category tidak ditemukan / bukan Category."))
        gc["ticket"].update({
            "category":     cat_id,
            "log_category": log_cat_id,
            "support_role": role_id,
            "max_tickets":  max(1, min(5, max_t)),
        })
        save_config(cfg)
        embed = base_embed("Ticket System Configured", None)
        embed.add_field(name="Ticket Category", value=cat.name,     inline=True)
        embed.add_field(name="Log Category",    value=log_cat.name, inline=True)
        embed.add_field(name="Support Role",    value=f"<@&{role_id}>" if role_id else "None", inline=True)
        embed.add_field(name="Max Tickets",     value=str(gc["ticket"]["max_tickets"]), inline=True)
        embed.set_footer(text="Setiap ticket baru otomatis dapat log channel sendiri di dalam Log Category.")
        await ctx.send(embed=embed)

    elif sub == "panel":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed(t(cfg, ctx.guild.id, "no_perm")))
        if not gc["ticket"].get("category"):
            return await ctx.send(embed=error_embed("Jalankan `ticket setup` dulu."))
        try:
            parts = shlex.split(rest) if rest.strip() else []
        except ValueError:
            parts = rest.split()
        title_txt = parts[0] if len(parts) > 0 else "Support Tickets"
        desc_txt  = parts[1] if len(parts) > 1 else "Klik tombol di bawah untuk membuka support ticket."
        await ctx.send(embed=base_embed(title_txt, desc_txt), view=TicketPanelView())

    elif sub == "close":
        rec = gc["active_tickets"].get(str(ctx.channel.id))
        if not rec:
            return await ctx.send(embed=error_embed("Channel ini bukan ticket aktif."))
        if (ctx.author.id != bot.owner_id
                and not ctx.author.guild_permissions.manage_channels
                and rec.get("owner") != ctx.author.id):
            return await ctx.send(embed=error_embed("Kamu tidak bisa menutup ticket ini."))
        reason_txt = rest.strip() if rest.strip() else "Closed via command."
        await close_ticket(ctx.guild, ctx.channel, ctx.author, reason_txt)

    else:
        await ctx.send(embed=info_embed(
            "Ticket",
            '`ticket setup <cat_id> <log_category_id> [role_id] [max]`\n'
            '`ticket panel "Judul" "Deskripsi"` — deskripsi opsional\n'
            '`ticket close [reason]`'
        ))

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
        for reaction in msg.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot: entries.append(user.id)
                break
        if not entries: return await ctx.send(embed=error_embed("Tidak ada peserta."))
        count   = max(1, min(count, len(entries)))
        winners = random.sample(list(set(entries)), count)
        ws      = " ".join(f"<@{w}>" for w in winners)
        embed   = discord.Embed(title="Giveaway Rerolled!", description=f"Pemenang baru: {ws}", color=COLOR_SUCCESS, timestamp=discord.utils.utcnow())
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
        trap   = gc.get("spam_trap_channel")
        ch     = ctx.guild.get_channel(trap) if trap else None
        log_id = gc.get("mod_log_channel")
        log_ch = ctx.guild.get_channel(log_id) if log_id else None
        embed  = base_embed("Honeypot Status", "Aktif di " + ch.mention if ch else "Tidak aktif.", color=COLOR_ERROR if ch else COLOR_INFO)
        embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "Belum diatur", inline=True)
        await ctx.send(embed=embed)
    elif sub == "logchannel":
        if not args:
            gc["mod_log_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Mod log channel dinonaktifkan."))
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else (ctx.guild.get_channel(int(args.strip())) if args.strip().isdigit() else None)
        if not ch: return await ctx.send(embed=error_embed("Channel tidak ditemukan."))
        gc["mod_log_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Mod log channel diset ke {ch.mention}."))
    else:
        await ctx.send(embed=info_embed("Antispam Honeypot", "`antispam setchannel #channel`\n`antispam setchannel` (nonaktifkan)\n`antispam logchannel #channel`\n`antispam status`"))

# ── OWNER COMMANDS ────────────────────────────────────────────────

@bot.command(name="noprefix")
@is_owner()
async def pfx_noprefix(ctx, action: str = "", *, target: str = ""):
    action    = action.lower()
    np_users  = cfg.setdefault("no_prefix_users",  [])
    np_guilds = cfg.setdefault("no_prefix_guilds", [])
    if action == "list":
        u_lines = [f"<@{uid}> (`{uid}`)" for uid in np_users] or ["*(none)*"]
        g_lines = []
        for gid in np_guilds:
            g = bot.get_guild(gid)
            g_lines.append(f"**{g.name}** (`{gid}`)" if g else f"`{gid}`")
        g_lines = g_lines or ["*(none)*"]
        embed = base_embed("No-Prefix Access List", None)
        embed.add_field(name="Users",  value="\n".join(u_lines), inline=False)
        embed.add_field(name="Guilds", value="\n".join(g_lines), inline=False)
        return await ctx.send(embed=embed)
    if action not in ("grant","revoke"):
        return await ctx.send(embed=info_embed("No-Prefix",
            "`noprefix grant @user/guild_id`\n`noprefix revoke @user/guild_id`\n`noprefix list`"))
    if not target: return await ctx.send(embed=error_embed("Masukkan @user atau guild ID."))
    uid_match = re.match(r"<@!?(\d+)>|(\d{17,20})", target.strip())
    if not uid_match: return await ctx.send(embed=error_embed("Target tidak valid."))
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
    else:
        try: user = await bot.fetch_user(parsed_id)
        except Exception: return await ctx.send(embed=error_embed("User/Guild tidak ditemukan."))
        if action == "grant":
            if parsed_id not in np_users: np_users.append(parsed_id)
            save_config(cfg)
            try:
                dm = base_embed("No-Prefix Access Granted!", "Kamu bisa gunain command VALLENT EXS tanpa prefix!\nCukup ketik nama command langsung.", color=COLOR_SUCCESS)
                await user.send(embed=dm)
            except Exception: pass
            await ctx.send(embed=success_embed(f"No-prefix diaktifkan untuk {user.mention}."))
        else:
            if parsed_id in np_users: np_users.remove(parsed_id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"No-prefix dicabut dari {user.mention}."))

@bot.command(name="botrole")
@is_owner()
async def pfx_botrole(ctx, action: str = "", member: discord.Member = None, role: str = ""):
    action    = action.lower()
    bot_roles = cfg.setdefault("bot_roles", {})
    if action == "list":
        if not bot_roles: return await ctx.send(embed=info_embed("Bot Roles", "Belum ada assignment."))
        lines = []
        for uid_str, r in bot_roles.items():
            user = bot.get_user(int(uid_str))
            name = user.display_name if user else f"ID {uid_str}"
            lines.append(f"**{name}** → {r.capitalize()}")
        return await ctx.send(embed=info_embed("Bot Roles", "\n".join(lines)))
    if not member:
        return await ctx.send(embed=info_embed("Bot Role", "`botrole set @user <staff/management/developer>`\n`botrole remove @user`\n`botrole list`"))
    if action == "set":
        role = role.lower()
        if role not in ["staff","management","developer"]:
            return await ctx.send(embed=error_embed("Role valid: `staff`, `management`, `developer`"))
        bot_roles[str(member.id)] = role
        save_config(cfg)
        info = BOT_ROLE_BADGES[role]
        embed = discord.Embed(title="Bot Role Assigned", description=f"{member.mention} → **{info['label']}**", color=info["color"], timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            dm = discord.Embed(title="Bot Role Granted!", description=f"Kamu mendapat role **{info['label']}** di {BOT_NAME}!\nCek profil: `profile`", color=info["color"])
            await member.send(embed=dm)
        except Exception: pass
        await ctx.send(embed=embed)
    elif action == "remove":
        if str(member.id) not in bot_roles: return await ctx.send(embed=error_embed(f"{member.display_name} tidak punya bot role."))
        removed = bot_roles.pop(str(member.id))
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Bot role **{removed.capitalize()}** dihapus dari {member.mention}."))

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
            await member.send(embed=base_embed("Premium Ended", f"Premium {BOT_NAME} kamu telah berakhir.", color=COLOR_ERROR))
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
        dm = discord.Embed(title="Premium Activated!", description=f"Premium {BOT_NAME} aktif!\nExpires: {dur_display}\n\nSemua fitur premium terbuka.", color=COLOR_WARNING)
        await member.send(embed=dm)
    except Exception: pass
    await ctx.send(embed=embed)

def _apply_premium_marker(name: str, locked: bool) -> None:
    """Tandai/bersihkan prefix [💎] di description slash command yang di-lock premium."""
    cmd = bot.tree.get_command(name)
    if not cmd:
        return
    base = ORIGINAL_CMD_DESCRIPTIONS.get(name, cmd.description.removeprefix("[\U0001F48E] "))
    cmd.description = ("[\U0001F48E] " + base) if locked else base

@bot.command(name="premiumlock")
@is_owner()
async def pfx_premiumlock(ctx, action: str = "", *, command_name: str = ""):
    """Atur command apa saja yang cuma bisa dipakai user Premium."""
    action = action.lower()
    locked = cfg.setdefault("premium_commands", [])
    known_prefix = {c.name for c in bot.commands}
    known_slash  = {c.name for c in bot.tree.get_commands()}

    if action in ("add", "lock"):
        name = command_name.strip().lower()
        if not name:
            return await ctx.send(embed=error_embed("Sebutkan nama command. Contoh: `premiumlock add rank`"))
        if name not in known_prefix and name not in known_slash:
            return await ctx.send(embed=error_embed(f"Command `{name}` tidak ditemukan."))
        if name in OWNER_ONLY_CMDS:
            return await ctx.send(embed=error_embed("Command owner-only tidak bisa di-lock premium."))
        if name in locked:
            return await ctx.send(embed=error_embed(f"Command `{name}` sudah di-lock."))
        locked.append(name)
        save_config(cfg)
        _apply_premium_marker(name, True)
        try:
            await bot.tree.sync()
        except Exception:
            pass
        await ctx.send(embed=success_embed(f"Command `{name}` sekarang **Premium Only**."))

    elif action in ("remove", "unlock"):
        name = command_name.strip().lower()
        if name not in locked:
            return await ctx.send(embed=error_embed(f"Command `{name}` tidak sedang di-lock."))
        locked.remove(name)
        save_config(cfg)
        _apply_premium_marker(name, False)
        try:
            await bot.tree.sync()
        except Exception:
            pass
        await ctx.send(embed=success_embed(f"Command `{name}` sudah bisa dipakai semua user lagi."))

    elif action == "list":
        if not locked:
            return await ctx.send(embed=info_embed("Premium Locked Commands", "Belum ada command yang di-lock."))
        await ctx.send(embed=info_embed("Premium Locked Commands", "\n".join(f"`{c}`" for c in locked)))

    else:
        await ctx.send(embed=info_embed(
            "Premium Lock",
            "`premiumlock add <command>` — kunci command untuk premium only\n"
            "`premiumlock remove <command>` — buka kunci\n"
            "`premiumlock list` — lihat semua command yang di-lock"
        ))

@bot.command(name="maintenance")
@is_owner()
async def pfx_maintenance(ctx, action: str = "status", *, reason: str = ""):
    """Kunci seluruh command bot kecuali untuk owner."""
    action = action.lower()
    state  = cfg.setdefault("maintenance", {"enabled": False, "reason": ""})

    if action == "on":
        state["enabled"] = True
        state["reason"]  = reason or "Sedang ada perbaikan sistem."
        save_config(cfg)
        await ctx.send(embed=base_embed(
            "Maintenance Mode: ON",
            f"Semua command dikunci kecuali untuk owner.\n**Alasan:** {state['reason']}",
            color=COLOR_WARNING
        ))
    elif action == "off":
        state["enabled"] = False
        save_config(cfg)
        await ctx.send(embed=success_embed("Maintenance mode dimatikan. Semua command sudah normal kembali."))
    elif action == "status":
        status_txt = "🟢 OFF" if not state["enabled"] else "🔴 ON"
        desc = f"Status: **{status_txt}**"
        if state["enabled"] and state.get("reason"):
            desc += f"\nAlasan: {state['reason']}"
        await ctx.send(embed=info_embed("Maintenance Status", desc))
    else:
        await ctx.send(embed=info_embed(
            "Maintenance",
            "`maintenance on [reason]` · `maintenance off` · `maintenance status`"
        ))

@bot.command(name="syncsupport")
@is_owner()
async def pfx_syncsupport(ctx):
    """Backfill badge USER untuk semua member yang sudah ada di server support."""
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if not support_server_id:
        return await ctx.send(embed=error_embed("`SUPPORT_SERVER_ID` belum di-set di environment variable."))
    guild = bot.get_guild(support_server_id)
    if not guild:
        return await ctx.send(embed=error_embed("Bot tidak berada di server support tersebut (cek `SUPPORT_SERVER_ID`)."))
    support_members = cfg.setdefault("support_server_members", [])
    added = 0
    for m in guild.members:
        if m.bot:
            continue
        if m.id not in support_members:
            support_members.append(m.id)
            added += 1
    save_config(cfg)
    await ctx.send(embed=success_embed(
        f"Sync selesai. **{added}** member baru dapat badge **USER**.\nTotal member ber-badge: **{len(support_members)}**."
    ))

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
    is_owner_user = (ctx.author.id == bot.owner_id)
    np_users  = cfg.get("no_prefix_users",  [])
    np_guilds = cfg.get("no_prefix_guilds", [])
    has_np    = (is_owner_user or ctx.author.id in np_users or (ctx.guild and ctx.guild.id in np_guilds)
                 or user_has_premium(ctx.guild, ctx.author))
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
        value='`ticket setup <cat> <log_cat> [role] [max]` · `ticket panel "Judul" "Deskripsi"` · `ticket close [reason]`', inline=False)
    embed.add_field(name=sec(ICON_LEVEL, "Level & XP"),
        value="`rank` · `leaderboard` · `level toggle/setchannel/status` · `xp`", inline=False)
    embed.add_field(name=sec(ICON_GIVEAWAY, "Giveaway"),
        value="`giveaway start/end/reroll/list`\n`--role <id>` · `--winrole <id>`", inline=False)
    embed.add_field(name=sec(ICON_ANTISPAM, "Antispam"),
        value="`antispam setchannel #ch` · `antispam logchannel #ch` · `antispam status`", inline=False)
    embed.add_field(name=sec(ICON_LANGUAGE, "Language"),
        value="`language list` · `language set <code>`", inline=False)
    embed.add_field(name=sec(ICON_OWNER, "Owner Only"), value=(
        "`maintenance on/off/status`\n"
        "`noprefix grant/revoke/list`\n"
        "`botrole set/remove/list`\n"
        "`grantpremium @user <durasi>/revoke`\n"
        "`premiumlock add/remove/list <command>`\n"
        "`syncsupport`\n"
        "`blacklist add/remove/list`\n"
        "`vxleave <guild_id>`"
    ), inline=False)
    embed.set_footer(text=BOT_NAME + " v" + BOT_VERSION + " • " + BOT_TAGLINE)
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════

@bot.tree.command(name="rank", description="Lihat rank card XP kamu atau member lain.")
@app_commands.describe(member="Member yang ingin dilihat ranknya")
async def slash_rank(i: discord.Interaction, member: Optional[discord.Member] = None):
    ctx_like = type("C", (), {"guild": i.guild, "author": i.user, "channel": i.channel,
                              "typing": i.channel.typing, "send": i.followup.send})()
    await i.response.defer()
    target      = member or i.user
    gc          = guild_cfg(cfg, i.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"])
    all_m       = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp",0), reverse=True)
    rank        = next((idx+1 for idx,(uid,_) in enumerate(all_m) if uid == str(target.id)), 1)
    pct         = int((cx / max(nx,1)) * 100)
    avatar_url  = str(target.display_avatar.with_format("png").with_size(256))
    bar_color   = "F59E0B" if user_has_premium(i.guild, target) else "8B0000"
    import aiohttp, io
    api_url = (
        "https://some-random-api.com/canvas/misc/rank-card"
        f"?username={target.display_name}&avatar={avatar_url}"
        f"&currentxp={cx}&neededxp={nx}&level={lvl}&rank={rank}&barcolor={bar_color}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200 and "image" in resp.content_type:
                    img_bytes = await resp.read()
                    file  = discord.File(io.BytesIO(img_bytes), filename="rank.png")
                    embed = discord.Embed(color=int(bar_color,16), timestamp=discord.utils.utcnow())
                    embed.set_author(name=f"Rank Card — {target.display_name}", icon_url=target.display_avatar.url)
                    embed.set_image(url="attachment://rank.png")
                    embed.set_footer(text=f"Total XP: {data['xp']:,} · Messages: {data.get('messages',0):,}")
                    return await i.followup.send(file=file, embed=embed)
    except Exception:
        pass
    bar   = "▰"*int(pct/100*16) + "▱"*(16-int(pct/100*16))
    embed = discord.Embed(description=f"**@{target.display_name}**\n\n**Level: {lvl}** | **XP: {cx:,}/{nx:,}** | **Rank: #{rank}**\n\n`{bar}` {pct}%\n\n*Total XP: {data['xp']:,}*", color=COLOR_PRIMARY)
    embed.set_author(name="Rank Card", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)
    await i.followup.send(embed=embed)

@bot.tree.command(name="leaderboard", description="Lihat top 10 XP leaderboard server ini.")
async def slash_leaderboard(i: discord.Interaction):
    gc    = guild_cfg(cfg, i.guild.id)
    all_d = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp",0), reverse=True)[:10]
    if not all_d:
        return await i.response.send_message(embed=info_embed("Leaderboard", "Belum ada data XP."), ephemeral=True)
    lines = []
    for idx,(uid,data) in enumerate(all_d):
        m     = i.guild.get_member(int(uid))
        name  = m.display_name if m else f"User ({uid[:6]})"
        medal = ["#1","#2","#3"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"**{medal} {name}** — Level **{data.get('level',0)}** · {data.get('xp',0):,} XP")
    embed = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"{BOT_NAME} · {i.guild.name}")
    await i.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="Lihat profile card dan badge kamu atau member lain.")
@app_commands.describe(member="Member yang ingin dilihat profilenya")
async def slash_profile(i: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or i.user
    embed  = build_profile_embed(target)
    embed.set_author(name="Profile & Badge Panel", icon_url=target.display_avatar.url)
    embed.set_footer(
        text=BOT_NAME + " \u2022 ID: " + str(target.id) + "  |  Requested By " + i.user.display_name,
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

@bot.tree.command(name="ping", description="Cek latency bot.")
async def slash_ping(i: discord.Interaction):
    lat = round(bot.latency * 1000)
    await i.response.send_message(embed=base_embed("Pong!", f"Latency: **{lat}ms**", COLOR_SUCCESS if lat < 100 else COLOR_WARNING))

@bot.tree.command(name="help", description="Lihat semua command VALLENT EXS.")
async def slash_help(i: discord.Interaction):
    ctx_like = type("C", (), {"author": i.user, "guild": i.guild})()
    is_owner_user = (i.user.id == bot.owner_id)
    np_users  = cfg.get("no_prefix_users",  [])
    np_guilds = cfg.get("no_prefix_guilds", [])
    has_np    = (is_owner_user or i.user.id in np_users or (i.guild and i.guild.id in np_guilds)
                 or user_has_premium(i.guild, i.user))
    embed = discord.Embed(
        title=f"{BOT_NAME} — Command Reference",
        description=f"*{BOT_TAGLINE}*\n\nPrefix: **`!vx`** · **`!v`**\n" + ("✨ **No-prefix aktif**\n" if has_np else "") + "\u200b",
        color=COLOR_PRIMARY, timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderation", value="`kick` · `ban` · `unban` · `timeout` · `untimeout`\n`warn` · `warnings` · `unwarn` · `clearwarnings`\n`purge` · `lock` · `unlock` · `slowmode`", inline=False)
    embed.add_field(name="Role & Voice", value="`addrole` · `removerole` · `move`", inline=False)
    embed.add_field(name="Info", value="`userinfo` · `serverinfo` · `avatar` · `ping` · `profile`", inline=False)
    embed.add_field(name="Ticket", value='`ticket setup <cat> <log_cat> [role] [max]` · `ticket panel "Judul" "Deskripsi"` · `ticket close [reason]`', inline=False)
    embed.add_field(name="Level & XP", value="`rank` · `leaderboard` · `level` · `xp`", inline=False)
    embed.add_field(name="Giveaway", value="`giveaway start/end/reroll/list`", inline=False)
    embed.add_field(name="Antispam", value="`antispam setchannel` · `antispam status`", inline=False)
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
    badges = get_user_badges(uid)
    role   = get_bot_role(uid)
    embed  = discord.Embed(
        title="Selamat datang di " + member.guild.name + "!",
        description="Halo " + member.mention + "!\n\nKamu baru saja mendapatkan badge **USER**!\nKetik `profile` untuk lihat badge kamu.\n\nKetik `help` untuk lihat semua command.",
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    badge_lines = []
    for b in badges:
        info = BOT_ROLE_BADGES.get(b, BOT_ROLE_BADGES["user"])
        badge_lines.append("\u2022 **" + info["label"] + "**")
    embed.add_field(name="ALL BADGES", value="\n".join(badge_lines), inline=True)
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
