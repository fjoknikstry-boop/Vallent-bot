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
import time
import datetime
import logging
import pytz
from collections import defaultdict
from typing import Optional

logging.basicConfig(level=logging.INFO)

from emoji_config import (
    BADGE_FOUNDER, BADGE_DEVELOPER, BADGE_MANAGEMENT, BADGE_STAFF,
    BADGE_PREMIUM, BADGE_NOPREFIX, BADGE_USER, BADGE_MODERATOR, BADGE_SERVER_MANAGER,
    BADGE_MOONKEEPER,
    ICON_MODERATION, ICON_ROLE, ICON_INFO, ICON_TICKET, ICON_LEVEL,
    ICON_GIVEAWAY, ICON_ANTISPAM, ICON_OWNER,
    ICON_SUCCESS, ICON_ERROR, ICON_WARNING, ICON_LOADING,
    ICON_PROFILE, ICON_BADGES, ICON_COMMANDS, ICON_PREMIUM_TAG,
    ICON_TICKET_OPEN, ICON_TICKET_CLOSE, ICON_GIVEAWAY_REACT, ICON_WINNER,
    ICON_BOOST, ICON_ANTINUKE, ICON_IGNORE, ICON_AUTOMOD, ICON_AUTORESPONSE,
    ICON_AFK, ICON_VERIFICATION,
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
            "custom_badges":     {},
            "user_custom_badges": {},
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
    data.setdefault("custom_badges",      {})   # badge_id -> {"name": str, "emoji": str} — owner-defined, free-form badges
    data.setdefault("user_custom_badges", {})   # uid(str) -> [badge_id, ...] — which custom badges each user holds
    data.setdefault("moonkeeper_users",     [])   # uid list — manual Moonkeeper grants (independent of bot_roles hierarchy)
    data.setdefault("moonkeeper_sync_role", None)  # single Discord role ID synced to Moonkeeper, if any
    data.setdefault("role_sync",        {})
    data.setdefault("votes",            {})
    data.setdefault("support_server_members", [])  # user IDs who have joined the support server
    data.setdefault("commands_run",           {})  # uid -> number of commands run
    data.setdefault("xp_boost",                {})  # uid(str) -> {"expiry": iso, "multiplier": float}
    data.setdefault("join_boost_last_grant",    {})  # uid(str) -> iso timestamp of last support-server-join XP boost grant (anti leave/rejoin farm)
    data.setdefault("maintenance", {"enabled": False, "reason": "", "since": None})
    for gid, gc in data.get("guilds", {}).items():
        _init_guild(gc)
    save_config(data)
    return data

def _init_guild(gc: dict):
    gc.setdefault("main_channel",      None)
    gc.setdefault("announce_channel",  None)
    gc.setdefault("level_channel",     None)
    gc.setdefault("levelup_message",   "{mention} just leveled up to **Level {level}**! Keep chatting in {server} to climb even higher. {roles}")
    # Migration: kalau nilai yang kesimpen masih PERSIS default lama (artinya
    # user belum pernah custom manual), upgrade otomatis ke default baru.
    if gc.get("levelup_message") == "{mention} leveled up to **Level {level}**!":
        gc["levelup_message"] = "{mention} just leveled up to **Level {level}**! Keep chatting in {server} to climb even higher. {roles}"
    gc.setdefault("antispam", {
        "trap_channel": None,
        "log_channel":  None,
        "ignore_users": [],
        "ignore_roles": [],
        "threshold":    SPAM_THRESHOLD,
        "window":       SPAM_WINDOW,
        "flood_count":  5,
        "flood_window": 4,
        "punishment":   "ban",
    })
    gc["antispam"].setdefault("trap_channel", None)
    gc["antispam"].setdefault("log_channel",  None)
    gc["antispam"].setdefault("ignore_users", [])
    gc["antispam"].setdefault("ignore_roles", [])
    gc["antispam"].setdefault("threshold",    SPAM_THRESHOLD)
    gc["antispam"].setdefault("window",       SPAM_WINDOW)
    gc["antispam"].setdefault("flood_count",  5)
    gc["antispam"].setdefault("flood_window", 4)
    gc["antispam"].setdefault("punishment",   "ban")
    # Migration from the old spam_trap_channel key (before the centralized antispam dict existed)
    if "spam_trap_channel" in gc:
        legacy_trap = gc.pop("spam_trap_channel")
        if legacy_trap and not gc["antispam"]["trap_channel"]:
            gc["antispam"]["trap_channel"] = legacy_trap
    gc.setdefault("leveling_enabled",  True)
    gc.setdefault("xp_per_message",    [15, 25])
    gc.setdefault("xp_cooldown",       60)
    gc.setdefault("xp_difficulty",     1.0)
    gc.setdefault("xp_ignore_roles",   [])   # role IDs that never gain XP
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
    gc.setdefault("ignored_channels",  [])   # channel ID -> bot stays fully silent (no commands, no XP)
    gc.setdefault("autoresponses_enabled", True)
    gc.setdefault("autoresponses", {})   # trigger(lower) -> {"trigger","response","match","case_sensitive"}
    gc.setdefault("afk_users", {})   # uid(str) -> {"reason": str, "since": unix_ts}
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
    gc.setdefault("verification", {
        "enabled":            False,
        "channel_id":         None,
        "unverified_role_id": None,
        "verified_role_id":   None,
        "log_channel_id":     None,
        "message_id":         None,
        "panel_message":      "Click **Verify** below — I'll DM you a short captcha to unlock the rest of the server. Make sure your DMs are open!",
        "result_message":     "Thanks for verifying — enjoy your stay!",
    })
    gc["verification"].setdefault("enabled",            False)
    gc["verification"].setdefault("channel_id",         None)
    gc["verification"].setdefault("unverified_role_id", None)
    gc["verification"].setdefault("verified_role_id",   None)
    gc["verification"].setdefault("log_channel_id",     None)
    gc["verification"].setdefault("message_id",         None)
    gc["verification"].setdefault("panel_message",      "Click **Verify** below — I'll DM you a short captcha to unlock the rest of the server. Make sure your DMs are open!")
    gc["verification"].setdefault("result_message",     "Thanks for verifying — enjoy your stay!")
    gc.setdefault("ticket", {"panels": {}})
    gc["ticket"].setdefault("panels", {})
    # Migrate the old ticket structure (single-config, panels as a list) to the multi-panel dict.
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
            "description":  "Click the button below to open a support ticket.",
            "welcome_message": "Thanks for reaching out, {user}! Our support team has been notified and will be with you shortly. Please describe your issue in as much detail as you can.",
            "message_id":   None,
            "channel_id":   None,
        }
    for p in gc["ticket"]["panels"].values():
        p.setdefault("category",     None)
        p.setdefault("log_channel",  None)
        p.setdefault("support_role", None)
        p.setdefault("max_tickets",  1)
        p.setdefault("title",        "Support Tickets")
        p.setdefault("description",  "Click the button below to open a support ticket.")
        p.setdefault("welcome_message", "Thanks for reaching out, {user}! Our support team has been notified and will be with you shortly. Please describe your issue in as much detail as you can.")
        p.setdefault("message_id",   None)
        p.setdefault("channel_id",   None)
    # Migrate the old active_tickets format (uid -> single channel_id int) to the new format (uid -> list).
    for uid, val in list(gc["active_tickets"].items()):
        if isinstance(val, int):
            gc["active_tickets"][uid] = [{"channel_id": val, "panel_id": "default", "opened_at": None, "claimed_by": None}]
        else:
            for tk in val:
                tk.setdefault("claimed_by", None)

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

def xp_for_level(level: int, difficulty: float = 1.0) -> int:
    return round((5 * (level ** 2) + 50 * level + 100) * difficulty)

def level_from_xp(xp: int, difficulty: float = 1.0) -> int:
    level = 0
    while xp >= xp_for_level(level, difficulty):
        xp -= xp_for_level(level, difficulty)
        level += 1
    return level

def xp_progress(total_xp: int, difficulty: float = 1.0):
    level = 0
    xp    = total_xp
    while xp >= xp_for_level(level, difficulty):
        xp -= xp_for_level(level, difficulty)
        level += 1
    return level, xp, xp_for_level(level, difficulty)

def get_member_xp(gc: dict, uid: str) -> dict:
    data = gc["members_xp"].setdefault(uid, {"xp": 0, "level": 0, "last_msg_ts": 0.0, "messages": 0})
    data.setdefault("messages", 0)
    return data

async def apply_level_roles(guild: discord.Guild, member: discord.Member, gc: dict, new_level: int) -> list:
    """Grant every level-role reward whose level is <= new_level that the member
    doesn't already have (stacking — once granted, earlier roles are never removed).
    Returns the list of roles that were just granted (for display in the level-up notification)."""
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
            await member.add_roles(role, reason=f"Level role reward — reached level {lvl}")
            granted.append(role)
        except Exception as e:
            logging.error(f"[{BOT_NAME}] Failed to grant level role {role_id} to {member.id}: {e}")
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
        # Only process real slash-command invocations — let autocomplete
        # and other interaction types pass through untouched.
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

        # ── Maintenance mode — only the owner can bypass ────────────────
        if is_maintenance_on() and not is_owner_:
            m = cfg.get("maintenance", {})
            desc = f"**{BOT_NAME}** is under maintenance, please try again later."
            if m.get("reason"):
                desc += f"\n\n**Reason:** {m['reason']}"
            try:
                await interaction.response.send_message(
                    embed=warning_embed("Under Maintenance", desc), ephemeral=True)
            except discord.InteractionResponded:
                pass
            return False

        # ── Premium-locked command ──────────────────────────────────────
        if cmd_name in cfg.get("premium_commands", []) and not is_owner_ and not user_has_premium(interaction.guild, interaction.user):
            try:
                kwargs = {"embed": warning_embed(
                    "Premium Required",
                    f"Command `/{cmd_name}` is for **Premium** users only.\n"
                    "Contact the owner or join the support server to subscribe."
                ), "ephemeral": True}
                view = premium_upsell_view()
                if view:
                    kwargs["view"] = view
                await interaction.response.send_message(**kwargs)
            except discord.InteractionResponded:
                pass
            return False

        # ── Command usage counter ────────────────────────────────────────
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

def bot_invite_url() -> Optional[str]:
    """Build the bot's OAuth2 invite URL. Returns None if the bot hasn't
    logged in yet (bot.user unavailable)."""
    if not bot.user:
        return None
    perms = discord.Permissions(
        kick_members=True, ban_members=True, moderate_members=True,
        manage_roles=True, manage_channels=True, manage_messages=True,
        manage_guild=True, manage_webhooks=True, manage_emojis=True,
        view_audit_log=True, mention_everyone=True, embed_links=True,
        attach_files=True, read_message_history=True, send_messages=True,
        add_reactions=True, connect=True, move_members=True,
        use_external_emojis=True,
    )
    return discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=("bot", "applications.commands"))

def invite_support_view() -> discord.ui.View:
    """Shared 'Invite Me' / 'Support' link-button row — used by the mention
    auto-reply and the help menu. Support button only appears if SUPPORT_INVITE
    is configured and looks like a real URL."""
    view = discord.ui.View()
    invite_url = bot_invite_url()
    if invite_url:
        view.add_item(discord.ui.Button(label="Invite Me", style=discord.ButtonStyle.link, url=invite_url))
    if SUPPORT_INVITE and SUPPORT_INVITE.startswith(("http://", "https://")):
        view.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.link, url=SUPPORT_INVITE))
    return view

def premium_upsell_view() -> Optional[discord.ui.View]:
    """Single 'Get Premium' link button pointing at the support server —
    shown whenever someone hits a Premium-locked command. Returns None if
    SUPPORT_INVITE isn't configured, so callers can skip attaching a view."""
    if not (SUPPORT_INVITE and SUPPORT_INVITE.startswith(("http://", "https://"))):
        return None
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Get Premium", style=discord.ButtonStyle.link, url=SUPPORT_INVITE, emoji="💎"))
    return view

def bot_info_embed(mention: str, guild_id: int) -> discord.Embed:
    """The card shown when the bot is @mentioned directly in chat."""
    embed = discord.Embed(
        title=f"{BOT_NAME} — INFO",
        description=(
            f"Hey {mention},\n"
            f"My prefix here is: `!vx` (`!v` also works)\n"
            f"Server ID: `{guild_id}`\n\n"
            f"Type `!vx help` to see the command list."
        ),
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=BOT_TAGLINE)
    return embed

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
                    "Premium Expired",
                    f"Your Premium subscription on **{BOT_NAME}** has ended.\n"
                    "All premium commands and no-prefix access have been disabled.\n"
                    "Contact the owner if you'd like to renew.",
                    color=COLOR_ERROR
                ))
            except Exception:
                pass

def user_has_no_prefix(guild: Optional[discord.Guild], user: discord.abc.User) -> bool:
    """No-prefix is active for: the owner, manually-granted users (with/without a
    duration), granted guilds, or anyone with active Premium (Premium auto-unlocks no-prefix)."""
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
                    "No-Prefix Expired",
                    f"Your no-prefix access on **{BOT_NAME}** has ended.\n"
                    "Commands now need the `!vx` prefix again.\n"
                    "Contact the owner if you'd like to renew.",
                    color=COLOR_ERROR
                ))
            except Exception:
                pass

def is_maintenance_on() -> bool:
    return bool(cfg.get("maintenance", {}).get("enabled", False))

def grant_xp_boost(uid: int, minutes: int = 60, multiplier: float = 1.10):
    """Grant a temporary XP boost — used as an incentive for joining the support
    server. Applies across ALL guilds (not per-guild) since this is a personal
    reward, not a server setting."""
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
    cfg.setdefault("xp_boost", {})[str(uid)] = {"expiry": expiry.isoformat(), "multiplier": multiplier}
    save_config(cfg)

def can_receive_join_boost(uid: int, cooldown_hours: int = 24) -> bool:
    """Anti-farm guard for the support-server join XP boost. Without this,
    someone could leave and rejoin the support server on repeat to keep
    resetting the boost's 60-minute timer and hold +10% XP indefinitely for
    free. Limits a fresh grant to once per `cooldown_hours` per user —
    genuine returning members still get it, repeat leave/rejoin spam doesn't."""
    last = cfg.setdefault("join_boost_last_grant", {}).get(str(uid))
    if not last:
        return True
    try:
        last_dt = datetime.datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return True
    return datetime.datetime.now(datetime.timezone.utc) - last_dt >= datetime.timedelta(hours=cooldown_hours)

def mark_join_boost_granted(uid: int):
    cfg.setdefault("join_boost_last_grant", {})[str(uid)] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_config(cfg)

def get_xp_multiplier(uid: int) -> float:
    """Return the active XP multiplier for a user (1.0 if no boost / already expired).
    Expired entries are cleaned up automatically (lazy cleanup, same pattern as premium)."""
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
    """Return the expiry time of an active boost, or None if there isn't one."""
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
    # Emoji sourced from emoji_config.py — edit that file to set the emoji IDs
    "founder":        {"label": "• Founder",        "color": 0x8B0000, "emoji": BADGE_FOUNDER},
    "developer":      {"label": "• Developer",      "color": 0xDC143C, "emoji": BADGE_DEVELOPER},
    "management":     {"label": "• Management",     "color": 0xB22222, "emoji": BADGE_MANAGEMENT},
    "moonkeeper":     {"label": "• Moonkeeper",      "color": 0x6366F1, "emoji": e(BADGE_MOONKEEPER, "🌙")},
    "server_manager": {"label": "• Server Manager", "color": 0xE67E22, "emoji": e(BADGE_SERVER_MANAGER, "🗂️")},
    "moderator":      {"label": "• Moderator",      "color": 0xC97C3D, "emoji": e(BADGE_MODERATOR, "🛡️")},
    "staff":          {"label": "• Staff",          "color": 0xCD5C5C, "emoji": BADGE_STAFF},
    "premium":        {"label": "• Premium",        "color": 0xF59E0B, "emoji": BADGE_PREMIUM},
    "noprefix":       {"label": "• No Prefix",      "color": 0x22C55E, "emoji": BADGE_NOPREFIX},
    "user":           {"label": "• User",           "color": 0x6B7280, "emoji": BADGE_USER},
}

def get_support_guild() -> Optional[discord.Guild]:
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    return bot.get_guild(support_server_id) if support_server_id else None

def get_synced_role(uid: int) -> Optional[str]:
    """Check the user's real Discord role in the support server against the
    role_sync mapping. Checked from highest (founder) to lowest (staff) — if the
    member has multiple synced roles, the highest badge wins."""
    guild = get_support_guild()
    if not guild:
        return None
    member = guild.get_member(uid)
    if not member:
        return None
    role_sync = cfg.get("role_sync", {})
    for tier in reversed(BOT_ROLE_HIERARCHY):  # founder -> developer -> management -> staff
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
    Collect all of a user's badges.
    Hierarchy: founder > developer > management > staff > noprefix > premium > user
    The USER badge is only granted if the user has joined the bot's support server.
    If they have no badges at all -> empty list.
    """
    badges  = []
    role    = get_bot_role(uid)
    is_prem = uid in cfg.get("premium_users", [])
    if role != "user":
        badges.append(role)
    if is_moonkeeper(uid):
        badges.append("moonkeeper")
    if uid in cfg.get("no_prefix_users", []) or is_prem:
        badges.append("noprefix")
    if is_prem:
        badges.append("premium")
    if uid in cfg.get("support_server_members", []):
        badges.append("user")
    # No default badge — if it's empty, it stays empty
    return badges

# ══════════════════════════════════════════════════════════════════
# CUSTOM BADGES — free-form badges the owner designs and assigns
# ══════════════════════════════════════════════════════════════════
# Fully independent from BOT_ROLE_BADGES above. Name and emoji are 100%
# up to the owner (any text, any emoji including custom server emoji) —
# these aren't tied to a hierarchy or a Discord role, just a manual grant
# stored per-user. Only the bot owner can create/delete/give/remove them
# (see the `custombadge` command further down).

def _sanitize_badge_name(name: str) -> str:
    """Strip any Discord mention syntax (@user, @role, #channel, @everyone/
    @here) out of a badge name. Badge names are just display text — a
    mention accidentally typed while naming a badge (e.g. `custombadge
    create 🔥 Monarch @Niks.`) should never turn into a real, clickable/
    pinging tag on the profile card."""
    name = re.sub(r"<@!?\d+>|<@&\d+>|<#\d+>", "", name)
    name = re.sub(r"@(everyone|here)", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def _slugify_badge_id(name: str) -> str:
    """Turn a badge name into a short, stable dict key (e.g. 'Dragon Tamer'
    -> 'dragon_tamer'). If that slug is already used by a different badge,
    suffix it with a counter so two similarly-named badges never collide
    or silently overwrite each other."""
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "badge"
    defs = cfg.get("custom_badges", {})
    slug = base
    n = 2
    while slug in defs:
        slug = f"{base}_{n}"
        n += 1
    return slug

def get_custom_badges(uid: int) -> list:
    """Return this user's owner-granted custom badges, in the order they
    were given, as {"id", "name", "emoji"} dicts. If the owner later deletes
    a badge's definition, it's silently dropped here instead of erroring."""
    defs = cfg.get("custom_badges", {})
    ids  = cfg.get("user_custom_badges", {}).get(str(uid), [])
    return [{"id": bid, **defs[bid]} for bid in ids if bid in defs]

def _badge_display_lines(uid: int) -> tuple:
    """Build the formatted '<emoji> **Name**' lines for every badge a user
    holds — bot-role badges (Founder/Staff/etc.) first, then owner-granted
    custom badges — plus the total count. Shared by the profile embed and
    the support-server welcome DM so the two can never drift out of sync."""
    lines = []
    for b in get_user_badges(uid):
        info      = BOT_ROLE_BADGES.get(b, BOT_ROLE_BADGES["user"])
        emoji_str = info.get("emoji", "")
        prefix    = (emoji_str + " ") if emoji_str else "\u2022 "
        lines.append(prefix + "**" + info["label"] + "**")
    for cb in get_custom_badges(uid):
        emoji_str = cb.get("emoji", "")
        prefix    = (emoji_str + " ") if emoji_str else "\u2022 "
        lines.append(prefix + "**\u2022 " + cb["name"] + "**")
    return lines, len(lines)

def _resolve_badge_target(token: str) -> Optional[int]:
    """Parse a user mention or raw ID into an int. Returns None if the
    token isn't a valid user reference. Deliberately doesn't require the
    target to be a member of the current guild — custom badges are global
    (bot-wide), same as the bot-role badges, so the owner can badge anyone
    the bot has ever seen from any server."""
    m = re.match(r"<@!?(\d+)>$|^(\d{17,20})$", token.strip())
    if not m:
        return None
    return int(m.group(1) or m.group(2))

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

    # ── ALL BADGES — its own field, one badge per line (bot-role badges +
    # owner-granted custom badges, in that order) ───────────────────────
    badge_lines, total_badges = _badge_display_lines(uid)
    if badge_lines:
        badges_value = "\n".join(badge_lines)
    else:
        invite = SUPPORT_INVITE
        badges_value = "No badges yet."
        if invite:
            badges_value += "\n[Join the support server](" + invite + ") to get the **USER** badge!"
        else:
            badges_value += "\nJoin the support server to get the **USER** badge!"

    badges_icon = e(ICON_BADGES, "✨")
    embed.add_field(name=f"{badges_icon} __ALL BADGES__".strip(), value=badges_value, inline=False)

    # ── Total Badges & Commands Runned — two fields side by side ───────
    embed.add_field(name="Total Badges", value="**" + str(total_badges) + "**", inline=True)
    embed.add_field(name=f"{e(ICON_COMMANDS, '⚙️')} Commands Runned".strip(), value="**" + str(cmds_run) + "**", inline=True)

    # ── Premium — its own field, only shown if active ───────────────────
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

spam_tracker:       dict[tuple, dict[str, dict]] = defaultdict(dict)  # (guild_id, uid) -> fingerprint -> entry
spam_cleanup_times: dict[tuple, float]           = {}
flood_tracker:      dict[tuple, list]             = defaultdict(list)  # (guild_id, uid) -> [timestamps]

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

def _antispam_is_ignored(member: discord.Member, ac: dict) -> bool:
    """True if this member should be skipped from all antispam detection —
    bot owner, manage_guild (staff/admin), or on the manual ignore list."""
    if member.id == bot.owner_id:
        return True
    if member.guild_permissions.manage_guild:
        return True
    if member.id in ac.get("ignore_users", []):
        return True
    role_ids = {r.id for r in member.roles}
    if role_ids & set(ac.get("ignore_roles", [])):
        return True
    return False

async def _antispam_punish(guild: discord.Guild, member: discord.Member, punishment: str, reason: str) -> str:
    """Execute the antispam punishment, return a short string for the log."""
    try:
        if punishment == "kick":
            await guild.kick(member, reason=reason)
            return "**KICKED**"
        elif punishment == "timeout":
            await member.timeout(datetime.timedelta(hours=1), reason=reason)
            return "**TIMEOUT** (1 hour)"
        else:  # ban — default, the harshest option for spam bots/raids
            await guild.ban(member, reason=reason, delete_message_seconds=86400)
            return "**BANNED**"
    except discord.Forbidden:
        return "⚠️ FAILED — bot lacks permission, or its role is lower than the target's"
    except Exception as e:
        logging.error(f"[{BOT_NAME}] Failed to execute antispam punishment: {e}")
        return f"⚠️ FAILED — {e}"

async def _antispam_log(guild: discord.Guild, gc: dict, member: discord.Member, kind: str, detail: str, result: str):
    """Send a report to the antispam log channel (if set) — shared by the
    honeypot, cross-channel spam, and flood detector for consistency."""
    ac     = gc.get("antispam", {})
    log_id = ac.get("log_channel") or _fallback_log_channel(gc)
    if not log_id:
        return
    log_ch = guild.get_channel(log_id)
    if not log_ch:
        return
    emb = base_embed(f"Antispam: {kind}", None, color=COLOR_ERROR)
    emb.add_field(name="User",   value=f"{member.mention} (`{member.id}`)", inline=True)
    emb.add_field(name="Action", value=result, inline=True)
    emb.add_field(name="Detail", value=detail, inline=False)
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.set_footer(text=BOT_NAME)
    try:
        await log_ch.send(embed=emb)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════
# OWNER / PERMISSION HELPERS
# ══════════════════════════════════════════════════════════════════

OWNER_ONLY_CMDS = {"maintenance", "noprefix", "botrole", "grantpremium", "premiumlock", "blacklist", "vxleave", "vxservers", "vxguilds", "ownerhelp"}

def is_owner():
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.id == bot.owner_id
    return commands.check(predicate)

def is_moonkeeper(uid: int) -> bool:
    """Independent of the staff hierarchy on purpose — Moonkeeper is a
    standalone permission flag, not a rank on the same ladder as
    staff/moderator/management/etc. That means holding a higher moderation
    tier never silently suppresses Moonkeeper (or vice versa): someone can
    be Management AND Moonkeeper at the same time, and both badges/both
    powers show up. Checked two ways: a manual per-user grant, or a synced
    Discord role in the support server (mirrors how the other tiers sync)."""
    if uid in cfg.get("moonkeeper_users", []):
        return True
    role_id = cfg.get("moonkeeper_sync_role")
    if role_id:
        guild = get_support_guild()
        member = guild.get_member(uid) if guild else None
        if member and any(r.id == role_id for r in member.roles):
            return True
    return False

def can_manage_access(uid: int) -> bool:
    """True for the bot owner, or anyone currently flagged as Moonkeeper
    (see `is_moonkeeper`) — a dedicated, standalone permission for this one
    power, separate from the moderation tiers so day-to-day staff can't
    cascade this access to others. Moonkeepers can grant/revoke no-prefix
    and premium on the owner's behalf, treated exactly as if the owner did
    it. Revoking it is instant and total: `botrole remove @user` for a
    manual grant, or removing the Discord role / `botrole sync remove
    moonkeeper` for a synced one — either way the person loses this power
    immediately, no separate permission list to clean up."""
    if uid == bot.owner_id:
        return True
    return is_moonkeeper(uid)

def is_owner_or_staff():
    async def predicate(ctx: commands.Context) -> bool:
        return can_manage_access(ctx.author.id)
    return commands.check(predicate)

def is_staff_or_above(uid: int) -> bool:
    role = get_bot_role(uid)
    return role in BOT_ROLE_HIERARCHY

@bot.check
async def global_maintenance_check(ctx: commands.Context) -> bool:
    if ctx.author.id == bot.owner_id or not is_maintenance_on():
        return True
    m    = cfg.get("maintenance", {})
    desc = f"**{BOT_NAME}** is under maintenance, please try again later."
    if m.get("reason"):
        desc += f"\n\n**Reason:** {m['reason']}"
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
    kwargs = {"embed": warning_embed(
        "Premium Required",
        f"Command `{cmd}` is for **Premium** users only.\n"
        "Contact the owner or join the support server to subscribe."
    )}
    view = premium_upsell_view()
    if view:
        kwargs["view"] = view
    await ctx.send(**kwargs)
    return False

# ══════════════════════════════════════════════════════════════════
# MODERATION HELPERS
# ══════════════════════════════════════════════════════════════════

def _is_protected(guild: discord.Guild, member: discord.Member) -> bool:
    """Check whether this member cannot be moderated (guild owner or a role higher than the bot's)."""
    if member.id == guild.owner_id:
        return True
    if guild.me and member.top_role >= guild.me.top_role:
        return True
    return False

async def do_kick(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.kick_members:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("This user can't be kicked."))
    try:
        await member.kick(reason=f"{author} | {reason}")
        await reply_fn(embed=success_embed(f"{member.mention} has been kicked. Reason: {reason}"))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to kick."))

async def do_ban(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.ban_members:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("This user can't be banned."))
    try:
        await guild.ban(member, reason=f"{author} | {reason}", delete_message_days=0)
        await reply_fn(embed=success_embed(f"{member.mention} has been banned. Reason: {reason}"))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to ban."))

def _parse_timeout_duration(duration: str) -> Optional[datetime.timedelta]:
    """Parse a timeout duration into a timedelta. Accepts a bare number
    (minutes, kept for backwards compatibility with the old `timeout
    @user 60` usage) or a suffixed value: `30s`, `10m`, `2h`, `1d`, `1w`.
    Returns None if the format is invalid or works out to zero/negative.
    Discord itself caps timeouts at 28 days, so anything longer just gets
    clamped down to that instead of failing the command."""
    duration = duration.strip().lower()
    if duration.isdigit():
        amount, unit = int(duration), "m"
    else:
        m = re.fullmatch(r"(\d+)\s*(s|m|h|d|w)", duration)
        if not m:
            return None
        amount, unit = int(m.group(1)), m.group(2)
    if amount <= 0:
        return None
    delta = {
        "s": datetime.timedelta(seconds=amount),
        "m": datetime.timedelta(minutes=amount),
        "h": datetime.timedelta(hours=amount),
        "d": datetime.timedelta(days=amount),
        "w": datetime.timedelta(weeks=amount),
    }[unit]
    return min(delta, datetime.timedelta(days=28))

async def do_timeout(guild, author, member, duration, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.moderate_members:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    if _is_protected(guild, member):
        return await reply_fn(embed=error_embed("This user can't be timed out."))
    delta = _parse_timeout_duration(str(duration))
    if not delta:
        return await reply_fn(embed=error_embed(
            "Invalid duration. Use a plain number of minutes, or a suffixed value like "
            "`30s`, `10m`, `2h`, `1d`, `1w` (max 28 days)."
        ))
    try:
        until = discord.utils.utcnow() + delta
        await member.timeout(until, reason=f"{author} | {reason}")
        await reply_fn(embed=success_embed(
            f"{member.mention} has been timed out until {discord.utils.format_dt(until, 'f')} "
            f"({discord.utils.format_dt(until, 'R')})."
        ))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to timeout members."))

async def do_warn(guild, author, member, reason, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_messages:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
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
    await reply_fn(embed=success_embed(f"{member.mention} has been warned. Reason: {reason}"))

async def do_addrole(guild, author, member, role, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_roles:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    try:
        await member.add_roles(role, reason=f"By {author}")
        await reply_fn(embed=success_embed(f"Role {role.name} added to {member.mention}."))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to manage roles."))

async def do_removerole(guild, author, member, role, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.manage_roles:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    try:
        await member.remove_roles(role, reason=f"By {author}")
        await reply_fn(embed=success_embed(f"Role {role.name} removed from {member.mention}."))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to manage roles."))

async def do_move(guild, author, member, channel, reply_fn):
    if author.id != bot.owner_id and not author.guild_permissions.move_members:
        return await reply_fn(embed=error_embed("You don't have permission to use this command."))
    try:
        await member.move_to(channel, reason=f"By {author}")
        await reply_fn(embed=success_embed(f"{member.mention} moved to {channel.name}."))
    except discord.Forbidden:
        await reply_fn(embed=error_embed("The bot doesn't have permission to move members."))

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

    # Link buttons so the person can grab a full-res static copy straight
    # away, without needing to right-click -> Open Image -> Save manually.
    avatar = member.display_avatar
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Download PNG", style=discord.ButtonStyle.link,
        url=avatar.with_format("png").with_size(1024).url
    ))
    view.add_item(discord.ui.Button(
        label="Download JPG", style=discord.ButtonStyle.link,
        url=avatar.with_format("jpg").with_size(1024).url
    ))
    await reply_fn(embed=embed, view=view)

async def do_ping(reply_fn):
    lat = round(bot.latency * 1000)
    embed = base_embed("Pong!", f"Latency: **{lat}ms**", COLOR_SUCCESS if lat < 100 else COLOR_WARNING)
    await reply_fn(embed=embed)

async def do_afk_set(guild: discord.Guild, author: discord.abc.User, reason: str, reply_fn):
    """Mark `author` as AFK in this guild. Any message they send afterwards
    (other than re-running `afk`) automatically clears it — see on_message.
    Anyone who @mentions them while AFK gets an embed with their reason."""
    gc       = guild_cfg(cfg, guild.id)
    afk_map  = gc.setdefault("afk_users", {})
    reason   = (reason or "").strip()[:200] or "AFK"
    since_ts = int(discord.utils.utcnow().timestamp())
    afk_map[str(author.id)] = {"reason": reason, "since": since_ts}
    save_config(cfg)

    embed = base_embed(
        _title_with_icon(ICON_AFK, "💤", "AFK Notice"),
        "-# Sending any message will automatically clear this status.",
        color=COLOR_PRIMARY
    )
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.add_field(name="Reason", value=reason, inline=True)
    embed.add_field(name="Duration", value=f"<t:{since_ts}:R>", inline=True)
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
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
            return {"success": False, "error": "An emoji name is required."}
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return {"success": False, "error": f"Failed to fetch image: HTTP {r.status}"}
                data = await r.read()
        emoji = await guild.create_custom_emoji(name=name, image=data)
        return {"success": True, "emoji": emoji}
    except discord.Forbidden:
        return {"success": False, "error": "The bot doesn't have permission to manage emojis."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ══════════════════════════════════════════════════════════════════
# TICKET HANDLER
# ══════════════════════════════════════════════════════════════════

def _fallback_log_channel(gc: dict) -> Optional[int]:
    """Used by the general honeypot/log system when mod_log_channel isn't set —
    borrows the log channel from the antispam config, then falls back to the
    first ticket panel that has one."""
    if gc.get("antispam", {}).get("log_channel"):
        return gc["antispam"]["log_channel"]
    if gc.get("mod_log_channel"):
        return gc["mod_log_channel"]
    for p in gc["ticket"]["panels"].values():
        if p.get("log_channel"):
            return p["log_channel"]
    return None

def _find_active_ticket(gc: dict, channel_id: int):
    """Find an active ticket by channel_id.
    Returns (uid_str, ticket_dict, panel_dict) or (None, None, None)."""
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
            embed=error_embed("This ticket panel hasn't been configured properly."), ephemeral=True)

    tickets    = gc["active_tickets"].setdefault(uid, [])
    same_panel = [tk for tk in tickets if tk.get("panel_id") == panel_id and interaction.guild.get_channel(tk.get("channel_id"))]
    max_t      = panel.get("max_tickets", 1)
    if len(same_panel) >= max_t:
        ch  = interaction.guild.get_channel(same_panel[0]["channel_id"]) if same_panel else None
        msg = "You already have an open ticket." if max_t == 1 else \
            f"You already have {len(same_panel)}/{max_t} open tickets for the **{panel.get('title', panel_id)}** panel."
        if ch:
            msg += f"\n{ch.mention}"
        return await interaction.response.send_message(embed=error_embed(msg), ephemeral=True)

    category = interaction.guild.get_channel(panel["category"])
    if not category:
        return await interaction.response.send_message(
            embed=error_embed("Ticket category not found."), ephemeral=True)

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
        "claimed_by": None,
    })
    save_config(cfg)

    welcome_text = (panel.get("welcome_message") or "Thanks for reaching out, {user}! Our support team will be with you shortly.")
    welcome_text = (welcome_text
                    .replace("{user}",   interaction.user.mention)
                    .replace("{server}", interaction.guild.name)
                    .replace("{panel}",  panel.get("title") or panel_id))
    welcome_embed = base_embed(
        panel.get("title") or f"Ticket — {interaction.user.display_name}",
        welcome_text,
        color=COLOR_PRIMARY
    )
    await ch.send(content=interaction.user.mention, embed=welcome_embed, view=TicketControlView())

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
        embed=success_embed(f"Your ticket has been created: {ch.mention}"),
        ephemeral=True
    )

async def close_ticket_channel(guild: discord.Guild, channel: discord.abc.GuildChannel,
                                closer: discord.abc.User, reason: str, send_confirmation) -> bool:
    """Core ticket-closing logic, shared by the Close button and the `ticket close` command.
    The log is sent to the log channel belonging to the ticket's PANEL, not a global log channel."""
    gc = guild_cfg(cfg, guild.id)
    uid, tk, panel = _find_active_ticket(gc, channel.id)
    if not tk:
        await send_confirmation(embed=error_embed("This channel isn't an active ticket."))
        return False

    is_owner_  = closer.id == bot.owner_id
    can_manage = getattr(closer, "guild_permissions", None) and closer.guild_permissions.manage_channels
    if not (is_owner_ or can_manage or str(closer.id) == uid):
        await send_confirmation(embed=error_embed("You can't close this ticket."))
        return False

    gc["active_tickets"][uid] = [x for x in gc["active_tickets"][uid] if x.get("channel_id") != channel.id]
    if not gc["active_tickets"][uid]:
        del gc["active_tickets"][uid]
    save_config(cfg)

    reason = reason or "Closed via command."
    await send_confirmation(embed=base_embed(
        "Ticket Closing", f"Closed by {closer.mention}.\n{reason}\n\nChannel will be deleted in 5 seconds.", color=COLOR_ERROR))

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
            claimed_by   = tk.get("claimed_by")
            claimer      = guild.get_member(claimed_by) if claimed_by else None
            log_emb = base_embed("Ticket Closed", None, color=COLOR_ERROR)
            log_emb.add_field(name="Ticket Owner", value=f"{owner_member.mention if owner_member else '<@'+uid+'>'} (`{uid}`)", inline=True)
            log_emb.add_field(name="Closed By",    value=closer.mention, inline=True)
            log_emb.add_field(name="Claimed By",   value=claimer.mention if claimer else "*(unclaimed)*", inline=True)
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

# ══════════════════════════════════════════════════════════════════
# VERIFICATION SYSTEM — captcha gate for new members
# ══════════════════════════════════════════════════════════════════
# Fully opt-in per guild: nothing happens on join until an admin sets a
# channel + an Unverified role + a Verified role, then runs
# `verification enable`. Until then this whole system stays dormant.
#
# Pending captchas are kept in memory only (a few minutes at most) —
# same reasoning as antinuke's sliding-window tracker: short-lived by
# nature, no benefit to persisting them across a bot restart.

_PENDING_CAPTCHAS: dict = {}   # uid -> {"code","guild_id","expires","attempts"}
CAPTCHA_TTL     = 300   # seconds a generated code stays valid
CAPTCHA_MAX_TRY = 3     # wrong guesses allowed before a fresh code is required

async def _apply_unverified_role(member: discord.Member):
    """Hooked into on_member_join for every guild the bot is in — a no-op
    unless that specific guild has verification configured and enabled."""
    gc = guild_cfg(cfg, member.guild.id)
    vc = gc.get("verification", {})
    if not vc.get("enabled"):
        return
    role = member.guild.get_role(vc.get("unverified_role_id") or 0)
    if not role:
        return
    try:
        await member.add_roles(role, reason="Verification system — pending captcha")
    except (discord.Forbidden, discord.HTTPException):
        pass

async def _complete_verification(member: discord.Member, gc: dict) -> bool:
    """Swap Unverified -> Verified and post an optional log entry. Returns
    False if the Verified role is missing/unassignable so the caller can
    tell the member to ping staff instead of silently doing nothing."""
    vc         = gc.get("verification", {})
    ver_role   = member.guild.get_role(vc.get("verified_role_id") or 0)
    unver_role = member.guild.get_role(vc.get("unverified_role_id") or 0)
    if not ver_role:
        return False
    try:
        if ver_role not in member.roles:
            await member.add_roles(ver_role, reason="Verification system — captcha passed")
        if unver_role and unver_role in member.roles:
            await member.remove_roles(unver_role, reason="Verification system — captcha passed")
    except (discord.Forbidden, discord.HTTPException):
        return False

    log_ch = member.guild.get_channel(vc.get("log_channel_id") or 0)
    if log_ch:
        emb = base_embed(f"{e(ICON_VERIFICATION, '🔐')} Member Verified", f"{member.mention} completed the captcha and was verified.", color=COLOR_SUCCESS)
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.set_footer(text=BOT_NAME)
        try:
            await log_ch.send(embed=emb)
        except Exception:
            pass
    return True

def _verification_result_embed(user: discord.abc.User, success: bool, gc: dict) -> discord.Embed:
    """Detailed result card shown after a verification attempt concludes
    (either passed, or exhausted its attempts/expired) — username, a clear
    pass/fail status, the exact time, and the server's custom message.
    Always dark red regardless of outcome, per how this bot's brand embeds
    are themed."""
    vc     = gc.get("verification", {})
    words  = vc.get("result_message") or "Thanks for verifying — enjoy your stay!"
    now_ts = int(discord.utils.utcnow().timestamp())
    embed  = discord.Embed(
        title=f"{e(ICON_VERIFICATION, '🔐')} Verification Result",
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Username", value=str(user), inline=True)
    embed.add_field(name="Status", value="✅ Verified" if success else "❌ Failed", inline=True)
    embed.add_field(name="Verification Time", value=f"<t:{now_ts}:F>", inline=False)
    embed.add_field(name="Message", value=words, inline=False)
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=BOT_NAME)
    return embed

class CaptchaModal(discord.ui.Modal, title="Enter the Verification Code"):
    code_input = discord.ui.TextInput(
        label="Type the code shown in the image",
        placeholder="e.g. NHR3K4",
        min_length=4, max_length=8, required=True
    )

    def __init__(self):
        super().__init__(timeout=180)

    async def on_submit(self, interaction: discord.Interaction):
        pending = _PENDING_CAPTCHAS.get(interaction.user.id)
        if not pending:
            return await interaction.response.send_message(
                embed=error_embed("That code expired or wasn't found — go back to the server and click **Verify** again to get a new one.")
            )

        # This modal is submitted from a DM, where interaction.guild is
        # always None — the guild/member have to be resolved from what we
        # captured back when the Verify button was first clicked.
        guild = bot.get_guild(pending["guild_id"])
        if not guild:
            _PENDING_CAPTCHAS.pop(interaction.user.id, None)
            return await interaction.response.send_message(
                embed=error_embed("Couldn't reach that server anymore — please try again from the server.")
            )
        member = guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.NotFound:
                member = None
        if not member:
            _PENDING_CAPTCHAS.pop(interaction.user.id, None)
            return await interaction.response.send_message(
                embed=error_embed("You don't appear to be a member of that server anymore.")
            )
        gc = guild_cfg(cfg, guild.id)

        if time.monotonic() > pending["expires"]:
            _PENDING_CAPTCHAS.pop(interaction.user.id, None)
            return await interaction.response.send_message(embed=_verification_result_embed(member, False, gc))
        if self.code_input.value.strip().upper() != pending["code"]:
            pending["attempts"] += 1
            if pending["attempts"] >= CAPTCHA_MAX_TRY:
                _PENDING_CAPTCHAS.pop(interaction.user.id, None)
                return await interaction.response.send_message(embed=_verification_result_embed(member, False, gc))
            left = CAPTCHA_MAX_TRY - pending["attempts"]
            return await interaction.response.send_message(
                embed=error_embed(f"That's not quite right. **{left}** attempt(s) left before you'll need a new code.")
            )

        _PENDING_CAPTCHAS.pop(interaction.user.id, None)
        ok = await _complete_verification(member, gc)
        if ok:
            await interaction.response.send_message(embed=_verification_result_embed(member, True, gc))
        else:
            await interaction.response.send_message(
                embed=error_embed(
                    "The Verified role couldn't be applied — the bot may be missing permissions, its role "
                    "may be positioned too low, or the role was deleted. Please ping staff for help."
                )
            )

class CaptchaEnterView(discord.ui.View):
    """One-off view attached to a single captcha image sent via DM — not
    persistent (unlike VerificationView below), since it's only ever
    valid for the short life of that specific code anyway."""
    def __init__(self):
        super().__init__(timeout=CAPTCHA_TTL)

    @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.success, emoji="⌨️")
    async def enter_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        pending = _PENDING_CAPTCHAS.get(interaction.user.id)
        if not pending:
            return await interaction.response.send_message(
                embed=error_embed("This code expired. Go back to the server and click **Verify** again.")
            )
        await interaction.response.send_modal(CaptchaModal())

class VerificationView(discord.ui.View):
    """Persistent, static view — one shared custom_id, re-registered via
    bot.add_view() in on_ready so the button keeps working across bot
    restarts (same pattern as TicketControlView below)."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.secondary, custom_id="vx_verify_start")
    async def verify_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        gc = guild_cfg(cfg, interaction.guild.id)
        vc = gc.get("verification", {})
        if not vc.get("enabled"):
            return await interaction.response.send_message(
                embed=error_embed("Verification isn't set up on this server."), ephemeral=True
            )
        ver_role = interaction.guild.get_role(vc.get("verified_role_id") or 0)
        if ver_role and ver_role in interaction.user.roles:
            return await interaction.response.send_message(
                embed=info_embed("Already Verified", "You're already verified — no need to do this again!"),
                ephemeral=True
            )

        code = rank_card.generate_captcha_code()
        img  = rank_card.render_captcha_image(code)
        file = discord.File(img, filename="captcha.png")
        embed = base_embed(
            f"{e(ICON_VERIFICATION, '🔐')} Verify You're Human",
            "Type the code shown below, then hit **Enter Code**.\n"
            f"-# This code expires in {CAPTCHA_TTL // 60} minutes. Sent because you clicked Verify in "
            f"**{interaction.guild.name}**.",
            color=COLOR_PRIMARY
        )
        embed.set_image(url="attachment://captcha.png")

        # DM-only by design — keeps the captcha off a public/verifiable
        # channel entirely, out of reach of anything scraping messages in
        # the server itself.
        try:
            await interaction.user.send(embed=embed, file=file, view=CaptchaEnterView())
        except discord.Forbidden:
            return await interaction.response.send_message(
                embed=error_embed(
                    "I couldn't DM you the captcha — please enable **Direct Messages from server members** "
                    "in your Privacy Settings for this server, then click **Verify** again."
                ),
                ephemeral=True
            )

        _PENDING_CAPTCHAS[interaction.user.id] = {
            "code": code, "guild_id": interaction.guild.id,
            "expires": time.monotonic() + CAPTCHA_TTL, "attempts": 0
        }
        await interaction.response.send_message(
            embed=success_embed("Check your DMs — I've sent you a captcha to complete verification."),
            ephemeral=True
        )

class TicketControlView(discord.ui.View):
    """Persistent, static view — one custom_id shared by every ticket, safe to use
    across bot restarts via bot.add_view() in on_ready. Holds both Claim and
    Close so staff always have both actions in the same place."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary,
                        emoji="🙋", custom_id="vx_ticket_claim")
    async def claim_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        gc = guild_cfg(cfg, interaction.guild.id)
        uid, tk, panel = _find_active_ticket(gc, interaction.channel.id)
        if not tk:
            return await interaction.response.send_message(embed=error_embed("This channel isn't an active ticket."), ephemeral=True)

        claimed_by = tk.get("claimed_by")
        if claimed_by:
            # Already claimed. Re-lock the button on this message too, in case
            # it's showing stale/clickable state (e.g. a bot restart happened
            # before it got edited) — nobody, including the original claimer,
            # should ever be able to click this again once it's claimed.
            claimer = interaction.guild.get_member(claimed_by)
            btn.disabled = True
            btn.style    = discord.ButtonStyle.secondary
            btn.label    = f"Claimed by {claimer.display_name}" if claimer else "Claimed"
            try:
                await interaction.response.edit_message(view=self)
            except discord.InteractionResponded:
                pass
            return await interaction.followup.send(
                embed=error_embed(f"This ticket is already claimed by {claimer.mention if claimer else 'someone else'}."),
                ephemeral=True
            )

        is_owner_ = interaction.user.id == bot.owner_id
        role_id   = panel.get("support_role")
        has_role  = bool(role_id and interaction.guild.get_role(role_id) in interaction.user.roles)
        can_claim = is_owner_ or interaction.user.guild_permissions.manage_channels or has_role
        if not can_claim:
            return await interaction.response.send_message(embed=error_embed("Only support staff can claim tickets."), ephemeral=True)

        tk["claimed_by"] = interaction.user.id
        save_config(cfg)

        # One claim, permanently — disable + relabel the button right away so
        # it can never be pressed again by anyone, staff or otherwise.
        btn.disabled = True
        btn.style    = discord.ButtonStyle.secondary
        btn.label    = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=success_embed(f"🙋 Ticket claimed by {interaction.user.mention} — they'll be handling this from here."))

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger,
                        emoji=ICON_TICKET_CLOSE if ICON_TICKET_CLOSE else "🔒",
                        custom_id="vx_ticket_close")
    async def close_btn(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        async def _respond(**kw):
            try:
                await interaction.response.send_message(**kw)
            except discord.InteractionResponded:
                await interaction.followup.send(**kw)
        await close_ticket_channel(interaction.guild, interaction.channel, interaction.user, "Closed via button.", _respond)

class TicketOpenView(discord.ui.View):
    """One instance per panel — custom_id stores the panel_id so the button always
    knows which panel to open, even after a bot restart."""
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
            f"React with 🎉 to enter!\n\n"
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
        ended_embed.description = "**Giveaway Ended**\n\nNo entries."
        ended_embed.color = 0x4B5563
        try:
            await msg.edit(embed=ended_embed)
        except Exception:
            pass
        await channel.send(embed=info_embed("Giveaway Ended", f"No winners for **{gw['prize']}**."))
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
                role_note = f"\nRole {win_role.mention} was granted to {assigned} winner(s)."
    win_embed = discord.Embed(
        title=f"{e(ICON_WINNER, '🏆')} Giveaway Winners!".strip(),
        description=f"Congratulations {winner_str}!\n\n**Prize:** {gw['prize']}{role_note}",
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
    now    = discord.utils.utcnow().timestamp()
    to_del = [key for key, t in spam_cleanup_times.items() if now - t > 120]
    for key in to_del:
        spam_tracker.pop(key, None)
        spam_cleanup_times.pop(key, None)
    stale_flood = [key for key, ts in flood_tracker.items() if not ts or now - ts[-1] > 120]
    for key in stale_flood:
        flood_tracker.pop(key, None)
    now_mono = time.monotonic()
    for gid, entries in list(_recent_boost_starts.items()):
        entries[:] = [(uid, ts) for uid, ts in entries if now_mono - ts < 60]
        if not entries:
            _recent_boost_starts.pop(gid, None)

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
    """Prepend a [💎] prefix to the descriptions of slash commands that are
    Premium-locked, then re-sync to Discord so it shows up in the slash-command UI."""
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
            logging.error(f"[{BOT_NAME}] Failed to sync premium descriptions: {e}")

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

    # Re-register persistent views (tickets) so buttons keep working after a restart.
    bot.add_view(TicketControlView())
    panel_ids = {pid for gcfg in cfg.get("guilds", {}).values() for pid in gcfg.get("ticket", {}).get("panels", {}).keys()}
    for pid in panel_ids:
        bot.add_view(TicketOpenView(pid))
    bot.add_view(VerificationView())

    if not cleanup_spam_cache.is_running():
        cleanup_spam_cache.start()
    if not rotate_status.is_running():
        rotate_status.start()
    if not premium_expiry_task.is_running():
        premium_expiry_task.start()
    print(f"[{BOT_NAME}] Online — {len(bot.guilds)} guild(s).")

@bot.event
async def on_command_completion(ctx: commands.Context):
    """Called by discord.py every time a prefix command runs SUCCESSFULLY.
    This is the source of truth for the 'Commands Runned' stat on the profile."""
    uid_str  = str(ctx.author.id)
    cmds_run = cfg.setdefault("commands_run", {})
    cmds_run[uid_str] = cmds_run.get(uid_str, 0) + 1
    save_config(cfg)

@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    """The heart of anti-nuke — called by Discord in real time whenever a new
    audit log entry appears, no polling needed. Requires the 'View Audit Log'
    permission on the bot's role."""
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
    result = await antinuke.punish(guild, member, punishment, f"[Anti-Nuke] Detected: {antinuke.ACTION_LABELS.get(action, action)}")
    antinuke.reset_tracker(guild.id, entry.user.id)

    log_id = ac.get("log_channel")
    log_ch = guild.get_channel(log_id) if log_id else None
    if log_ch:
        emb = discord.Embed(
            title=f"{e(ICON_ANTINUKE, '🛡️')} Anti-Nuke Triggered".strip(),
            description=(
                f"**Culprit:** {member.mention} (`{member.id}`)\n"
                f"**Detected:** {antinuke.ACTION_LABELS.get(action, action)}\n"
                f"**Action:** {result}"
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

    # ── Ignored channel — bot stays fully silent, no processing at all ─────
    gc_ignore = guild_cfg(cfg, message.guild.id)
    if message.channel.id in gc_ignore.get("ignored_channels", []):
        return

    # ── AFK system ───────────────────────────────────────────────────────────
    gc_afk  = guild_cfg(cfg, message.guild.id)
    afk_map = gc_afk.get("afk_users", {})

    # -- Returning from AFK: any message from a currently-AFK member clears
    #    their status, EXCEPT when the message is them re-running the `afk`
    #    command itself (that's setting a new status, not "coming back").
    author_key = str(message.author.id)
    if author_key in afk_map:
        low_afk = message.content.strip().lower()
        is_afk_cmd = (
            low_afk in ("!vx afk", "!v afk") or
            low_afk.startswith(("!vx afk ", "!v afk ")) or
            (user_has_no_prefix(message.guild, message.author) and (low_afk == "afk" or low_afk.startswith("afk ")))
        )
        if not is_afk_cmd:
            entry = afk_map.pop(author_key, None)
            save_config(cfg)
            if entry:
                since_ts = entry.get("since")
                since_txt = f" (AFK since <t:{since_ts}:R>)" if since_ts else ""
                try:
                    await message.channel.send(
                        embed=success_embed(f"Welcome back, {message.author.mention}! Your AFK status has been removed{since_txt}."),
                        delete_after=8
                    )
                except Exception:
                    pass

    # -- Notify the sender if this message @mentions someone who is AFK
    if message.mentions:
        afk_hits = []
        seen_ids = set()
        for m in message.mentions:
            if m.id == message.author.id or m.bot or m.id in seen_ids:
                continue
            entry = afk_map.get(str(m.id))
            if entry:
                afk_hits.append((m, entry))
                seen_ids.add(m.id)
        if afk_hits:
            if len(afk_hits) == 1:
                m, entry = afk_hits[0]
                reason   = entry.get("reason") or "AFK"
                since_ts = entry.get("since")
                duration = f"<t:{since_ts}:R>" if since_ts else "Unknown"
                emb = base_embed(
                    _title_with_icon(ICON_AFK, "💤", "User is AFK"),
                    f"{m.mention} is currently AFK — they won't see this ping until they're back.",
                    color=COLOR_PRIMARY
                )
                emb.set_author(name=m.display_name, icon_url=m.display_avatar.url)
                emb.add_field(name="Reason", value=reason, inline=True)
                emb.add_field(name="Duration", value=duration, inline=True)
                emb.set_thumbnail(url=m.display_avatar.url)
            else:
                emb = base_embed(
                    _title_with_icon(ICON_AFK, "💤", "User is AFK"),
                    "The following mentioned members are currently AFK:",
                    color=COLOR_PRIMARY
                )
                for m, entry in afk_hits[:5]:
                    reason   = entry.get("reason") or "AFK"
                    since_ts = entry.get("since")
                    duration = f"<t:{since_ts}:R>" if since_ts else "Unknown"
                    emb.add_field(name=m.display_name, value=f"**Reason:** {reason}\n**Duration:** {duration}", inline=False)
                if bot.user:
                    emb.set_thumbnail(url=bot.user.display_avatar.url)
            try:
                await message.channel.send(embed=emb, reference=message, mention_author=False)
            except Exception:
                pass

    # ── Honeypot channel check ──────────────────────────────────────────────
    gc_trap  = guild_cfg(cfg, message.guild.id)
    ac_trap  = gc_trap.get("antispam", {})
    trap_ch  = ac_trap.get("trap_channel")
    if trap_ch and message.channel.id == trap_ch:
        if isinstance(message.author, discord.Member) and _antispam_is_ignored(message.author, ac_trap):
            return
        try:
            await message.delete()
        except Exception:
            pass
        result = await _antispam_punish(
            message.guild, message.author, ac_trap.get("punishment", "ban"),
            f"[{BOT_NAME}] Sent message in honeypot channel."
        )
        log_id = ac_trap.get("log_channel") or _fallback_log_channel(gc_trap)
        if log_id:
            log_ch = message.guild.get_channel(log_id)
            if log_ch:
                emb = base_embed("Honeypot Triggered", None, color=COLOR_ERROR)
                emb.add_field(name="User",      value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
                emb.add_field(name="Channel",   value=f"<#{trap_ch}>", inline=True)
                emb.add_field(name="Action",    value=result, inline=True)
                snippet = (message.content or "")[:200]
                if snippet:
                    emb.add_field(name="Content", value=f"```{snippet}```", inline=False)
                try:
                    await log_ch.send(embed=emb)
                except Exception:
                    pass
        return

    # ── XP system ────────────────────────────────────────────────────────
    gc = guild_cfg(cfg, message.guild.id)
    ignore_role_ids = set(gc.get("xp_ignore_roles", []))
    author_role_ids = {r.id for r in message.author.roles} if isinstance(message.author, discord.Member) else set()
    if gc.get("leveling_enabled", True) and not (ignore_role_ids & author_role_ids):
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
            data["level"]  = level_from_xp(data["xp"], gc.get("xp_difficulty", 1.0))
            data["last_msg_ts"] = now
            data["messages"]    = data.get("messages", 0) + 1
            save_config(cfg)
            if data["level"] > old_level:
                granted_roles = await apply_level_roles(message.guild, message.author, gc, data["level"])
                lvl_ch_id = gc.get("level_channel")
                lvl_ch    = message.guild.get_channel(lvl_ch_id) if lvl_ch_id else message.channel
                if lvl_ch:
                    roles_txt = ("🎁 Unlocked: " + " ".join(r.mention for r in granted_roles)) if granted_roles else ""
                    template  = gc.get("levelup_message") or "{mention} just leveled up to **Level {level}**! Keep chatting in {server} to climb even higher. {roles}"
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
                            avatar_bytes, message.author.name, old_level, data["level"], is_prem, role_names
                        )
                        file = discord.File(buf, filename="levelup.png")
                        await lvl_ch.send(content=content, file=file)
                    except Exception as e:
                        logging.error(f"[{BOT_NAME}] Failed to render level-up card: {e}")
                        lvl_emb = discord.Embed(description=content, color=COLOR_ERROR)
                        lvl_emb.set_author(name="Level Up!", icon_url=message.author.display_avatar.url)
                        lvl_emb.set_footer(text=BOT_NAME)
                        try:
                            await lvl_ch.send(embed=lvl_emb)
                        except Exception:
                            pass

    # ── Anti cross-channel spam + flood ─────────────────────────────────────
    ac = gc.get("antispam", {})
    if isinstance(message.author, discord.Member) and not _antispam_is_ignored(message.author, ac):
        uid    = message.author.id
        gid    = message.guild.id
        key    = (gid, uid)
        now_ts = discord.utils.utcnow().timestamp()

        # -- Flood: many rapid-fire messages in the same channel within a short window
        flood_count  = ac.get("flood_count", 5)
        flood_window = ac.get("flood_window", 4)
        fl = flood_tracker[key]
        fl.append(now_ts)
        while fl and now_ts - fl[0] > flood_window:
            fl.pop(0)
        if len(fl) >= flood_count:
            flood_tracker.pop(key, None)
            result = await _antispam_punish(message.guild, message.author, ac.get("punishment", "ban"),
                                             f"[{BOT_NAME}] Message flood detected ({flood_count}+ messages within {flood_window}s).")
            await _antispam_log(message.guild, gc, message.author, "Message Flood",
                                 f"{flood_count}+ messages within {flood_window} seconds in {message.channel.mention}", result)
            return

        # -- Cross-channel: an identical message/link/attachment spammed across many different channels
        fingerprint = _spam_fingerprint(message)
        if fingerprint != "empty":
            threshold = ac.get("threshold", SPAM_THRESHOLD)
            window    = ac.get("window", SPAM_WINDOW)
            spam_cleanup_times[key] = now_ts
            tracker = spam_tracker[key]
            if fingerprint not in tracker:
                tracker[fingerprint] = {"channels": set(), "messages": [], "first_seen": now_ts}
            entry = tracker[fingerprint]
            if now_ts - entry["first_seen"] > window:
                tracker[fingerprint] = {"channels": {message.channel.id}, "messages": [(message.channel.id, message.id)], "first_seen": now_ts}
                entry = tracker[fingerprint]
            else:
                entry["channels"].add(message.channel.id)
                entry["messages"].append((message.channel.id, message.id))
            if len(entry["channels"]) >= threshold:
                del tracker[fingerprint]
                for ch_id, msg_id in entry["messages"]:
                    try:
                        ch  = message.guild.get_channel(ch_id)
                        msg = await ch.fetch_message(msg_id) if ch else None
                        if msg:
                            await msg.delete()
                    except Exception:
                        pass
                result = await _antispam_punish(message.guild, message.author, ac.get("punishment", "ban"),
                                                 f"[{BOT_NAME}] Cross-channel spam detected ({threshold}+ channels within {window}s).")
                await _antispam_log(message.guild, gc, message.author, "Cross-Channel Spam",
                                     f"The same message/link appeared in {len(entry['channels'])} channels within {window} seconds.", result)
                return

    # ── Bot mention auto-reply — only when the message is JUST the mention ──
    stripped = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if bot.user in message.mentions and not stripped:
        return await message.reply(embed=bot_info_embed(message.author.mention, message.guild.id), view=invite_support_view(), mention_author=False)

    # ── Keyword auto-responses ────────────────────────────────────────────
    if gc.get("autoresponses_enabled", True) and gc.get("autoresponses"):
        content_lower = message.content.lower()
        for entry in gc["autoresponses"].values():
            trigger = entry["trigger"] if entry.get("case_sensitive") else entry["trigger"].lower()
            haystack = message.content if entry.get("case_sensitive") else content_lower
            match_type = entry.get("match", "contains")
            hit = (
                (match_type == "contains"   and trigger in haystack) or
                (match_type == "exact"      and haystack == trigger) or
                (match_type == "startswith" and haystack.startswith(trigger))
            )
            if hit:
                try:
                    await message.channel.send(entry["response"], reference=message, mention_author=False)
                except Exception:
                    pass
                break

    # ── Prefix routing + no-prefix ───────────────────────────────────────
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
    """Revoke the USER badge when a user leaves the support server."""
    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if member.guild.id != support_server_id:
        return
    support_members = cfg.get("support_server_members", [])
    if member.id in support_members:
        support_members.remove(member.id)
        save_config(cfg)

_recent_boost_starts: dict = defaultdict(list)  # guild_id -> [(member_id, monotonic_ts), ...]
_last_attributed_booster: dict = {}  # guild_id -> (member_id, monotonic_ts) — see fallback below
LAST_BOOSTER_FALLBACK_WINDOW = 600  # seconds (10 min)

async def handle_new_boost(guild: discord.Guild, member: Optional[discord.Member], boost_number: int):
    """Send a notification for ONE individual boost. Fires once per boost,
    even if the same member contributes multiple boosts to the same server
    (Discord only exposes a per-member 'started boosting' transition once —
    guild.premium_subscription_count is the reliable signal that counts
    every single boost, which is why detection is driven from there)."""
    gc    = guild_cfg(cfg, guild.id)
    bc    = gc.get("boost", {})
    ch_id = bc.get("channel")
    if not ch_id:
        return
    channel = guild.get_channel(ch_id)
    if not channel:
        return

    mention_txt = member.mention if member else "Someone"
    name_txt    = member.display_name if member else "Someone"
    avatar_url  = member.display_avatar.url if member else guild.icon.url if guild.icon else None

    def fill(template: str) -> str:
        return (template
                .replace("{mention}", mention_txt)
                .replace("{user}",    name_txt)
                .replace("{server}",  guild.name)
                .replace("{count}",   str(boost_number))
                .replace("{tier}",    str(guild.premium_tier)))

    title = fill(bc.get("title") or "New Server Boost!")
    emoji_str = bc.get("emoji") or e(ICON_BOOST, "🎉")
    desc  = fill(bc.get("description") or "{mention} just boosted **{server}**! Thanks for the support 💜")

    embed = discord.Embed(
        title=f"{emoji_str} {title}".strip(),
        description=desc,
        color=0xF47FFF,
        timestamp=discord.utils.utcnow()
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"{guild.name} • Boost #{boost_number}")
    try:
        await channel.send(embed=embed)
    except Exception:
        pass

@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    """Authoritative trigger for boost notifications. guild.premium_subscription_count
    increments by exactly 1 for EVERY individual boost — including a repeat
    boost from someone who's already boosting, unlike member.premium_since
    which only transitions once per member. This guarantees one notification
    per boost, professionally handling Discord's API limitation on
    per-member repeat-boost attribution."""
    before_count = before.premium_subscription_count or 0
    after_count  = after.premium_subscription_count or 0
    diff = after_count - before_count
    if diff <= 0:
        return

    # Give a slightly-delayed on_member_update a moment to land so we can
    # attribute the boost to whoever actually triggered it when possible.
    await asyncio.sleep(1.5)

    now = time.monotonic()
    pending = _recent_boost_starts.get(after.id, [])
    pending[:] = [(uid, ts) for uid, ts in pending if now - ts < 15]

    for i in range(diff):
        member = None
        if pending:
            uid, _ts = pending.pop(0)
            member = after.get_member(uid)
        if member is None:
            # Discord only flips premium_since the very first time a member
            # boosts — adding extra boost slots while already boosting (or
            # boosting again later without ever un-boosting) never retriggers
            # it, so there's no fresh on_member_update signal for those. The
            # best available attribution is whoever we last confirmed
            # boosting in this guild recently, since that's overwhelmingly
            # the real explanation (same person contributing another slot),
            # rather than silently falling back to an anonymous "Someone".
            last = _last_attributed_booster.get(after.id)
            if last and (now - last[1]) < LAST_BOOSTER_FALLBACK_WINDOW:
                member = after.get_member(last[0])
        if member is not None:
            _last_attributed_booster[after.id] = (member.id, now)
        await handle_new_boost(after, member, boost_number=before_count + i + 1)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # ── Server boost attribution cache — the actual notification is fired
    # from on_guild_update (see above); this just records WHO started
    # boosting so that event can credit the right member. ──────────────────
    if not before.premium_since and after.premium_since:
        _recent_boost_starts[after.guild.id].append((after.id, time.monotonic()))

    # ── Badge role-sync is computed live (straight from the Discord role every
    # time get_bot_role() is called), so nothing needs updating here. This is
    # just to send a congratulatory DM when someone gains a role that's synced
    # to a badge — so they notice their badge went up. Support server only. ──
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
                    f"You just got a role in **{after.guild.name}** and now automatically have the "
                    f"{badge_tag}**{info['label']}** badge on {BOT_NAME}!\nCheck your profile: `profile`",
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

@bot.command(name="kick", aliases=["k"])
async def pfx_kick(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_kick(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="ban", aliases=["b"])
async def pfx_ban(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_ban(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="unban", aliases=["ub"])
async def pfx_unban(ctx, user_id: str):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.ban_members:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    try:
        uid  = int(user_id.strip("<@!>"))
        await ctx.guild.unban(discord.Object(id=uid), reason=f"By {ctx.author}")
        await ctx.send(embed=success_embed(f"User `{uid}` has been unbanned."))
    except discord.NotFound:
        await ctx.send(embed=error_embed("That user isn't on the ban list."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="timeout", aliases=["to", "mute"])
async def pfx_timeout(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
    await do_timeout(ctx.guild, ctx.author, member, duration, reason, ctx.send)

@bot.command(name="untimeout", aliases=["unmute", "unto"])
async def pfx_untimeout(ctx, member: discord.Member):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.moderate_members:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    try:
        await member.timeout(None, reason=f"By {ctx.author}")
        await ctx.send(embed=success_embed(f"Timeout removed from {member.mention}."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="warn", aliases=["w"])
async def pfx_warn(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    await do_warn(ctx.guild, ctx.author, member, reason, ctx.send)

@bot.command(name="warnings", aliases=["warns"])
async def pfx_warnings(ctx, member: discord.Member = None):
    target = member or ctx.author
    gc     = guild_cfg(cfg, ctx.guild.id)
    warns  = gc.get("warnings", {}).get(str(target.id), [])
    if not warns:
        return await ctx.send(embed=info_embed(f"Warnings — {target.display_name}", "No warnings."))
    lines = [
        f"**{i+1}.** {w.get('reason','?')} *(by <@{w.get('warned_by','?')}> — {w.get('timestamp','')[:10]})*"
        for i, w in enumerate(warns)
    ]
    embed = discord.Embed(title=f"Warnings — {target.display_name}", description="\n".join(lines), color=COLOR_WARNING)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text=f"Total: {len(warns)} warning(s) • {BOT_NAME}")
    await ctx.send(embed=embed)

@bot.command(name="unwarn", aliases=["uw"])
async def pfx_unwarn(ctx, member: discord.Member, number: int):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    gc    = guild_cfg(cfg, ctx.guild.id)
    warns = gc.get("warnings", {}).get(str(member.id), [])
    if not warns:
        return await ctx.send(embed=error_embed(f"{member.display_name} has no warnings."))
    if not 1 <= number <= len(warns):
        return await ctx.send(embed=error_embed(f"Invalid number (1–{len(warns)})."))
    removed = warns.pop(number - 1)
    save_config(cfg)
    await ctx.send(embed=success_embed(f"Warning #{number} `{removed.get('reason','?')}` removed from {member.mention}."))

@bot.command(name="clearwarnings", aliases=["cw", "clearwarns"])
async def pfx_clearwarnings(ctx, member: discord.Member):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    gc = guild_cfg(cfg, ctx.guild.id)
    gc.setdefault("warnings", {})[str(member.id)] = []
    save_config(cfg)
    await ctx.send(embed=success_embed(f"All warnings for {member.mention} have been cleared."))

@bot.command(name="purge", aliases=["clear", "prune"])
async def pfx_purge(ctx, amount: int = 10):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."), delete_after=5)
    amount  = max(1, min(100, amount))
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=success_embed(f"Deleted {max(0, len(deleted)-1)} message(s)."))
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except Exception:
        pass

@bot.command(name="lock", aliases=["lockdown"])
async def pfx_lock(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.send_messages = False
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Locked by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} has been locked."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="unlock", aliases=["unlockdown"])
async def pfx_unlock(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.send_messages = None
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unlocked by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} has been unlocked."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="slowmode", aliases=["sm"])
async def pfx_slowmode(ctx, seconds: int = 0, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    ch = channel or ctx.channel
    seconds = max(0, min(21600, seconds))
    try:
        await ch.edit(slowmode_delay=seconds, reason=f"By {ctx.author}")
        msg = f"Slowmode disabled in {ch.mention}." if seconds == 0 else f"Slowmode in {ch.mention} → **{seconds}s**."
        await ctx.send(embed=success_embed(msg))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="hide", aliases=["hidechannel", "hc"])
async def pfx_hide(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.view_channel = False
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Hidden by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} has been hidden from everyone."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

@bot.command(name="unhide", aliases=["unhidechannel", "uhc", "showchannel"])
async def pfx_unhide(ctx, channel: discord.TextChannel = None):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_channels:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    ch = channel or ctx.channel
    ow = ch.overwrites_for(ctx.guild.default_role)
    ow.view_channel = None
    try:
        await ch.set_permissions(ctx.guild.default_role, overwrite=ow, reason=f"Unhidden by {ctx.author}")
        await ctx.send(embed=success_embed(f"{ch.mention} is visible to everyone again."))
    except discord.Forbidden:
        await ctx.send(embed=error_embed("The bot doesn't have permission."))

# ── ROLE & VOICE ──────────────────────────────────────────────────

@bot.command(name="addrole", aliases=["ar"])
async def pfx_addrole(ctx, member: discord.Member, role: discord.Role):
    await do_addrole(ctx.guild, ctx.author, member, role, ctx.send)

@bot.command(name="removerole", aliases=["rr"])
async def pfx_removerole(ctx, member: discord.Member, role: discord.Role):
    await do_removerole(ctx.guild, ctx.author, member, role, ctx.send)

@bot.command(name="move", aliases=["mv"])
async def pfx_move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    await do_move(ctx.guild, ctx.author, member, channel, ctx.send)

# ── INFO ──────────────────────────────────────────────────────────

@bot.command(name="userinfo", aliases=["ui", "whois"])
async def pfx_userinfo(ctx, member: discord.Member = None):
    await do_userinfo(ctx.guild, member or ctx.author, ctx.send)

@bot.command(name="serverinfo", aliases=["si"])
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

@bot.command(name="avatar", aliases=["av", "pfp"])
async def pfx_avatar(ctx, member: discord.Member = None):
    await do_avatar(member or ctx.author, ctx.send)

@bot.command(name="ping", aliases=["pong", "latency"])
async def pfx_ping(ctx):
    await do_ping(ctx.send)

@bot.command(name="afk", aliases=["away"])
async def pfx_afk(ctx, *, reason: str = ""):
    await do_afk_set(ctx.guild, ctx.author, reason, ctx.send)

@bot.command(name="addemoji", aliases=["ae"])
async def pfx_addemoji(ctx, emoji_or_url: str = "", *, name: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_emojis:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    if not emoji_or_url:
        return await ctx.send(embed=error_embed("Usage: `!vx addemoji <:emoji:id>` or `!vx addemoji <url> <name>`"))
    result = await do_addemoji(ctx.guild, emoji_or_url, name)
    if result["success"]:
        emoji = result["emoji"]
        await ctx.send(embed=success_embed(f"Emoji **{emoji.name}** added! {emoji}"))
    else:
        await ctx.send(embed=error_embed(result["error"]))

# ── PROFILE ───────────────────────────────────────────────────────

@bot.command(name="profile", aliases=["p", "pf"])
async def pfx_profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed  = build_profile_embed(target)
    embed.set_author(name="Profile & Badge Panel", icon_url=target.display_avatar.url)
    # Requested By in the footer with avatar
    embed.set_footer(
        text=BOT_NAME + "  |  Requested By " + ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

# ── RANK & LEADERBOARD ────────────────────────────────────────────

async def _build_leaderboard_entries(guild: discord.Guild, all_d: list) -> list:
    """Fetch each top-10 member's avatar in parallel (not one at a time) so
    generating the leaderboard card doesn't stall waiting on 10 sequential HTTP requests."""
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
    """Return (content_text, view) for the join-support-server + XP boost promo.
    content_text is None if SUPPORT_INVITE isn't set / isn't a valid URL — so we
    don't offer an invite that doesn't exist or make discord.ui.Button error
    out on a broken URL."""
    if not SUPPORT_INVITE or not SUPPORT_INVITE.startswith(("http://", "https://")):
        return None, None
    remaining = xp_boost_remaining(uid)
    if remaining:
        content = f"Your **+10%** XP Boost is still active until {discord.utils.format_dt(remaining, 'R')}!"
    else:
        content = "**Join the support server** and get a **+10% XP Boost** for 60 minutes!"
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Join Support Server", style=discord.ButtonStyle.link, url=SUPPORT_INVITE))
    return content, view

@bot.command(name="rank", aliases=["r"])
async def pfx_rank(ctx, member: discord.Member = None):
    import aiohttp
    target      = member or ctx.author
    gc          = guild_cfg(cfg, ctx.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"], gc.get("xp_difficulty", 1.0))
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
            logging.exception(f"[{BOT_NAME}] Failed to render rank card")
            file = None

        if file:
            kwargs = {"file": file}
            try:
                content, view = _support_boost_promo(ctx.author.id)
                if content: kwargs["content"] = content
                if view:    kwargs["view"] = view
            except Exception:
                logging.exception(f"[{BOT_NAME}] Failed to build boost promo (rank card still sent)")
            return await ctx.send(**kwargs)
    # Fallback text embed if image rendering fails entirely
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
        return await ctx.send(embed=info_embed("Leaderboard", "No XP data yet."))

    async with ctx.typing():
        try:
            entries = await _build_leaderboard_entries(ctx.guild, all_d)
            buf  = await asyncio.to_thread(rank_card.render_leaderboard_card, ctx.guild.name, entries)
            file = discord.File(buf, filename="leaderboard.png")
            return await ctx.send(file=file)
        except Exception as e:
            logging.error(f"[{BOT_NAME}] Failed to render leaderboard card: {e}")

    # Fallback text if image rendering fails entirely
    lines = []
    for idx, (uid, data) in enumerate(all_d):
        m     = ctx.guild.get_member(int(uid))
        name  = m.name if m else f"User ({uid[:6]})"
        medal = ["#1","#2","#3"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"**{medal} {name}** — Level **{data.get('level',0)}** · {data.get('xp',0):,} XP")
    embed = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"{BOT_NAME} · {ctx.guild.name}")
    await ctx.send(embed=embed)

@bot.command(name="level", aliases=["lvl"])
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
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        action = args[0].lower() if args else ""
        if action == "set":
            template = " ".join(args[1:]).strip()
            if not template:
                return await ctx.send(embed=error_embed(
                    "Usage: `level message set <text>`\n\n"
                    "Placeholders: `{mention}` `{user}` `{level}` `{server}` `{roles}`\n"
                    "Example: `level message set {mention} just hit **Level {level}**! 🔥 {roles}`"
                ))
            gc["levelup_message"] = template
            save_config(cfg)
            preview = (template
                       .replace("{mention}", ctx.author.mention)
                       .replace("{user}",    ctx.author.name)
                       .replace("{level}",   "27")
                       .replace("{server}",  ctx.guild.name)
                       .replace("{roles}",   "🎁 Unlocked: @Elite"))
            embed = success_embed(f"Level-up message updated.\n\n**Preview:**\n{preview}")
            return await ctx.send(embed=embed)
        elif action == "reset":
            gc["levelup_message"] = "{mention} just leveled up to **Level {level}**! Keep chatting in {server} to climb even higher. {roles}"
            save_config(cfg)
            return await ctx.send(embed=success_embed("Level-up message reset to default."))
        elif action == "show":
            return await ctx.send(embed=info_embed("Level-Up Message Template", f"```{gc.get('levelup_message','')}```"))
        else:
            return await ctx.send(embed=info_embed("Level-Up Message", (
                "`level message set <text>` — change the level-up notification message\n"
                "`level message show` — view the current template\n"
                "`level message reset` — revert to the default\n\n"
                "Available placeholders: `{mention}` `{user}` `{level}` `{server}` `{roles}`\n"
                "(`{roles}` is automatically empty if no role reward was earned)"
            )))

    elif sub == "toggle":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        current = gc.get("leveling_enabled", True)
        gc["leveling_enabled"] = not current
        save_config(cfg)
        state = "enabled" if gc["leveling_enabled"] else "disabled"
        color = COLOR_SUCCESS if gc["leveling_enabled"] else COLOR_ERROR
        await ctx.send(embed=base_embed("Leveling System",
            "The leveling system is now **" + state + "** in this server.", color=color))

    elif sub == "xp":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        parts = list(args)
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            cur_min, cur_max = gc.get("xp_per_message", [15, 25])
            return await ctx.send(embed=error_embed(
                f"Usage: `level xp <min> <max>`\nCurrent: **{cur_min}-{cur_max} XP** per message"))
        xp_min, xp_max = int(parts[0]), int(parts[1])
        if xp_min < 1 or xp_max < xp_min or xp_max > 1000:
            return await ctx.send(embed=error_embed("Values must be positive, min ≤ max, and max ≤ 1000."))
        gc["xp_per_message"] = [xp_min, xp_max]
        save_config(cfg)
        await ctx.send(embed=success_embed(f"XP per message set to **{xp_min}-{xp_max} XP**."))

    elif sub == "cooldown":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if not args or not args[0].isdigit():
            return await ctx.send(embed=error_embed(
                f"Usage: `level cooldown <seconds>`\nCurrent: **{gc.get('xp_cooldown', 60)}s** between XP gains"))
        seconds = int(args[0])
        if not 0 <= seconds <= 3600:
            return await ctx.send(embed=error_embed("Must be between 0 and 3600 seconds."))
        gc["xp_cooldown"] = seconds
        save_config(cfg)
        await ctx.send(embed=success_embed(f"XP cooldown set to **{seconds} seconds** between messages that count."))

    elif sub == "difficulty":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if not args:
            cur = gc.get("xp_difficulty", 1.0)
            return await ctx.send(embed=info_embed("Level Difficulty", (
                f"Current multiplier: **{cur}x**\n\n"
                "`level difficulty <number>` — scales how much XP every level requires.\n"
                "`1.0` = default · `2.0` = twice as slow · `0.5` = twice as fast\n\n"
                f"Example at 1.0x: Level 10 needs {xp_for_level(9, 1.0):,} XP for that step.\n"
                f"At **{cur}x**: Level 10 needs {xp_for_level(9, cur):,} XP for that step."
            )))
        try:
            mult = float(args[0])
        except ValueError:
            return await ctx.send(embed=error_embed("Must be a number, e.g. `1.5`."))
        if not 0.1 <= mult <= 10:
            return await ctx.send(embed=error_embed("Must be between 0.1 and 10."))
        gc["xp_difficulty"] = mult
        for uid, data in gc["members_xp"].items():
            data["level"] = level_from_xp(data["xp"], mult)
        save_config(cfg)
        await ctx.send(embed=success_embed(
            f"Level difficulty set to **{mult}x**. Everyone's level has been recalculated to match "
            f"(their XP totals are untouched — only how much XP each level requires changed)."
        ))

    elif sub == "noxp":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        ignore_roles = gc.setdefault("xp_ignore_roles", [])
        action = args[0].lower() if args else ""
        if action == "add" and ctx.message.role_mentions:
            r = ctx.message.role_mentions[0]
            if r.id not in ignore_roles:
                ignore_roles.append(r.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"Members with {r.mention} will no longer gain XP or level up."))
        elif action == "remove" and ctx.message.role_mentions:
            r = ctx.message.role_mentions[0]
            if r.id in ignore_roles:
                ignore_roles.remove(r.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"{r.mention} can gain XP again."))
        elif action == "list":
            lines = []
            for rid in ignore_roles:
                role = ctx.guild.get_role(rid)
                lines.append(role.mention if role else f"`{rid}` (role no longer exists)")
            await ctx.send(embed=info_embed("No-XP Roles", "\n".join(lines) or "*(none — everyone gains XP normally)*"))
        else:
            await ctx.send(embed=info_embed("No-XP Roles", (
                "`level noxp add @role` — members with this role never gain XP or level up\n"
                "`level noxp remove @role` — let them gain XP again\n"
                "`level noxp list` — view all no-XP roles\n\n"
                "Useful for muted/timeout roles, bot-adjacent roles, or a dedicated \"NOXP\" role for people who opt out."
            )))

    elif sub == "setchannel":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if not args:
            gc["level_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Level channel disabled. Notifications will be sent to the active channel."))
        ch = None
        if ctx.message.channel_mentions:
            ch = ctx.message.channel_mentions[0]
        elif args[0].isdigit():
            ch = ctx.guild.get_channel(int(args[0]))
        if not ch:
            return await ctx.send(embed=error_embed("Channel not found. Use a #mention or channel ID."))
        gc["level_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed("Level-up notifications will be sent to " + ch.mention + "."))

    elif sub == "role":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
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
                return await ctx.send(embed=error_embed("Role not found."))
            level_roles[str(lvl)] = role.id
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Members who reach **Level {lvl}** will now automatically get the {role.mention} role."))

        elif action == "remove":
            if len(args) < 2 or not args[1].isdigit():
                return await ctx.send(embed=error_embed("Usage: `level role remove <level>`"))
            lvl = args[1]
            if lvl not in level_roles:
                return await ctx.send(embed=error_embed(f"There's no role reward set for level {lvl}."))
            level_roles.pop(lvl, None)
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Role reward for level {lvl} removed. Roles members already have won't be revoked."))

        elif action == "list":
            if not level_roles:
                return await ctx.send(embed=info_embed("Level Role Rewards", "No role rewards have been set yet."))
            lines = []
            for lvl in sorted(level_roles, key=lambda x: int(x)):
                role = ctx.guild.get_role(level_roles[lvl])
                lines.append(f"**Level {lvl}** → {role.mention if role else '*(role not found)*'}")
            return await ctx.send(embed=info_embed("Level Role Rewards", "\n".join(lines)))

        else:
            await ctx.send(embed=info_embed("Level Role Rewards", (
                "`level role set <level> <@role>` — auto-grant a role once a member reaches that level\n"
                "`level role remove <level>` — remove that level's reward\n"
                "`level role list` — view all active rewards\n\n"
                "Roles stack — once granted, they won't be revoked even if the reward is later changed/removed."
            )))

    elif sub == "status":
        enabled  = gc.get("leveling_enabled", True)
        lvl_ch   = ctx.guild.get_channel(gc["level_channel"]) if gc.get("level_channel") else None
        xp_range = gc.get("xp_per_message", [15, 25])
        cooldown = gc.get("xp_cooldown", 60)
        difficulty = gc.get("xp_difficulty", 1.0)
        embed = base_embed("Leveling Status", None, COLOR_SUCCESS if enabled else COLOR_ERROR)
        embed.add_field(name="Status",     value="Enabled" if enabled else "Disabled",             inline=True)
        embed.add_field(name="Channel",    value=lvl_ch.mention if lvl_ch else "Current channel",  inline=True)
        embed.add_field(name="XP/Message", value=str(xp_range[0]) + "-" + str(xp_range[1]) + " XP", inline=True)
        embed.add_field(name="Cooldown",   value=str(cooldown) + " seconds",                       inline=True)
        embed.add_field(name="Difficulty", value=f"{difficulty}x",                                 inline=True)
        embed.add_field(name="No-XP Roles", value=str(len(gc.get("xp_ignore_roles", []))) + " role(s)", inline=True)
        await ctx.send(embed=embed)

    else:
        enabled = gc.get("leveling_enabled", True)
        status  = "Enabled" if enabled else "Disabled"
        await ctx.send(embed=info_embed("Level System",
            "Status: **" + status + "**\n\n"
            "`level toggle` - turn leveling on/off\n"
            "`level setchannel #channel` - set the notification channel\n"
            "`level setchannel` - disable the channel override\n"
            "`level xp <min> <max>` - set XP earned per message\n"
            "`level cooldown <seconds>` - set time between XP gains\n"
            "`level difficulty <multiplier>` - scale how much XP each level needs\n"
            "`level noxp add/remove/list @role` - exclude a role from gaining XP entirely\n"
            "`level role set/remove/list` - manage per-level role rewards\n"
            "`level message set/show/reset` - customize the level-up notification\n"
            "`level status` - view current configuration\n"
            "`level rank [@user]` - view rank\n"
            "`level leaderboard` - top 10"))
@bot.command(name="xp", aliases=["exp"])
async def pfx_xp(ctx, sub: str = "", *args):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    sub  = sub.lower()
    gc   = guild_cfg(cfg, ctx.guild.id)
    VALID = ("add","remove","set","setlevel","reset")
    if sub not in VALID:
        return await ctx.send(embed=info_embed("XP", "`xp add/remove/set @user <amount>` · `xp setlevel @user <lvl>` · `xp reset @user`"))
    if not args:
        return await ctx.send(embed=error_embed(f"Usage: `xp {sub} @user [amount]`"))
    try:
        member = ctx.guild.get_member(int(args[0].strip("<@!>")))
        if not member: return await ctx.send(embed=error_embed("Member not found."))
    except ValueError:
        return await ctx.send(embed=error_embed("Please provide a valid mention or ID."))
    data = get_member_xp(gc, str(member.id))
    if sub == "reset":
        gc["members_xp"][str(member.id)] = {"xp":0,"level":0,"last_msg_ts":0.0,"messages":0}
        save_config(cfg)
        return await ctx.send(embed=success_embed(f"XP for {member.mention} has been reset."))
    if len(args) < 2:
        return await ctx.send(embed=error_embed(f"Usage: `xp {sub} @user <amount>`"))
    try:
        amount = int(args[1])
    except ValueError:
        return await ctx.send(embed=error_embed("Amount must be a number."))
    diff = gc.get("xp_difficulty", 1.0)
    if sub == "add":
        data["xp"] = max(0, data["xp"] + amount)
        data["level"] = level_from_xp(data["xp"], diff)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"+{amount} XP to {member.mention} (Total: {data['xp']:,} · Level {data['level']})"))
    elif sub == "remove":
        data["xp"] = max(0, data["xp"] - amount)
        data["level"] = level_from_xp(data["xp"], diff)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"-{amount} XP from {member.mention} (Total: {data['xp']:,} · Level {data['level']})"))
    elif sub == "set":
        data["xp"] = max(0, amount)
        data["level"] = level_from_xp(data["xp"], diff)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"XP {member.mention} → {amount:,} (Level {data['level']})"))
    elif sub == "setlevel":
        if not 0 <= amount <= 999: return await ctx.send(embed=error_embed("Level must be between 0 and 999."))
        total = sum(xp_for_level(lv, diff) for lv in range(amount))
        data["xp"] = total; data["level"] = amount
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Level {member.mention} → **{amount}** ({total:,} XP)"))

# ── TICKET ────────────────────────────────────────────────────────

@bot.command(name="ticket", aliases=["tix"])
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
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        parts = rest.split()
        if len(parts) < 3:
            return await ctx.send(embed=error_embed(
                "Usage: `ticket setup <panel_id> <category_id> <log_id> [role_id] [max]`\n"
                "Example: `ticket setup support 123456 654321 999999 3`"))
        panel_id = parts[0].lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,32}", panel_id):
            return await ctx.send(embed=error_embed("Panel ID can only contain lowercase letters, numbers, `-`, `_` (max 32 characters)."))
        try:
            cat_id  = int(parts[1]); log_id = int(parts[2])
            role_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
            max_t   = int(parts[4]) if len(parts) > 4 else 1
        except ValueError:
            return await ctx.send(embed=error_embed("Category ID / Log ID / Role ID must be numbers."))
        cat    = ctx.guild.get_channel(cat_id)
        log_ch = ctx.guild.get_channel(log_id)
        if not isinstance(cat, discord.CategoryChannel):
            return await ctx.send(embed=error_embed("Category channel not found."))
        if not log_ch:
            return await ctx.send(embed=error_embed("Log channel not found."))
        panel = panels.setdefault(panel_id, {
            "title": "Support Tickets", "description": "Click the button below to open a support ticket.",
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
        embed.set_footer(text=f"Next: ticket panel {panel_id} <title> | <description>")
        await ctx.send(embed=embed)

    elif sub == "panel":
        if not is_manager():
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        parts = rest.split(maxsplit=1)
        if not parts:
            return await ctx.send(embed=error_embed("Usage: `ticket panel <panel_id> <title> | <description>`"))
        panel_id = parts[0].lower()
        panel    = panels.get(panel_id)
        if not panel or not panel.get("category"):
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` hasn't been set up yet. Run `ticket setup` first."))
        title, desc = parse_title_desc(parts[1] if len(parts) > 1 else "", panel["title"], panel["description"])
        panel["title"], panel["description"] = title, desc
        msg = await ctx.send(embed=base_embed(title, desc, color=COLOR_PRIMARY), view=TicketOpenView(panel_id))
        panel["message_id"], panel["channel_id"] = msg.id, msg.channel.id
        save_config(cfg)

    elif sub == "edit":
        if not is_manager():
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            return await ctx.send(embed=error_embed("Usage: `ticket edit <panel_id> <title> | <description>`"))
        panel_id = parts[0].lower()
        panel    = panels.get(panel_id)
        if not panel:
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` not found."))
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
        note = "The panel message was updated too." if edited else "Config saved, but the old panel message wasn't found/was deleted — resend it with `ticket panel`."
        await ctx.send(embed=success_embed(f"Panel `{panel_id}` updated.\n{note}"))

    elif sub == "welcome":
        if not is_manager():
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            panel_id = parts[0].lower() if parts else ""
            panel    = panels.get(panel_id)
            current  = panel.get("welcome_message") if panel else None
            return await ctx.send(embed=info_embed("Ticket Welcome Message", (
                "Usage: `ticket welcome <panel_id> <message>`\n\n"
                "This is shown INSIDE the ticket channel once it's opened — separate from the panel's "
                "public description, so you're not stuck repeating the same text twice.\n"
                "Placeholders: `{user}` `{server}` `{panel}`\n\n"
                + (f"Current for `{panel_id}`:\n```{current}```" if current else "")
            )))
        panel_id = parts[0].lower()
        panel    = panels.get(panel_id)
        if not panel:
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` not found."))
        panel["welcome_message"] = parts[1].strip()
        save_config(cfg)
        preview = (parts[1]
                   .replace("{user}", ctx.author.mention)
                   .replace("{server}", ctx.guild.name)
                   .replace("{panel}", panel.get("title") or panel_id))
        await ctx.send(embed=success_embed(f"Welcome message for `{panel_id}` updated.\n\n**Preview:**\n{preview}"))

    elif sub == "list":
        if not panels:
            return await ctx.send(embed=info_embed("Ticket Panels", "No panels have been set up yet."))
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
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        panel_id = rest.strip().lower()
        if panel_id not in panels:
            return await ctx.send(embed=error_embed(f"Panel `{panel_id}` not found."))
        del panels[panel_id]
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Panel `{panel_id}` deleted. Tickets still open from this panel won't be closed automatically."))

    elif sub == "close":
        async def _respond(**kw):
            await ctx.send(**kw)
        await close_ticket_channel(ctx.guild, ctx.channel, ctx.author, rest.strip(), _respond)

    else:
        await ctx.send(embed=info_embed("Ticket", (
            "`ticket setup <panel_id> <cat_id> <log_id> [role_id] [max]`\n"
            "`ticket panel <panel_id> <title> | <description>`\n"
            "`ticket edit <panel_id> <title> | <description>`\n"
            "`ticket welcome <panel_id> <message>` — customize the message shown INSIDE the ticket (separate from the panel's public description)\n"
            "`ticket list`\n"
            "`ticket delete <panel_id>`\n"
            "`ticket close [reason]`\n\n"
            "Each panel has its own category, log channel, and support role — "
            "so every ticket type can have its logs kept separate.\n"
            "Every ticket has **Claim** and **Close** buttons, so staff can mark who's handling it."
        )))

# ── GIVEAWAY ─────────────────────────────────────────────────────

@bot.command(name="giveaway", aliases=["gw"])
async def pfx_giveaway(ctx, sub: str = "", *args):
    sub = sub.lower()
    if sub == "list":
        gws = [gw for gw in active_giveaways.values() if gw.get("guild_id") == ctx.guild.id]
        if not gws: return await ctx.send(embed=info_embed("Giveaways", "No active giveaways."))
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
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if not args: return await ctx.send(embed=error_embed("Usage: `giveaway end <message_id>`"))
        try: mid = int(args[0])
        except ValueError: return await ctx.send(embed=error_embed("ID must be a number."))
        gw = active_giveaways.get(mid)
        if not gw or gw["guild_id"] != ctx.guild.id: return await ctx.send(embed=error_embed("Giveaway not found."))
        await ctx.send(embed=info_embed("", f"Ending **{gw['prize']}**..."))
        await end_giveaway(gw)
    elif sub == "reroll":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if not args: return await ctx.send(embed=error_embed("Usage: `giveaway reroll <message_id> [count]`"))
        try: mid = int(args[0]); count = int(args[1]) if len(args) > 1 else 1
        except ValueError: return await ctx.send(embed=error_embed("ID and count must be numbers."))
        try: msg = await ctx.channel.fetch_message(mid)
        except discord.NotFound: return await ctx.send(embed=error_embed("Message not found."))
        entries = []
        target_emoji = ICON_GIVEAWAY_REACT if ICON_GIVEAWAY_REACT else "🎉"
        for reaction in msg.reactions:
            if str(reaction.emoji) == target_emoji or str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot: entries.append(user.id)
                break
        if not entries: return await ctx.send(embed=error_embed("No entries."))
        count   = max(1, min(count, len(entries)))
        winners = random.sample(list(set(entries)), count)
        ws      = " ".join(f"<@{w}>" for w in winners)
        embed   = discord.Embed(title=f"{e(ICON_WINNER, '🏆')} Giveaway Rerolled!".strip(), description=f"New winner(s): {ws}", color=COLOR_SUCCESS, timestamp=discord.utils.utcnow())
        embed.set_footer(text=BOT_NAME)
        await ctx.send(content=ws, embed=embed)
    elif sub == "start":
        if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(embed=error_embed("You don't have permission to use this command."))
        if len(args) < 3:
            return await ctx.send(embed=error_embed("Usage: `giveaway start <duration> <winners> <prize>`\nOptional: `--role <id>` `--winrole <id>`"))
        dur_str = args[0].lower()
        m_dur   = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", dur_str)
        if not m_dur or not any(m_dur.group(x) for x in (1,2,3)):
            return await ctx.send(embed=error_embed("Duration format: `1h`, `30m`, `2h30m`, `1d`"))
        dur_secs = int(m_dur.group(1) or 0)*86400 + int(m_dur.group(2) or 0)*3600 + int(m_dur.group(3) or 0)*60
        if not dur_secs or dur_secs > 7*86400:
            return await ctx.send(embed=error_embed("Duration must be between 1 minute and 7 days."))
        try:
            winner_count = int(args[1])
            if not 1 <= winner_count <= 20: raise ValueError
        except ValueError:
            return await ctx.send(embed=error_embed("Winners must be between 1 and 20."))
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
        if not prize: return await ctx.send(embed=error_embed("Prize name can't be empty."))
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
            return await ctx.send(embed=error_embed("The bot can't send messages in this channel."))
        gw["message_id"] = msg.id
        active_giveaways[msg.id] = gw
        async def _timer():
            await asyncio.sleep(dur_secs)
            if msg.id in active_giveaways: await end_giveaway(active_giveaways[msg.id])
        asyncio.create_task(_timer())
        ends_dt = datetime.datetime.utcfromtimestamp(ends_ts).replace(tzinfo=datetime.timezone.utc)
        confirm = success_embed(f"Giveaway started!\n\nPrize: {prize}\nWinners: {winner_count}\nEnds: {discord.utils.format_dt(ends_dt,'R')}")
        if req_role: confirm.add_field(name="Required Role", value=req_role.mention, inline=True)
        if win_role: confirm.add_field(name="Winner Role",   value=win_role.mention, inline=True)
        await ctx.send(embed=confirm)
    else:
        await ctx.send(embed=info_embed("Giveaway",
            "`giveaway start <duration> <winners> <prize>`\n"
            "  Optional: `--role <id>` `--winrole <id>`\n"
            "`giveaway end <msg_id>` · `giveaway reroll <msg_id>` · `giveaway list`"))

# ── ANTISPAM HONEYPOT ─────────────────────────────────────────────

@bot.command(name="autoresponse", aliases=["arp", "autoreply"])
async def pfx_autoresponse(ctx, action: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    gc      = guild_cfg(cfg, ctx.guild.id)
    entries = gc.setdefault("autoresponses", {})
    action  = action.lower()

    if action == "add":
        parts = rest.split(maxsplit=1)
        if len(parts) < 2 or "|" not in parts[1]:
            return await ctx.send(embed=error_embed(
                "Usage: `autoresponse add <trigger> | <response>`\n"
                "Example: `autoresponse add discord.gg/ | Please don't post invite links here.`"
            ))
        trigger_raw = parts[0]
        response    = parts[1].split("|", 1)[1].strip()
        if not response:
            return await ctx.send(embed=error_embed("The response text can't be empty."))
        key = trigger_raw.lower()
        entries[key] = {"trigger": trigger_raw, "response": response, "match": "contains", "case_sensitive": False}
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Auto-response added for trigger `{trigger_raw}`."))

    elif action == "remove":
        key = rest.strip().lower()
        if key not in entries:
            return await ctx.send(embed=error_embed(f"No auto-response found for trigger `{rest.strip()}`. Check `autoresponse list` for exact triggers."))
        del entries[key]
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Auto-response for `{rest.strip()}` removed."))

    elif action == "match":
        parts = rest.split()
        if len(parts) != 2 or parts[1].lower() not in ("contains", "exact", "startswith"):
            return await ctx.send(embed=error_embed("Usage: `autoresponse match <trigger> <contains/exact/startswith>`"))
        key = parts[0].lower()
        if key not in entries:
            return await ctx.send(embed=error_embed(f"No auto-response found for trigger `{parts[0]}`."))
        entries[key]["match"] = parts[1].lower()
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Match type for `{parts[0]}` set to **{parts[1].lower()}**."))

    elif action == "list":
        if not entries:
            return await ctx.send(embed=info_embed("Auto-Responses", "No auto-responses configured yet."))
        lines = [f"**`{v['trigger']}`** ({v.get('match','contains')}) → {v['response'][:80]}" for v in entries.values()]
        await ctx.send(embed=info_embed(f"Auto-Responses ({len(entries)})", "\n".join(lines)))

    elif action == "toggle":
        gc["autoresponses_enabled"] = not gc.get("autoresponses_enabled", True)
        save_config(cfg)
        state = "enabled" if gc["autoresponses_enabled"] else "disabled"
        await ctx.send(embed=success_embed(f"Auto-responses are now **{state}** in this server."))

    else:
        await ctx.send(embed=info_embed("Auto-Response", (
            "`autoresponse add <trigger> | <response>` — reply automatically when a message contains the trigger\n"
            "`autoresponse remove <trigger>` — delete one\n"
            "`autoresponse match <trigger> <contains/exact/startswith>` — change how it matches (default: contains)\n"
            "`autoresponse list` — view all configured triggers\n"
            "`autoresponse toggle` — turn the whole system on/off\n\n"
            "Matching is case-insensitive by default and checks every message (not just commands)."
        )))

@bot.command(name="ignorechannel", aliases=["ignorech", "ic"])
async def pfx_ignorechannel(ctx, action: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    gc     = guild_cfg(cfg, ctx.guild.id)
    ignored = gc.setdefault("ignored_channels", [])
    action  = action.lower()

    def resolve_channel():
        if ctx.message.channel_mentions:
            return ctx.message.channel_mentions[0]
        target = rest.strip()
        if target.isdigit():
            return ctx.guild.get_channel(int(target))
        return ctx.channel if not target else None

    if action == "add":
        ch = resolve_channel()
        if not ch: return await ctx.send(embed=error_embed("Channel not found. Mention the channel or give its ID."))
        if ch.id not in ignored:
            ignored.append(ch.id)
            save_config(cfg)
        warn = ""
        if ch.id == ctx.channel.id:
            warn = f"\n\n⚠️ This is the channel you're using right now — no command will be responded to here anymore starting now, **including** `ignorechannel remove`. To re-enable it, run the command from another channel: `ignorechannel remove #{ch.name}`."
        await ctx.send(embed=success_embed(f"The bot is now completely silent in {ch.mention} — no commands, no XP, no responses at all.{warn}"))

    elif action == "remove":
        ch = resolve_channel()
        if not ch: return await ctx.send(embed=error_embed("Channel not found. Mention the channel or give its ID."))
        if ch.id in ignored:
            ignored.remove(ch.id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"The bot is active again in {ch.mention}."))
        else:
            await ctx.send(embed=error_embed(f"{ch.mention} isn't being ignored anyway."))

    elif action == "list":
        lines = []
        for cid in ignored:
            ch = ctx.guild.get_channel(cid)
            lines.append(ch.mention if ch else f"`{cid}` (channel no longer exists)")
        await ctx.send(embed=info_embed("Ignored Channels", "\n".join(lines) or "*(empty — the bot is active in every channel)*"))

    else:
        await ctx.send(embed=info_embed("Ignore Channel", (
            "`ignorechannel add [#channel]` — makes the bot fully silent in this channel (defaults to the current channel)\n"
            "`ignorechannel remove [#channel]` — re-enables it\n"
            "`ignorechannel list` — lists every ignored channel\n\n"
            "Different from `antispam ignore` — that skips PEOPLE from spam detection, "
            "this makes the bot not respond at all in a specific CHANNEL."
        )))

@bot.command(name="antispam", aliases=["as"])
async def pfx_antispam(ctx, sub: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    gc  = guild_cfg(cfg, ctx.guild.id)
    ac  = gc.setdefault("antispam", {})
    sub = sub.lower()

    if sub == "setchannel":
        if not rest.strip():
            ac["trap_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Honeypot channel disabled."))
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else (ctx.guild.get_channel(int(rest.strip())) if rest.strip().isdigit() else None)
        if not ch: return await ctx.send(embed=error_embed("Channel not found."))
        ac["trap_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=base_embed("Honeypot Active", ch.mention + " — anyone who sends a message here gets punished immediately.", color=COLOR_ERROR))

    elif sub == "logchannel":
        if not rest.strip():
            ac["log_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Antispam log channel cleared."))
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else (ctx.guild.get_channel(int(rest.strip())) if rest.strip().isdigit() else None)
        if not ch: return await ctx.send(embed=error_embed("Channel not found."))
        ac["log_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Antispam reports (honeypot, cross-channel spam, flood) will be sent to {ch.mention}."))

    elif sub == "punishment":
        choice = rest.strip().lower()
        if choice not in ("ban", "kick", "timeout"):
            return await ctx.send(embed=error_embed("Choices: `ban`, `kick`, or `timeout`."))
        ac["punishment"] = choice
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Antispam punishment set to **{choice}**."))

    elif sub == "threshold":
        parts = rest.split()
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            return await ctx.send(embed=error_embed(
                f"Usage: `antispam threshold <channel_count> <seconds>`\nCurrent: **{ac.get('threshold', SPAM_THRESHOLD)} channels / {ac.get('window', SPAM_WINDOW)}s**"))
        ac["threshold"], ac["window"] = int(parts[0]), int(parts[1])
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Cross-channel spam will now trigger when the same message/link appears in **{ac['threshold']} channels** within **{ac['window']} seconds**."))

    elif sub == "flood":
        parts = rest.split()
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            return await ctx.send(embed=error_embed(
                f"Usage: `antispam flood <message_count> <seconds>`\nCurrent: **{ac.get('flood_count', 5)} messages / {ac.get('flood_window', 4)}s**"))
        ac["flood_count"], ac["flood_window"] = int(parts[0]), int(parts[1])
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Flood detection will now trigger on **{ac['flood_count']} messages** within **{ac['flood_window']} seconds** in the same channel."))

    elif sub == "ignore":
        parts  = rest.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        target_str = parts[1] if len(parts) > 1 else ""
        users = ac.setdefault("ignore_users", [])
        roles = ac.setdefault("ignore_roles", [])
        if action == "add":
            if ctx.message.mentions:
                u = ctx.message.mentions[0]
                if u.id not in users: users.append(u.id)
                save_config(cfg)
                return await ctx.send(embed=success_embed(f"{u.mention} is now skipped from all antispam detection."))
            if ctx.message.role_mentions:
                r = ctx.message.role_mentions[0]
                if r.id not in roles: roles.append(r.id)
                save_config(cfg)
                return await ctx.send(embed=success_embed(f"Role {r.mention} is now skipped from all antispam detection."))
            return await ctx.send(embed=error_embed("Mention the user or role you want to ignore."))
        elif action == "remove":
            if ctx.message.mentions:
                u = ctx.message.mentions[0]
                if u.id in users: users.remove(u.id)
                save_config(cfg)
                return await ctx.send(embed=success_embed(f"{u.mention} removed from the ignore list."))
            if ctx.message.role_mentions:
                r = ctx.message.role_mentions[0]
                if r.id in roles: roles.remove(r.id)
                save_config(cfg)
                return await ctx.send(embed=success_embed(f"Role {r.mention} removed from the ignore list."))
            return await ctx.send(embed=error_embed("Mention the user or role you want to remove from the ignore list."))
        elif action == "list":
            u_lines = [f"<@{uid}>" for uid in users] or ["*(empty)*"]
            r_lines = [f"<@&{rid}>" for rid in roles] or ["*(empty)*"]
            embed = base_embed("Antispam Ignore List", None)
            embed.add_field(name="Users", value="\n".join(u_lines), inline=False)
            embed.add_field(name="Roles", value="\n".join(r_lines), inline=False)
            embed.set_footer(text="The bot owner and anyone with Manage Server are always skipped too.")
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=info_embed("Antispam Ignore", "`antispam ignore add @user/@role`\n`antispam ignore remove @user/@role`\n`antispam ignore list`"))

    elif sub == "status":
        trap_ch = ctx.guild.get_channel(ac.get("trap_channel")) if ac.get("trap_channel") else None
        log_ch  = ctx.guild.get_channel(ac.get("log_channel"))  if ac.get("log_channel")  else None
        embed = base_embed("Antispam Status", None, color=COLOR_ERROR if trap_ch else COLOR_INFO)
        embed.add_field(name="Honeypot Channel", value=trap_ch.mention if trap_ch else "*(inactive)*", inline=True)
        embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "*(not set)*", inline=True)
        embed.add_field(name="Punishment", value=f"`{ac.get('punishment', 'ban')}`", inline=True)
        embed.add_field(name="Cross-Channel Threshold", value=f"{ac.get('threshold', SPAM_THRESHOLD)} channels / {ac.get('window', SPAM_WINDOW)}s", inline=True)
        embed.add_field(name="Flood Threshold", value=f"{ac.get('flood_count', 5)} messages / {ac.get('flood_window', 4)}s", inline=True)
        embed.add_field(name="Ignore List", value=f"{len(ac.get('ignore_users', []))} user, {len(ac.get('ignore_roles', []))} role", inline=True)
        await ctx.send(embed=embed)

    else:
        await ctx.send(embed=info_embed("Antispam", (
            "`antispam setchannel #channel` — honeypot trap (omit the argument to disable)\n"
            "`antispam logchannel #channel` — where reports get sent\n"
            "`antispam punishment ban/kick/timeout` — action taken against offenders\n"
            "`antispam threshold <channels> <seconds>` — cross-channel spam sensitivity\n"
            "`antispam flood <messages> <seconds>` — message flood sensitivity\n"
            "`antispam ignore add/remove/list @user/@role` — skip from detection\n"
            "`antispam status` — view the current configuration"
        )))

# ── ANTI-NUKE ────────────────────────────────────────────────────

@bot.command(name="automod", aliases=["am"])
async def pfx_automod(ctx, sub: str = "", *, rest: str = ""):
    """Bikin AutoMod Rule Discord asli lewat API (bukan deteksi manual bot).
    Sekali bot ini berhasil bikin 1 rule di server manapun, Discord otomatis
    kasih badge 'Uses AutoMod' di profile bot — permanen, gak perlu diulang."""
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("You don't have permission to use this command."))
    if not ctx.guild.me.guild_permissions.manage_guild:
        return await ctx.send(embed=error_embed("The bot needs the **Manage Server** permission to create AutoMod rules."))
    sub = sub.lower()

    if sub == "setup":
        try:
            existing = await ctx.guild.fetch_automod_rules()
        except Exception:
            existing = []
        if any(r.creator_id == bot.user.id for r in existing):
            return await ctx.send(embed=error_embed("This server already has an AutoMod rule created by this bot. Use `automod list` to see it."))

        actions = [discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)]
        try:
            rule = await ctx.guild.create_automod_rule(
                name=f"{BOT_NAME} — Blocked Content",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger=discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.keyword, presets=discord.AutoModPresets(profanity=True, sexual_content=True, slurs=True)),
                actions=actions,
                enabled=True,
                reason=f"[{BOT_NAME}] AutoMod setup"
            )
        except discord.Forbidden:
            return await ctx.send(embed=error_embed("The bot doesn't have permission to create AutoMod rules in this server."))
        except Exception as e:
            logging.exception(f"[{BOT_NAME}] Failed to create AutoMod rule")
            return await ctx.send(embed=error_embed(f"Failed to create the rule: {e}"))

        await ctx.send(embed=success_embed(
            f"AutoMod rule **{rule.name}** created and enabled — blocks profanity, sexual content, and slurs automatically.\n\n"
            "This uses Discord's native AutoMod (not the bot's own spam detection), so it also unlocks the "
            "**\"Uses AutoMod\"** badge on this bot's profile."
        ))

    elif sub == "list":
        try:
            rules = await ctx.guild.fetch_automod_rules()
        except Exception:
            rules = []
        if not rules:
            return await ctx.send(embed=info_embed("AutoMod Rules", "No AutoMod rules exist in this server yet."))
        mine   = [r for r in rules if r.creator_id == bot.user.id]
        others = [r for r in rules if r.creator_id != bot.user.id]
        embed  = base_embed("AutoMod Rules", None)
        if mine:
            embed.add_field(name=f"Created by {BOT_NAME}", value="\n".join(
                f"**{r.name}** — {'enabled' if r.enabled else 'disabled'} (`{r.id}`)" for r in mine
            ), inline=False)
        if others:
            embed.add_field(name="Other rules in this server (not made by this bot)", value="\n".join(
                f"**{r.name}** — {'enabled' if r.enabled else 'disabled'} (`{r.id}`) · creator: <@{r.creator_id}>" for r in others
            ), inline=False)
            embed.set_footer(text="These weren't created by this bot — they're Discord defaults, another bot, or set up manually via Server Settings.")
        await ctx.send(embed=embed)

    elif sub == "remove":
        rule_id = rest.strip()
        if not rule_id.isdigit():
            return await ctx.send(embed=error_embed("Usage: `automod remove <rule_id>` — get the ID from `automod list`."))
        try:
            rules = await ctx.guild.fetch_automod_rules()
            rule = next((r for r in rules if r.id == int(rule_id)), None)
            if not rule:
                return await ctx.send(embed=error_embed("Rule not found."))
            if rule.creator_id != bot.user.id:
                return await ctx.send(embed=error_embed(
                    f"**{rule.name}** wasn't created by this bot (creator: <@{rule.creator_id}>), "
                    "so it won't be removed from here — manage it directly in Server Settings > AutoMod instead."
                ))
            await rule.delete(reason=f"[{BOT_NAME}] Removed via automod remove")
            await ctx.send(embed=success_embed(f"AutoMod rule **{rule.name}** removed."))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed to remove the rule: {e}"))

    else:
        await ctx.send(embed=info_embed("AutoMod", (
            "`automod setup` — create a native Discord AutoMod rule (blocks profanity/sexual content/slurs) "
            "and unlocks the bot's \"Uses AutoMod\" profile badge\n"
            "`automod list` — view every AutoMod rule in this server (including ones not made by this bot)\n"
            "`automod remove <rule_id>` — delete a rule this bot created\n\n"
            "This is different from `antispam`/`antinuke` — those are the bot's own custom detection. "
            "This uses Discord's built-in AutoMod system directly."
        )))

@bot.command(name="antinuke", aliases=["an"])
async def pfx_antinuke(ctx, sub: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.administrator:
        return await ctx.send(embed=error_embed("Only Administrators or the owner can configure anti-nuke."))
    gc  = guild_cfg(cfg, ctx.guild.id)
    ac  = gc.setdefault("antinuke", {"enabled": False, "log_channel": None, "whitelist": [], "punishment": "strip_roles"})
    sub = sub.lower()

    if sub == "enable":
        me = ctx.guild.me
        if not me.guild_permissions.view_audit_log:
            return await ctx.send(embed=error_embed("The bot needs the **View Audit Log** permission before anti-nuke can be enabled."))
        ac["enabled"] = True
        save_config(cfg)
        await ctx.send(embed=success_embed(
            "Anti-Nuke is now **ENABLED**.\nDetects: mass channel delete/create, mass role delete, mass ban/kick, "
            "mass webhook create, and sudden Administrator permission grants.\n\n"
            "Don't forget: `antinuke logchannel #channel` so you get a report when it triggers."
        ))

    elif sub == "disable":
        ac["enabled"] = False
        save_config(cfg)
        await ctx.send(embed=success_embed("Anti-Nuke disabled."))

    elif sub == "logchannel":
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else None
        if not ch:
            ac["log_channel"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Anti-Nuke log channel cleared."))
        ac["log_channel"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Anti-Nuke reports will be sent to {ch.mention}."))

    elif sub == "punishment":
        choice = rest.strip().lower()
        if choice not in ("strip_roles", "kick", "ban"):
            return await ctx.send(embed=error_embed("Choices: `strip_roles`, `kick`, or `ban`."))
        ac["punishment"] = choice
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Anti-Nuke punishment set to **{choice}**."))

    elif sub == "whitelist":
        parts  = rest.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        wl     = ac.setdefault("whitelist", [])
        if action == "add" and ctx.message.mentions:
            u = ctx.message.mentions[0]
            if u.id not in wl:
                wl.append(u.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"{u.mention} is now whitelisted from anti-nuke."))
        elif action == "remove" and ctx.message.mentions:
            u = ctx.message.mentions[0]
            if u.id in wl:
                wl.remove(u.id)
                save_config(cfg)
            await ctx.send(embed=success_embed(f"{u.mention} removed from the whitelist."))
        elif action == "list":
            lines = [f"<@{uid}>" for uid in wl] or ["*(empty)*"]
            await ctx.send(embed=info_embed("Anti-Nuke Whitelist", "\n".join(lines)))
        else:
            await ctx.send(embed=info_embed("Anti-Nuke Whitelist", "`antinuke whitelist add @user`\n`antinuke whitelist remove @user`\n`antinuke whitelist list`"))

    elif sub == "status":
        status = "🟢 Enabled" if ac.get("enabled") else "🔴 Disabled"
        log_ch = ctx.guild.get_channel(ac.get("log_channel")) if ac.get("log_channel") else None
        embed = base_embed("Anti-Nuke Status", None, color=COLOR_ERROR if ac.get("enabled") else COLOR_INFO)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=f"`{ac.get('punishment','strip_roles')}`", inline=True)
        embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "*(not set)*", inline=True)
        embed.add_field(name="Whitelist", value=str(len(ac.get("whitelist", []))) + " user(s)", inline=True)
        embed.add_field(name="Detection", value="\n".join(f"• {v}" for v in antinuke.ACTION_LABELS.values()), inline=False)
        await ctx.send(embed=embed)

    else:
        await ctx.send(embed=info_embed("Anti-Nuke", (
            "`antinuke enable` — turn on protection\n"
            "`antinuke disable` — turn it off\n"
            "`antinuke logchannel #channel` — where reports get sent\n"
            "`antinuke punishment strip_roles/kick/ban` — action taken against offenders\n"
            "`antinuke whitelist add/remove/list @user` — people skipped from detection\n"
            "`antinuke status` — view the current configuration\n\n"
            "The bot owner and server owner are automatically whitelisted — no need to add them manually."
        )))

@bot.command(name="verification", aliases=["verify", "captcha"])
async def pfx_verification(ctx, sub: str = "", *, rest: str = ""):
    if ctx.author.id != bot.owner_id and not ctx.author.guild_permissions.administrator:
        return await ctx.send(embed=error_embed("Only Administrators or the owner can configure verification."))
    gc  = guild_cfg(cfg, ctx.guild.id)
    vc  = gc.setdefault("verification", {
        "enabled": False, "channel_id": None, "unverified_role_id": None,
        "verified_role_id": None, "log_channel_id": None, "message_id": None,
        "panel_message": "Click **Verify** below — I'll DM you a short captcha to unlock the rest of the server. Make sure your DMs are open!",
        "result_message": "Thanks for verifying — enjoy your stay!",
    })
    sub = sub.lower()

    if sub in ("channel", "setchannel"):
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else None
        if not ch:
            return await ctx.send(embed=error_embed("Mention a channel: `verification channel #channel`"))
        vc["channel_id"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Verification channel set to {ch.mention}."))

    elif sub in ("unverifiedrole", "urole", "unverified"):
        role = ctx.message.role_mentions[0] if ctx.message.role_mentions else None
        if not role:
            return await ctx.send(embed=error_embed("Mention a role: `verification unverifiedrole @role`"))
        vc["unverified_role_id"] = role.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Unverified role set to {role.mention}."))

    elif sub in ("verifiedrole", "vrole", "verified"):
        role = ctx.message.role_mentions[0] if ctx.message.role_mentions else None
        if not role:
            return await ctx.send(embed=error_embed("Mention a role: `verification verifiedrole @role`"))
        vc["verified_role_id"] = role.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Verified role set to {role.mention}."))

    elif sub == "logchannel":
        ch = ctx.message.channel_mentions[0] if ctx.message.channel_mentions else None
        if not ch:
            vc["log_channel_id"] = None
            save_config(cfg)
            return await ctx.send(embed=success_embed("Verification log channel cleared."))
        vc["log_channel_id"] = ch.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Verification logs will be sent to {ch.mention}."))

    elif sub == "message":
        text = rest.strip()
        if not text:
            return await ctx.send(embed=error_embed("Give me the text to show: `verification message <your text>`"))
        vc["panel_message"] = text[:1000]
        save_config(cfg)
        await ctx.send(embed=success_embed("Verification panel message updated. Run `verification send` to repost it with the new text."))

    elif sub == "resultmessage":
        text = rest.strip()
        if not text:
            return await ctx.send(embed=error_embed("Give me the text to show: `verification resultmessage <your text>`"))
        vc["result_message"] = text[:500]
        save_config(cfg)
        await ctx.send(embed=success_embed("Verification result message updated — shown on the detail embed members get after every attempt."))

    elif sub == "enable":
        missing = []
        if not vc.get("channel_id"):          missing.append("`verification channel #channel`")
        if not vc.get("unverified_role_id"):  missing.append("`verification unverifiedrole @role`")
        if not vc.get("verified_role_id"):    missing.append("`verification verifiedrole @role`")
        if missing:
            return await ctx.send(embed=error_embed(
                "Can't enable yet — still missing:\n" + "\n".join(missing) +
                "\n\nRun `verification status` any time to check your progress."
            ))
        me = ctx.guild.me
        if not me.guild_permissions.manage_roles:
            return await ctx.send(embed=error_embed("The bot needs the **Manage Roles** permission before verification can be enabled."))
        unver_role = ctx.guild.get_role(vc["unverified_role_id"])
        ver_role   = ctx.guild.get_role(vc["verified_role_id"])
        if not unver_role or not ver_role:
            return await ctx.send(embed=error_embed("One of the configured roles no longer exists — re-set it with `verification unverifiedrole`/`verifiedrole` first."))
        if unver_role >= me.top_role or ver_role >= me.top_role:
            return await ctx.send(embed=error_embed(
                "The bot's highest role needs to be **above** both the Unverified and Verified roles in the "
                "role list, otherwise it can't assign or remove them. Move the bot's role up and try again."
            ))
        vc["enabled"] = True
        save_config(cfg)
        ch = ctx.guild.get_channel(vc["channel_id"])
        await ctx.send(embed=success_embed(
            f"Verification is now **ENABLED**. New members will get {unver_role.mention} on join.\n"
            f"Run `verification send` in {ch.mention if ch else 'the verification channel'} to post the "
            "Verify button, if you haven't already."
        ))

    elif sub == "disable":
        vc["enabled"] = False
        save_config(cfg)
        await ctx.send(embed=success_embed(
            "Verification disabled. New members will no longer receive the Unverified role.\n"
            "-# Members who already have Unverified/Verified roles keep them — this only stops new assignments."
        ))

    elif sub == "send":
        if not vc.get("enabled"):
            return await ctx.send(embed=error_embed("Verification isn't enabled yet — run `verification enable` first."))
        ch = ctx.guild.get_channel(vc.get("channel_id") or 0)
        if not ch:
            return await ctx.send(embed=error_embed("Verification channel isn't set — run `verification channel #channel` first."))
        embed = base_embed(
            f"{e(ICON_VERIFICATION, '🔐')} Verification Required",
            vc.get("panel_message") or "Click **Verify** below — I'll DM you a short captcha to unlock the rest of the server. Make sure your DMs are open!",
            color=COLOR_PRIMARY
        )
        embed.set_footer(text=BOT_NAME)
        try:
            msg = await ch.send(embed=embed, view=VerificationView())
        except discord.Forbidden:
            return await ctx.send(embed=error_embed("The bot doesn't have permission to send messages in that channel."))
        vc["message_id"] = msg.id
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Verification panel posted in {ch.mention}."))

    elif sub == "status":
        status = "🟢 Enabled" if vc.get("enabled") else "🔴 Disabled"
        ch     = ctx.guild.get_channel(vc.get("channel_id") or 0)
        urole  = ctx.guild.get_role(vc.get("unverified_role_id") or 0)
        vrole  = ctx.guild.get_role(vc.get("verified_role_id") or 0)
        lch    = ctx.guild.get_channel(vc.get("log_channel_id") or 0)
        embed = base_embed("Verification Status", None, color=COLOR_SUCCESS if vc.get("enabled") else COLOR_INFO)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Channel", value=ch.mention if ch else "*(not set)*", inline=True)
        embed.add_field(name="Log Channel", value=lch.mention if lch else "*(not set)*", inline=True)
        embed.add_field(name="Unverified Role", value=urole.mention if urole else "*(not set)*", inline=True)
        embed.add_field(name="Verified Role", value=vrole.mention if vrole else "*(not set)*", inline=True)
        panel_msg  = vc.get("panel_message")  or "*(default)*"
        result_msg = vc.get("result_message") or "*(default)*"
        embed.add_field(name="Panel Message", value=panel_msg[:200], inline=False)
        embed.add_field(name="Result Message", value=result_msg[:200], inline=False)
        await ctx.send(embed=embed)

    else:
        await ctx.send(embed=info_embed("Verification Setup", (
            "`verification channel #channel` — where the Verify button gets posted\n"
            "`verification unverifiedrole @role` — role given to members automatically on join\n"
            "`verification verifiedrole @role` — role given once they solve the captcha\n"
            "`verification logchannel #channel` — *(optional)* log every successful verification\n"
            "`verification message <text>` — custom text shown on the verification panel embed\n"
            "`verification resultmessage <text>` — custom text shown on the pass/fail result embed\n"
            "`verification enable` — turn the feature on (needs the 3 items above set first)\n"
            "`verification disable` — turn it off (doesn't touch roles already given out)\n"
            "`verification send` — post/repost the Verify button in the configured channel\n"
            "`verification status` — view the current setup\n\n"
            "-# Nothing activates automatically — new members only start getting the Unverified "
            "role once you've configured everything above and run `enable`."
        )))

# ── OWNER COMMANDS ────────────────────────────────────────────────

@bot.command(name="maintenance", aliases=["mnt"])
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
        desc = f"**{BOT_NAME}** is now in **maintenance mode**.\nAll commands are locked for everyone except the owner."
        if m["reason"]:
            desc += f"\n\n**Reason:** {m['reason']}"
        await ctx.send(embed=warning_embed("Maintenance Mode: ON", desc))
    elif action == "off":
        m["enabled"] = False
        m["reason"]  = ""
        m["since"]   = None
        save_config(cfg)
        await ctx.send(embed=success_embed(f"**{BOT_NAME}** is back to normal. All commands are unlocked."))
    elif action == "status":
        if m.get("enabled"):
            since = m.get("since")
            since_txt = discord.utils.format_dt(datetime.datetime.fromisoformat(since), "R") if since else "?"
            desc = f"Status: **ENABLED** — since {since_txt}"
            if m.get("reason"):
                desc += f"\n**Reason:** {m['reason']}"
        else:
            desc = "Status: **Disabled.** The bot is running normally."
        await ctx.send(embed=info_embed("Maintenance Status", desc))
    else:
        await ctx.send(embed=info_embed("Maintenance",
            "`maintenance on [reason]` — lock all commands except for the owner\n"
            "`maintenance off` — unlock again\n"
            "`maintenance status` — check the current status"))

@bot.command(name="premiumlock", aliases=["plock"])
@is_owner()
async def pfx_premiumlock(ctx, action: str = "", *, cmd_name: str = ""):
    action = action.lower()
    locked = cfg.setdefault("premium_commands", [])
    cmd_name = cmd_name.strip().lower()
    if action == "add":
        if not cmd_name:
            return await ctx.send(embed=error_embed("Specify a command name. Example: `premiumlock add addemoji`"))
        if cmd_name in OWNER_ONLY_CMDS:
            return await ctx.send(embed=error_embed("Owner-only commands can't be Premium-locked."))
        if cmd_name not in locked:
            locked.append(cmd_name)
            save_config(cfg)
        await sync_premium_descriptions()
        await ctx.send(embed=success_embed(f"Command `{cmd_name}` is now **Premium only** (prefix & slash)."))
    elif action == "remove":
        if cmd_name in locked:
            locked.remove(cmd_name)
            save_config(cfg)
            await sync_premium_descriptions()
            await ctx.send(embed=success_embed(f"Command `{cmd_name}` is open to everyone again."))
        else:
            await ctx.send(embed=error_embed(f"Command `{cmd_name}` isn't on the premium lock list."))
    elif action == "list":
        if not locked:
            return await ctx.send(embed=info_embed("Premium Locked Commands", "No commands are Premium-locked yet."))
        await ctx.send(embed=info_embed("Premium Locked Commands", "\n".join(f"`{c}`" for c in locked)))
    else:
        await ctx.send(embed=info_embed("Premium Lock",
            "`premiumlock add <command>` — lock a command to Premium only\n"
            "`premiumlock remove <command>` — unlock a command\n"
            "`premiumlock list` — view every locked command\n\n"
            "Use the command's slash name, e.g. for a subcommand: `ticket setup`."))

@bot.command(name="noprefix", aliases=["np"])
@is_owner_or_staff()
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
            "`noprefix grant @user/guild_id [duration]`\n"
            "`noprefix revoke @user/guild_id`\n"
            "`noprefix list`\n\n"
            "Duration only applies to users (not guilds). Example: `7d`, `24h`, `30m`, "
            "or leave it blank/`permanent` for forever."
        )))

    parts = rest.split(maxsplit=1)
    if not parts:
        return await ctx.send(embed=error_embed("Provide an @user or guild ID."))
    target_tok = parts[0]
    duration   = parts[1].strip().lower() if len(parts) > 1 else ""
    uid_match  = re.match(r"<@!?(\d+)>|(\d{17,20})", target_tok.strip())
    if not uid_match:
        return await ctx.send(embed=error_embed("Invalid target."))
    parsed_id = int(uid_match.group(1) or uid_match.group(2))

    g = bot.get_guild(parsed_id)
    if g:
        if action == "grant":
            if parsed_id not in np_guilds: np_guilds.append(parsed_id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"No-prefix enabled for server **{g.name}**."))
        else:
            if parsed_id in np_guilds: np_guilds.remove(parsed_id)
            save_config(cfg)
            await ctx.send(embed=success_embed(f"No-prefix revoked from server **{g.name}**."))
        return

    try:
        user = await bot.fetch_user(parsed_id)
    except Exception:
        return await ctx.send(embed=error_embed("User/Guild not found."))

    if action == "grant":
        expiry_dt = None
        if duration and duration != "permanent":
            m = re.fullmatch(r"(\d+)(d|h|m)", duration)
            if not m:
                return await ctx.send(embed=error_embed("Duration format: `7d`, `24h`, `30m`, or `permanent`."))
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
                f"You can now use {BOT_NAME} commands without a prefix!\nJust type the command name directly.\nExpires: {dur_display}",
                color=COLOR_SUCCESS
            )
            await user.send(embed=dm)
        except Exception:
            pass
        await ctx.send(embed=success_embed(f"No-prefix enabled for {user.mention}.\nExpires: {dur_display}"))
    else:
        if parsed_id in np_users: np_users.remove(parsed_id)
        np_expiry.pop(str(parsed_id), None)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"No-prefix revoked from {user.mention}."))

@bot.command(name="botrole", aliases=["br"])
@is_owner()
async def pfx_botrole(ctx, action: str = "", *args):
    action    = action.lower()
    bot_roles = cfg.setdefault("bot_roles", {})
    role_sync = cfg.setdefault("role_sync", {})
    mk_users  = cfg.setdefault("moonkeeper_users", [])
    valid_tiers = ("staff", "moderator", "server_manager", "management", "developer")
    settable    = valid_tiers + ("moonkeeper",)  # moonkeeper accepted here, stored separately below

    if action == "list":
        lines = []
        for uid_str, r in bot_roles.items():
            user = bot.get_user(int(uid_str))
            name = user.display_name if user else f"ID {uid_str}"
            lines.append(f"**{name}** → {r.capitalize()}")
        for uid in mk_users:
            user = bot.get_user(uid)
            name = user.display_name if user else f"ID {uid}"
            lines.append(f"**{name}** → Moonkeeper")
        if not lines:
            return await ctx.send(embed=info_embed("Bot Roles (Manual)", "No manual assignments yet."))
        return await ctx.send(embed=info_embed("Bot Roles (Manual)", "\n".join(lines)))

    if action == "sync":
        sub = args[0].lower() if args else ""
        if sub == "list":
            guild = get_support_guild()
            lines = []
            for tier in valid_tiers:
                role_id = role_sync.get(tier)
                if not role_id:
                    lines.append(f"**{tier.capitalize()}** → *(not set)*")
                    continue
                role = guild.get_role(role_id) if guild else None
                lines.append(f"**{tier.capitalize()}** → {role.mention if role else f'`{role_id}` (role not found)'}")
            mk_role_id = cfg.get("moonkeeper_sync_role")
            if mk_role_id:
                mk_role = guild.get_role(mk_role_id) if guild else None
                lines.append(f"**Moonkeeper** → {mk_role.mention if mk_role else f'`{mk_role_id}` (role not found)'}")
            else:
                lines.append("**Moonkeeper** → *(not set)*")
            note = "" if guild else "\n\n⚠️ `SUPPORT_SERVER_ID` isn't set in the environment, so sync won't work."
            return await ctx.send(embed=info_embed("Bot Role Sync", "\n".join(lines) + note))
        if sub == "remove":
            tier = args[1].lower() if len(args) > 1 else ""
            if tier == "moonkeeper":
                cfg.pop("moonkeeper_sync_role", None)
                save_config(cfg)
                return await ctx.send(embed=success_embed("Sync role for **Moonkeeper** removed."))
            if tier not in valid_tiers:
                return await ctx.send(embed=error_embed("Valid tiers: `staff`, `moderator`, `server_manager`, `management`, `developer`, `moonkeeper`."))
            role_sync.pop(tier, None)
            save_config(cfg)
            return await ctx.send(embed=success_embed(f"Sync role for **{tier.capitalize()}** removed."))
        # botrole sync <tier> <role_id/mention>
        if len(args) < 2:
            return await ctx.send(embed=info_embed("Bot Role Sync", (
                "`botrole sync <staff/moderator/server_manager/management/developer/moonkeeper> <role_id or @role>` — link a Discord role in the support server to a badge\n"
                "`botrole sync remove <tier>` — unlink it\n"
                "`botrole sync list` — view the current mapping\n\n"
                "Once set, anyone with that role in the support server automatically gets the badge "
                "on `profile` — no need for manual `botrole set` anymore.\n\n"
                "-# Moonkeeper is independent of the other tiers — it stacks alongside whatever "
                "tier someone already has instead of competing with it."
            )))
        tier = args[0].lower()
        if tier not in settable:
            return await ctx.send(embed=error_embed("Valid tiers: `staff`, `moderator`, `server_manager`, `management`, `developer`, `moonkeeper`."))
        role_match = re.match(r"<@&(\d+)>|(\d{17,20})", args[1].strip())
        if not role_match:
            return await ctx.send(embed=error_embed("Provide a valid role ID or role mention."))
        role_id = int(role_match.group(1) or role_match.group(2))
        guild = get_support_guild()
        if not guild:
            return await ctx.send(embed=error_embed("`SUPPORT_SERVER_ID` isn't set in the bot's environment."))
        disc_role = guild.get_role(role_id)
        if not disc_role:
            return await ctx.send(embed=error_embed("Role not found in the support server."))
        if tier == "moonkeeper":
            cfg["moonkeeper_sync_role"] = role_id
        else:
            role_sync[tier] = role_id
        save_config(cfg)
        info = BOT_ROLE_BADGES[tier]
        badge_tag = (info["emoji"] + " ") if info.get("emoji") else ""
        return await ctx.send(embed=success_embed(
            f"Role {disc_role.mention} now automatically grants the {badge_tag}**{info['label']}** badge.\n"
            f"Any support-server member with this role gets their badge updated instantly."
        ))

    if not args:
        return await ctx.send(embed=info_embed("Bot Role", (
            "`botrole set @user <staff/moderator/server_manager/management/developer/moonkeeper>` — manual assignment (for people outside the support server)\n"
            "`botrole remove @user` — remove a manual assignment\n"
            "`botrole list` — view manual assignments\n"
            "`botrole sync <tier> <role_id>` — auto-sync from a Discord role in the support server"
        )))

    member = None
    for tok in args:
        m = re.match(r"<@!?(\d+)>|(\d{17,20})", tok.strip())
        if m:
            uid = int(m.group(1) or m.group(2))
            member = ctx.guild.get_member(uid)
            break
    if not member:
        return await ctx.send(embed=error_embed("User not found in this server."))
    role = next((a.lower() for a in args if a.lower() in settable), "")

    if action == "set":
        if role not in settable:
            return await ctx.send(embed=error_embed("Valid roles: `staff`, `moderator`, `server_manager`, `management`, `developer`, `moonkeeper`"))
        if role == "moonkeeper":
            if member.id not in mk_users:
                mk_users.append(member.id)
                save_config(cfg)
        else:
            bot_roles[str(member.id)] = role
            save_config(cfg)
        info = BOT_ROLE_BADGES[role]
        badge_tag = (info["emoji"] + " ") if info.get("emoji") else ""
        embed = discord.Embed(title="Bot Role Assigned", description=f"{member.mention} → {badge_tag}**{info['label']}**", color=info["color"], timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            dm = discord.Embed(title="Bot Role Granted!", description=f"You've been given the {badge_tag}**{info['label']}** role on {BOT_NAME}!\nCheck your profile: `profile`", color=info["color"])
            await member.send(embed=dm)
        except Exception: pass
        await ctx.send(embed=embed)
    elif action == "remove":
        removed = []
        if str(member.id) in bot_roles:
            removed.append(bot_roles.pop(str(member.id)).capitalize())
        if member.id in mk_users:
            mk_users.remove(member.id)
            removed.append("Moonkeeper")
        if not removed:
            return await ctx.send(embed=error_embed(f"{member.display_name} doesn't have a manual bot role."))
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Manual bot role(s) **{', '.join(removed)}** removed from {member.mention}."))

@bot.command(name="custombadge", aliases=["cbadge", "cb", "custombadges", "badge", "badges"])
@is_owner()
async def pfx_custombadge(ctx, action: str = "", *args):
    """
    Owner-only. Create fully custom, free-form badges — any name, any emoji
    (including this server's custom emoji) — and give/remove them on any
    specific user, any time. Completely separate from the built-in bot-role
    badges (Founder/Staff/etc.): no hierarchy, no auto-sync, just a manual
    grant that only the owner controls.
    """
    action = action.lower()
    defs   = cfg.setdefault("custom_badges", {})
    grants = cfg.setdefault("user_custom_badges", {})

    if action == "create":
        if len(args) < 2:
            return await ctx.send(embed=error_embed(
                "Usage: `custombadge create <emoji> <name>`\nExample: `custombadge create 🐉 Dragon Tamer`"
            ))
        emoji_tok = args[0]
        name      = _sanitize_badge_name(" ".join(args[1:]))
        if not name:
            return await ctx.send(embed=error_embed("Badge name can't be empty (mentions and channel tags don't count as a name)."))
        if len(name) > 100:
            return await ctx.send(embed=error_embed("Badge name is too long (max 100 characters)."))
        badge_id = _slugify_badge_id(name)
        defs[badge_id] = {"name": name, "emoji": emoji_tok}
        save_config(cfg)
        return await ctx.send(embed=success_embed(
            f"Custom badge created: {emoji_tok} **{name}**\n"
            f"ID: `{badge_id}` — use this ID to give or remove it.\n\n"
            f"`custombadge give @user {badge_id}`"
        ))

    if action == "delete":
        if not args:
            return await ctx.send(embed=error_embed("Usage: `custombadge delete <badge_id>`"))
        badge_id = args[0].lower()
        if badge_id not in defs:
            return await ctx.send(embed=error_embed(f"No custom badge with ID `{badge_id}`. Use `custombadge list` to see all IDs."))
        removed = defs.pop(badge_id)
        holders = 0
        for ids in grants.values():
            if badge_id in ids:
                ids.remove(badge_id)
                holders += 1
        save_config(cfg)
        return await ctx.send(embed=success_embed(
            f"Deleted custom badge {removed.get('emoji','')} **{removed.get('name', badge_id)}** (`{badge_id}`) — "
            f"removed from {holders} member(s) who had it."
        ))

    if action == "list":
        if not defs:
            return await ctx.send(embed=info_embed("Custom Badges", "No custom badges created yet.\nUse `custombadge create <emoji> <name>` to make one."))
        lines = []
        for bid, info in defs.items():
            holder_count = sum(1 for ids in grants.values() if bid in ids)
            lines.append(f"{info.get('emoji','')} **{info.get('name', bid)}** — `{bid}` · {holder_count} holder(s)")
        return await ctx.send(embed=info_embed("Custom Badges", "\n".join(lines)))

    if action in ("give", "grant"):
        if len(args) < 2:
            return await ctx.send(embed=error_embed("Usage: `custombadge give @user <badge_id>`"))
        target_id = _resolve_badge_target(args[0])
        badge_id  = args[1].lower()
        if not target_id:
            return await ctx.send(embed=error_embed("Provide a valid user mention or ID."))
        if badge_id not in defs:
            return await ctx.send(embed=error_embed(f"No custom badge with ID `{badge_id}`. Use `custombadge list` to see all IDs."))
        held = grants.setdefault(str(target_id), [])
        if badge_id in held:
            return await ctx.send(embed=error_embed(f"<@{target_id}> already has that badge."))
        held.append(badge_id)
        save_config(cfg)
        info = defs[badge_id]
        try:
            target_user = await bot.fetch_user(target_id)
            dm = base_embed(
                "Custom Badge Granted!",
                f"You've been given the {info.get('emoji','')} **{info['name']}** badge on {BOT_NAME}!\nCheck your profile: `profile`",
                color=COLOR_SUCCESS
            )
            await target_user.send(embed=dm)
        except Exception:
            pass
        return await ctx.send(embed=success_embed(f"Gave {info.get('emoji','')} **{info['name']}** to <@{target_id}>."))

    if action in ("remove", "revoke", "take"):
        if len(args) < 2:
            return await ctx.send(embed=error_embed("Usage: `custombadge remove @user <badge_id>`"))
        target_id = _resolve_badge_target(args[0])
        badge_id  = args[1].lower()
        if not target_id:
            return await ctx.send(embed=error_embed("Provide a valid user mention or ID."))
        held = grants.get(str(target_id), [])
        if badge_id not in held:
            return await ctx.send(embed=error_embed(f"<@{target_id}> doesn't have that badge."))
        held.remove(badge_id)
        save_config(cfg)
        info = defs.get(badge_id, {})
        return await ctx.send(embed=success_embed(f"Removed {info.get('emoji','')} **{info.get('name', badge_id)}** from <@{target_id}>."))

    if action == "user":
        if not args:
            return await ctx.send(embed=error_embed("Usage: `custombadge user @user`"))
        target_id = _resolve_badge_target(args[0])
        if not target_id:
            return await ctx.send(embed=error_embed("Provide a valid user mention or ID."))
        held = get_custom_badges(target_id)
        if not held:
            return await ctx.send(embed=info_embed("Custom Badges", f"<@{target_id}> has no custom badges."))
        lines = [f"{b.get('emoji','')} **{b['name']}** — `{b['id']}`" for b in held]
        return await ctx.send(embed=info_embed(f"Custom Badges — <@{target_id}>", "\n".join(lines)))

    return await ctx.send(embed=info_embed("Custom Badges", (
        "`custombadge create <emoji> <name>` — create a new custom badge\n"
        "`custombadge give @user <badge_id>` — give a badge to a member\n"
        "`custombadge remove @user <badge_id>` — revoke a badge from a member\n"
        "`custombadge delete <badge_id>` — permanently delete a badge (removes it from everyone who has it)\n"
        "`custombadge list` — view every custom badge, its ID, and how many people hold it\n"
        "`custombadge user @user` — view a member's custom badges\n\n"
        "-# Fully separate from the built-in bot-role badges (Founder, Staff, etc.) — name and "
        "emoji are 100% yours to decide, including this server's custom emoji. Shows up right "
        "alongside the other badges on `profile`."
    )))

@bot.command(name="grantpremium", aliases=["gp"])
@is_owner_or_staff()
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
            await member.send(embed=base_embed("Premium Ended", f"Your {BOT_NAME} Premium has ended. Premium command access and no-prefix have both been revoked.", color=COLOR_ERROR))
        except Exception: pass
        return await ctx.send(embed=success_embed(f"Premium revoked from {member.mention}."))
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
    embed = discord.Embed(title="Premium Granted!", description=f"{member.mention} is now **Premium**!\nExpires: {dur_display}", color=COLOR_WARNING, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    try:
        dm = discord.Embed(
            title="Premium Activated!",
            description=f"Your {BOT_NAME} Premium is active!\nExpires: {dur_display}\n\nEvery premium command is unlocked and **no-prefix is automatically enabled** — just type the command name without `!vx`.",
            color=COLOR_WARNING
        )
        await member.send(embed=dm)
    except Exception: pass
    await ctx.send(embed=embed)

@bot.command(name="blacklist", aliases=["bl"])
@is_owner()
async def pfx_blacklist(ctx, action: str = "", guild_id: str = ""):
    bl = cfg.setdefault("blacklisted_guilds", [])
    if action == "add":
        try: gid = int(guild_id)
        except ValueError: return await ctx.send(embed=error_embed("Guild ID must be a number."))
        if gid not in bl: bl.append(gid)
        save_config(cfg)
        g = bot.get_guild(gid)
        if g:
            try: await g.leave()
            except Exception: pass
        await ctx.send(embed=success_embed(f"Guild `{gid}` has been blacklisted and the bot has left."))
    elif action == "remove":
        try: gid = int(guild_id)
        except ValueError: return await ctx.send(embed=error_embed("Guild ID must be a number."))
        if gid in bl: bl.remove(gid)
        save_config(cfg)
        await ctx.send(embed=success_embed(f"Guild `{gid}` has been removed from the blacklist."))
    elif action == "list":
        if not bl: return await ctx.send(embed=info_embed("Blacklist", "No guilds are blacklisted."))
        lines = []
        for gid in bl:
            g = bot.get_guild(gid)
            lines.append(f"**{g.name}** (`{gid}`)" if g else f"`{gid}`")
        await ctx.send(embed=info_embed("Blacklisted Guilds", "\n".join(lines)))
    else:
        await ctx.send(embed=info_embed("Blacklist", "`blacklist add <guild_id>`\n`blacklist remove <guild_id>`\n`blacklist list`"))

class ServerListView(discord.ui.View):
    """List every server the bot is in, complete with key info
    (member count, owner, when the bot joined) — so the owner knows exactly
    which server they're about to leave before running vxleave."""
    PER_PAGE = 8

    def __init__(self, guilds: list, owner_id: int):
        super().__init__(timeout=120)
        self.guilds   = guilds
        self.owner_id = owner_id
        self.page     = 0

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.guilds) - 1) // self.PER_PAGE + 1)

    def build_embed(self) -> discord.Embed:
        start = self.page * self.PER_PAGE
        chunk = self.guilds[start:start + self.PER_PAGE]
        embed = base_embed(f"Server List — {len(self.guilds)} total", None)
        for g in chunk:
            joined_at = g.me.joined_at if g.me else None
            joined_txt = discord.utils.format_dt(joined_at, "R") if joined_at else "?"
            owner_txt  = f"{g.owner} (`{g.owner_id}`)" if g.owner else f"`{g.owner_id}`"
            embed.add_field(
                name=g.name,
                value=(
                    f"ID: `{g.id}`\n"
                    f"Members: **{g.member_count:,}** · Owner: {owner_txt}\n"
                    f"Bot joined: {joined_txt}"
                ),
                inline=False
            )
        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages} • `vxleave <guild_id>` to leave a server")
        return embed

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(embed=error_embed("Only the owner can navigate this."), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        if not await self._guard(interaction): return
        self.page = max(0, self.page - 1)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        if not await self._guard(interaction): return
        self.page = min(self.total_pages - 1, self.page + 1)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

@bot.command(name="vxservers", aliases=["vxguilds"])
@is_owner()
async def pfx_vxservers(ctx, sort: str = "members"):
    guilds = list(bot.guilds)
    if sort.lower() in ("name", "alpha"):
        guilds.sort(key=lambda g: g.name.lower())
    else:
        guilds.sort(key=lambda g: g.member_count or 0, reverse=True)
    if not guilds:
        return await ctx.send(embed=info_embed("Server List", "The bot hasn't joined any servers yet."))
    view = ServerListView(guilds, bot.owner_id)
    await ctx.send(embed=view.build_embed(), view=view)

@bot.command(name="vxleave", aliases=["leave"])
@is_owner()
async def pfx_vxleave(ctx, guild_id: str = ""):
    if not guild_id:
        guilds = sorted(bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        if not guilds:
            return await ctx.send(embed=info_embed("Leave Guild", "The bot hasn't joined any servers yet."))
        view = ServerListView(guilds, bot.owner_id)
        embed = view.build_embed()
        embed.description = "Pick a server from this list, then run `vxleave <guild_id>`."
        return await ctx.send(embed=embed, view=view)
    try:
        gid = int(guild_id)
    except ValueError:
        return await ctx.send(embed=error_embed("Guild ID must be a number. Check `vxservers` for the list and IDs."))
    g = bot.get_guild(gid)
    if not g:
        return await ctx.send(embed=error_embed("The bot isn't in that guild. Check `vxservers` for the server list."))
    owner_txt = f"{g.owner} (`{g.owner_id}`)" if g.owner else f"`{g.owner_id}`"
    embed = base_embed(f"Leaving {g.name}...", None, color=COLOR_ERROR)
    embed.add_field(name="Guild ID", value=f"`{g.id}`", inline=True)
    embed.add_field(name="Members", value=f"{g.member_count:,}", inline=True)
    embed.add_field(name="Owner", value=owner_txt, inline=True)
    await ctx.send(embed=embed)
    await g.leave()

# ── HELP ─────────────────────────────────────────────────────────

# ── HELP MENU — category dropdown so it doesn't pile up in one embed ──

HELP_CATEGORIES = [
    ("moderation", "Moderation", ICON_MODERATION, "🛠️", (
        "`kick` · `ban` · `unban` · `timeout` · `untimeout`\n"
        "`warn` · `warnings` · `unwarn` · `clearwarnings`\n"
        "`purge` · `lock` · `unlock` · `slowmode` · `hide` · `unhide`"
    )),
    ("role_voice", "Role & Voice", ICON_ROLE, "🎭", "`addrole` · `removerole` · `move`"),
    ("info", "Info", ICON_INFO, "ℹ️", "`userinfo` · `serverinfo` · `avatar` · `ping` · `addemoji` · `profile`"),
    ("afk", "AFK System", ICON_AFK, "💤", (
        "`afk [reason]` (alias `away`) · `/afk` — set yourself as AFK\n"
        "Sending any message automatically clears your AFK status.\n"
        "Anyone who @mentions you while you're AFK gets notified with your reason."
    )),
    ("ticket", "Ticket", ICON_TICKET, "🎫", "`ticket setup` · `ticket panel` · `ticket edit` · `ticket welcome` · `ticket list` · `ticket delete` · `ticket close`\nEach ticket has Claim + Close buttons."),
    ("level", "Level & XP", ICON_LEVEL, "📈", "`rank` · `leaderboard` (alias `lb`) · `level toggle/setchannel/status` · `xp`"),
    ("giveaway", "Giveaway", ICON_GIVEAWAY, "🎉", "`giveaway start/end/reroll/list`\n`--role <id>` · `--winrole <id>`"),
    ("antispam", "Antispam", ICON_ANTISPAM, "🛡️", "`antispam setchannel` · `logchannel` · `punishment` · `threshold` · `flood` · `ignore` · `status`"),
    ("antinuke", "Anti-Nuke", ICON_ANTINUKE, "🛡️", "`antinuke enable/disable` · `antinuke logchannel` · `antinuke punishment` · `antinuke whitelist` · `antinuke status`"),
    ("verification", "Verification", ICON_VERIFICATION, "🔐", "`verification channel/unverifiedrole/verifiedrole/logchannel` · `verification enable/disable` · `verification send` · `verification status`"),
    ("automod", "AutoMod", ICON_AUTOMOD, "🤖", "`automod setup` — creates a native Discord AutoMod rule (blocks profanity/sexual content/slurs)\n`automod list` · `automod remove <rule_id>`"),
    ("ignore", "Ignore Channel", ICON_IGNORE, "🔇", "`ignorechannel add/remove/list [#channel]` — makes the bot completely silent in a specific channel"),
    ("autoresponse", "Auto-Response", ICON_AUTORESPONSE, "💬", "`autoresponse add <trigger> | <response>` · `remove` · `match` · `list` · `toggle`"),
    ("boost", "Server Boost", ICON_BOOST, "🎉", "`/boostconfig` (slash only) — configure the server boost notification channel & appearance"),
]

OWNER_HELP_CATEGORY = ("owner", "Owner Only", ICON_OWNER, "👑", (
    "`maintenance on/off/status`\n"
    "`noprefix grant/revoke/list`\n"
    "`botrole set/remove/list`\n"
    "`custombadge create/give/remove/delete/list` — free-form badges you design and assign\n"
    "`grantpremium @user <duration>/revoke`\n"
    "`premiumlock add/remove/list`\n"
    "`blacklist add/remove/list`\n"
    "`vxservers` — view every server the bot is in\n"
    "`vxleave <guild_id>`"
))

DELEGATED_HELP_CATEGORY = ("delegated_access", "Access Management", "", "🌙", (
    "You're a **Moonkeeper** — you can grant/revoke access on " + BOT_NAME + "'s behalf, "
    "same as if the owner ran it themselves:\n\n"
    "`noprefix grant @user [duration]` / `noprefix revoke @user` / `noprefix list`\n"
    "`grantpremium @user <duration>` / `grantpremium @user revoke`\n\n"
    "-# The owner can remove this access at any time by changing your bot role."
))

class HelpView(discord.ui.View):
    """Help navigation dropdown — every person who runs `help` gets their own
    View instance, so the 'Owner Only' option automatically only shows up in
    the owner's dropdown, with no need for DMs or special ephemeral handling."""
    def __init__(self, invoker_id: int, is_owner_user: bool, has_np: bool):
        super().__init__(timeout=120)
        self.invoker_id = invoker_id
        self.has_np     = has_np
        self.message: Optional[discord.Message] = None
        self.categories = list(HELP_CATEGORIES) + (
            [OWNER_HELP_CATEGORY] if is_owner_user else
            ([DELEGATED_HELP_CATEGORY] if can_manage_access(invoker_id) else [])
        )

        options = [discord.SelectOption(label="Overview", value="_home", emoji="🏠", description="Home page")]
        for key, label, icon_var, fallback, _ in self.categories:
            options.append(discord.SelectOption(label=label, value=key, emoji=e(icon_var, fallback)))
        select = discord.ui.Select(placeholder="Pick a command category...", options=options)
        select.callback = self.on_select
        self.add_item(select)

        for item in invite_support_view().children:
            self.add_item(item)

    def home_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{BOT_NAME} — Command Reference",
            description=(
                f"*{BOT_TAGLINE}*\n\n"
                f"Prefix: **`!vx`** · **`!v`** (alias)\n"
                + ("✨ **No-prefix active** — just type the command directly!\n" if self.has_np else "")
                + "\nPick a category from the dropdown below to see its commands."
            ),
            color=COLOR_PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} • {BOT_TAGLINE}")
        return embed

    def category_embed(self, key: str) -> discord.Embed:
        _, label, icon_var, fallback, value = next(c for c in self.categories if c[0] == key)
        embed = discord.Embed(title=f"{e(icon_var, fallback)} {label}".strip(), description=value, color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} • {BOT_TAGLINE}")
        return embed

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.send_message(embed=error_embed("This menu isn't for you — run `help` yourself."), ephemeral=True)
        value = interaction.data["values"][0]
        embed = self.home_embed() if value == "_home" else self.category_embed(value)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

@bot.command(name="help", aliases=["h"])
async def pfx_help(ctx):
    has_np = user_has_no_prefix(ctx.guild, ctx.author)
    view   = HelpView(ctx.author.id, ctx.author.id == bot.owner_id, has_np)
    view.message = await ctx.send(embed=view.home_embed(), view=view)

@bot.command(name="ownerhelp", aliases=["oh"])
@is_owner()
async def pfx_ownerhelp(ctx):
    """Owner-only reference command — always sent via DM so it can't be read by anyone else in the channel."""
    embed = discord.Embed(
        title=f"{e(ICON_OWNER, '👑')} {BOT_NAME} — Owner Command Reference".strip(),
        description="This list is only ever sent to your DMs — it's never shown in a public channel.",
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Maintenance", value="`maintenance on [reason]` · `maintenance off` · `maintenance status`", inline=False)
    embed.add_field(name="No-Prefix", value="`noprefix grant @user [duration]` · `noprefix revoke @user` · `noprefix list`\nDuration: `7d` / `24h` / `30m` / leave blank for permanent.", inline=False)
    embed.add_field(name="Bot Role", value="`botrole set @user <role>` · `botrole remove @user` · `botrole list`\n`botrole sync <tier> <role_id>` — auto-badge from a Discord role in the support server", inline=False)
    embed.add_field(name="Custom Badges", value="`custombadge create <emoji> <name>` · `give/remove @user <badge_id>` · `list` · `delete <badge_id>` · `user @user`\nFree-form badges — any name, any emoji — fully separate from bot-role badges.", inline=False)
    embed.add_field(name="Premium", value="`grantpremium @user <duration>` · `grantpremium @user revoke`", inline=False)
    embed.add_field(name="Premium Lock", value="`premiumlock add <command>` · `premiumlock remove <command>` · `premiumlock list`", inline=False)
    embed.add_field(name="Blacklist", value="`blacklist add <id>` · `blacklist remove <id>` · `blacklist list`", inline=False)
    embed.add_field(name="Other", value="`vxservers` — view every server the bot is in\n`vxleave <guild_id>`", inline=False)
    embed.set_footer(text=BOT_NAME + " v" + BOT_VERSION + " • Owner Only")

    try:
        await ctx.author.send(embed=embed)
        ack = success_embed("The command reference has been sent to your DMs.")
    except discord.Forbidden:
        ack = error_embed("Couldn't DM you — open your DMs for this server/bot first, then try again.")
    await ctx.send(embed=ack, delete_after=8)

# ══════════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════

@bot.tree.command(name="rank", description="View your rank card or another member's.")
@app_commands.describe(member="The member whose rank you want to view")
async def slash_rank(i: discord.Interaction, member: Optional[discord.Member] = None):
    await i.response.defer()
    target      = member or i.user
    gc          = guild_cfg(cfg, i.guild.id)
    data        = get_member_xp(gc, str(target.id))
    lvl, cx, nx = xp_progress(data["xp"], gc.get("xp_difficulty", 1.0))
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
        logging.exception(f"[{BOT_NAME}] Failed to render rank card")

    if file:
        kwargs = {"file": file}
        try:
            content, view = _support_boost_promo(i.user.id)
            if content: kwargs["content"] = content
            if view:    kwargs["view"] = view
        except Exception:
            logging.exception(f"[{BOT_NAME}] Failed to build boost promo (rank card still sent)")
        return await i.followup.send(**kwargs)

    pct   = int((cx / max(nx,1)) * 100)
    bar   = "▰"*int(pct/100*16) + "▱"*(16-int(pct/100*16))
    embed = discord.Embed(description=f"**@{target.name}**\n\n**Level: {lvl}** | **XP: {cx:,}/{nx:,}** | **Rank: #{rank}**\n\n`{bar}` {pct}%\n\n*Total XP: {data['xp']:,}*", color=COLOR_PRIMARY)
    embed.set_author(name="Rank Card", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)
    await i.followup.send(embed=embed)

@bot.tree.command(name="leaderboard", description="View this server's top 10 XP leaderboard.")
async def slash_leaderboard(i: discord.Interaction):
    gc    = guild_cfg(cfg, i.guild.id)
    all_d = sorted(gc["members_xp"].items(), key=lambda x: x[1].get("xp",0), reverse=True)[:10]
    if not all_d:
        return await i.response.send_message(embed=info_embed("Leaderboard", "No XP data yet."), ephemeral=True)

    await i.response.defer()
    try:
        entries = await _build_leaderboard_entries(i.guild, all_d)
        buf  = await asyncio.to_thread(rank_card.render_leaderboard_card, i.guild.name, entries)
        file = discord.File(buf, filename="leaderboard.png")
        return await i.followup.send(file=file)
    except Exception as e:
        logging.error(f"[{BOT_NAME}] Failed to render leaderboard card: {e}")

    lines = []
    for idx,(uid,data) in enumerate(all_d):
        m     = i.guild.get_member(int(uid))
        name  = m.name if m else f"User ({uid[:6]})"
        medal = ["#1","#2","#3"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"**{medal} {name}** — Level **{data.get('level',0)}** · {data.get('xp',0):,} XP")
    embed = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"{BOT_NAME} · {i.guild.name}")
    await i.followup.send(embed=embed)

@bot.tree.command(name="profile", description="View your profile card and badges, or another member's.")
@app_commands.describe(member="The member whose profile you want to view")
async def slash_profile(i: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or i.user
    embed  = build_profile_embed(target)
    embed.set_author(name="Profile & Badge Panel", icon_url=target.display_avatar.url)
    embed.set_footer(
        text=BOT_NAME + "  |  Requested By " + i.user.display_name,
        icon_url=i.user.display_avatar.url
    )
    await i.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="View detailed info about a member.")
@app_commands.describe(member="The member you want info about")
async def slash_userinfo(i: discord.Interaction, member: Optional[discord.Member] = None):
    await do_userinfo(i.guild, member or i.user, i.response.send_message)

@bot.tree.command(name="avatar", description="View a member's avatar.")
@app_commands.describe(member="The member whose avatar you want to view")
async def slash_avatar(i: discord.Interaction, member: Optional[discord.Member] = None):
    await do_avatar(member or i.user, i.response.send_message)

@bot.tree.command(name="serverinfo", description="View this server's info.")
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

@bot.tree.command(name="boostconfig", description="Configure the server boost notification.")
@app_commands.describe(
    channel="The channel where boost notifications should be sent",
    title="Custom title (optional, default: 'New Server Boost!')",
    emoji="Custom emoji shown before the title (optional, default: 🎉)",
    description="Custom description (optional). Placeholders: {mention} {user} {server} {count} {tier}"
)
async def slash_boostconfig(
    i: discord.Interaction,
    channel: discord.TextChannel,
    title: Optional[str] = None,
    emoji: Optional[str] = None,
    description: Optional[str] = None
):
    if not (i.user.id == bot.owner_id or i.user.guild_permissions.manage_guild):
        return await i.response.send_message(embed=error_embed("You don't have permission to use this command."), ephemeral=True)

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
    preview.set_footer(text=f"{i.guild.name} • Preview — this is what it'll look like")

    await i.response.send_message(
        embed=success_embed(f"Boost notifications will now be sent to {channel.mention} whenever a member boosts."),
        ephemeral=True
    )
    await i.followup.send(embed=preview, ephemeral=True)

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def slash_ping(i: discord.Interaction):
    lat = round(bot.latency * 1000)
    await i.response.send_message(embed=base_embed("Pong!", f"Latency: **{lat}ms**", COLOR_SUCCESS if lat < 100 else COLOR_WARNING))

@bot.tree.command(name="afk", description="Set yourself as AFK — anyone who mentions you will be notified.")
@app_commands.describe(reason="Optional reason shown to people who mention you (default: 'AFK')")
async def slash_afk(i: discord.Interaction, reason: Optional[str] = None):
    await do_afk_set(i.guild, i.user, reason or "", i.response.send_message)

@bot.tree.command(name="help", description="View every VALLENT EXS command.")
async def slash_help(i: discord.Interaction):
    has_np = user_has_no_prefix(i.guild, i.user)
    view   = HelpView(i.user.id, i.user.id == bot.owner_id, has_np)
    await i.response.send_message(embed=view.home_embed(), view=view, ephemeral=True)
    view.message = await i.original_response()



@bot.event
async def on_member_join(member: discord.Member):
    # Verification runs for ANY guild that has it configured & enabled —
    # deliberately placed before the support-server-only return below,
    # since that early return only gates the badge/welcome-DM logic.
    if not member.bot:
        await _apply_unverified_role(member)

    support_server_id = int(os.getenv("SUPPORT_SERVER_ID", "0"))
    if member.guild.id != support_server_id or member.bot:
        return
    uid = member.id
    # Grant the USER badge when joining the support server
    support_members = cfg.setdefault("support_server_members", [])
    if uid not in support_members:
        support_members.append(uid)
        save_config(cfg)

    boosted = can_receive_join_boost(uid)
    if boosted:
        grant_xp_boost(uid, minutes=60, multiplier=1.10)
        mark_join_boost_granted(uid)

    badge_lines, _ = _badge_display_lines(uid)
    role   = get_bot_role(uid)
    bonus_line = (
        "Bonus: **+10% XP Boost** active for **60 minutes** on every server using " + BOT_NAME + "!\n\n"
        if boosted else ""
    )
    embed  = discord.Embed(
        title="Welcome to " + member.guild.name + "!",
        description=(
            "Hey " + member.mention + "!\n\n"
            "You just earned the **USER** badge!\n"
            + bonus_line +
            "Type `profile` to see your badges.\n\nType `help` to see every command."
        ),
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
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
            w = discord.Embed(description=member.mention + " has joined!", color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
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
        msg = "You don't have permission to use this command."
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
        await ctx.send(embed=error_embed("You don't have access to this command."), delete_after=5)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=error_embed(f"Missing argument: `{error.param.name}`"), delete_after=5)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(embed=error_embed(f"Invalid argument: {error}"), delete_after=5)
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
