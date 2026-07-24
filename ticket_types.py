"""
VALLENT EXS — Ticket Types (multi-category dropdown support)
==============================================================
Split out of vallent.py on purpose so that file doesn't keep growing —
this module is self-contained (same design as antinuke.py): it never
imports anything from vallent.py. Callers pass in whatever guild/panel
data it needs and get back plain data (dicts, discord.SelectOption lists)
that vallent.py wires into its own embeds/views/config saving.

Concept
-------
A ticket panel can now optionally have multiple "types" under one
dropdown — e.g. "Report a Bug" -> one category, "Billing" -> a totally
different category/log channel/support role. Each type is stored under
panel["types"][type_key] = {label, emoji, description, category,
log_channel, support_role, max_tickets}.

Panels that never configure any types keep working exactly like before
(single category, single button or single-option dropdown) — nothing
here is a breaking change, `get_type_config` transparently falls back to
the panel's own top-level category/log_channel/support_role/max_tickets
when no types dict (or an empty one) is present.
"""

import re
from typing import Optional

import discord

MAX_TYPES_PER_PANEL = 25  # Discord's own hard cap on select menu options


def slugify_type_id(label: str, existing: dict) -> str:
    """Turn a type's label into a short, stable dict key (e.g. 'Billing
    Support' -> 'billing_support'). Uniquified against keys already used
    in this panel, same approach as custom badge IDs — so two similarly
    named types never collide or silently overwrite each other."""
    base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "type"
    key = base
    n = 2
    while key in existing:
        key = f"{base}_{n}"
        n += 1
    return key


def get_type_config(panel: dict, type_key: Optional[str]) -> dict:
    """Resolve the effective category/log/role/max/label for an open-ticket
    action. If the panel has a matching type configured, its own settings
    win (falling back to the panel's top-level values for anything it
    doesn't override); otherwise this is a classic single-category panel
    and the top-level values are used directly."""
    types = panel.get("types") or {}
    if type_key and type_key in types:
        t = types[type_key]
        return {
            "category":     t.get("category") or panel.get("category"),
            "log_channel":  t.get("log_channel") or panel.get("log_channel"),
            "support_role": t.get("support_role") or panel.get("support_role"),
            "max_tickets":  t.get("max_tickets") or panel.get("max_tickets", 1),
            "label":        t.get("label") or type_key,
        }
    return {
        "category":     panel.get("category"),
        "log_channel":  panel.get("log_channel"),
        "support_role": panel.get("support_role"),
        "max_tickets":  panel.get("max_tickets", 1),
        "label":        panel.get("title") or "Ticket",
    }


def build_type_select_options(panel: dict) -> list:
    """discord.SelectOption list from a panel's configured types. Returns
    an empty list if the panel has no multi-type config (0 or 1 types
    isn't worth a "pick your type" dropdown) — caller should fall back to
    its existing single button/select behavior in that case."""
    types = panel.get("types") or {}
    if len(types) < 2:
        return []
    options = []
    for key, t in types.items():
        options.append(discord.SelectOption(
            label=(t.get("label") or key)[:100],
            value=key,
            description=(t.get("description") or "")[:100] or None,
            emoji=t.get("emoji") or None,
        ))
    return options[:MAX_TYPES_PER_PANEL]


def format_type_list(panel: dict, resolve_channel, resolve_role) -> str:
    """Human-readable summary of a panel's configured types, for the
    `/tickettype list` command. `resolve_channel`/`resolve_role` are
    passed in (e.g. guild.get_channel / guild.get_role) so this module
    never needs its own guild/bot reference."""
    types = panel.get("types") or {}
    if not types:
        return "No ticket types configured — this panel uses its single top-level category."
    lines = []
    for key, t in types.items():
        cat  = resolve_channel(t.get("category")) if t.get("category") else None
        log  = resolve_channel(t.get("log_channel")) if t.get("log_channel") else None
        role = resolve_role(t.get("support_role")) if t.get("support_role") else None
        emoji = (t.get("emoji") + " ") if t.get("emoji") else ""
        lines.append(
            f"{emoji}**{t.get('label', key)}** — `{key}`\n"
            f"　Category: {cat.mention if cat else '*(falls back to panel default)*'} · "
            f"Log: {log.mention if log else '*(falls back to panel default)*'} · "
            f"Role: {role.mention if role else '*(none)*'}"
        )
    return "\n".join(lines)
