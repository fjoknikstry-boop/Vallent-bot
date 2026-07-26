"""
VALLENT EXS — Embed Link Buttons
==================================
Self-contained, same design as ticket_types.py / antinuke.py / vote_system.py
— never imports anything from vallent.py. Pure data + discord.ui.View
building; vallent.py wires this into its own /embed builder draft, modals
and send/edit logic.

Concept
-------
The /embed builder can optionally attach one or more LINK buttons under
the embed (Discord's own hard cap: 25 buttons total in one message). A
draft's "links" key is just a plain list of
`{"label": str, "url": str, "emoji": str|None}` dicts — nothing here
depends on any bot/cfg state, so it's trivial to test or reuse.

If a draft has zero links, build_link_view() returns None on purpose —
callers should then send/edit the message with NO `view` argument at
all, so it stays a completely ordinary embed message (no empty button
row silently attached).
"""

import re
from typing import Optional

import discord

MAX_LINKS = 25  # Discord's hard cap across all buttons in one message

_URL_RE = re.compile(r"^https?://\S+$")


def validate_link(label: str, url: str) -> Optional[str]:
    """Returns a human-readable error, or None if the link is valid."""
    if not (label or "").strip():
        return "Label can't be empty."
    if not (url or "").strip() or not _URL_RE.match(url.strip()):
        return "URL must start with `http://` or `https://`."
    return None


def add_link(links: list, label: str, url: str, emoji: str = "") -> Optional[str]:
    """Append a link button spec to `links` IN PLACE. Returns an error
    string (leaving `links` untouched) if invalid or already at the cap,
    else None on success."""
    if len(links) >= MAX_LINKS:
        return f"This embed already has the max {MAX_LINKS} link buttons Discord allows."
    err = validate_link(label, url)
    if err:
        return err
    links.append({"label": label.strip()[:80], "url": url.strip(), "emoji": (emoji or "").strip() or None})
    return None


def build_link_view(links: list) -> Optional[discord.ui.View]:
    """Build the real View to send/edit onto the final message. Returns
    None for an empty list on purpose — see module docstring."""
    if not links:
        return None
    view = discord.ui.View(timeout=None)  # link buttons never expire — nothing here has a callback to time out
    for link in links[:MAX_LINKS]:
        view.add_item(discord.ui.Button(
            label=(link.get("label") or "Link")[:80],
            url=link["url"],
            style=discord.ButtonStyle.link,
            emoji=link.get("emoji") or None,
        ))
    return view


def parse_links_from_message(message: discord.Message) -> list:
    """Pull existing link buttons off an already-sent message — used when
    loading a message into the builder for editing, so any link buttons
    it already had aren't silently lost if the user doesn't touch them.
    Non-link components (there shouldn't be any on a plain embed message,
    but be defensive) are skipped."""
    links = []
    for row in getattr(message, "components", []) or []:
        for comp in getattr(row, "children", []) or []:
            url = getattr(comp, "url", None)
            if url:
                links.append({
                    "label": getattr(comp, "label", None) or "Link",
                    "url": url,
                    "emoji": str(comp.emoji) if getattr(comp, "emoji", None) else None,
                })
    return links[:MAX_LINKS]
