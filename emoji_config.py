"""
VALLENT EXS — Emoji Configuration
===================================
Isi semua ID emoji dari server Discord lu di sini.

Cara ambil ID emoji:
1. Upload emoji ke server Discord lu
2. Di chat Discord ketik  \:nama_emoji:  (pakai backslash)
3. Send — Discord akan tampilkan format lengkapnya: <:nama:1234567890>
4. Copy angka ID-nya, paste di bawah

Format:
  - Emoji biasa  : "<:nama:ID>"
  - Emoji animasi: "<a:nama:ID>"

Contoh:
  BADGE_FOUNDER = "<:founder:1234567890123456>"
  BADGE_STAFF   = "<a:staff:9876543210987654>"   # animated
"""

# ══════════════════════════════════════════════════════════════════
# BADGE EMOJI
# ══════════════════════════════════════════════════════════════════

BADGE_FOUNDER    = ""   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = ""   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = ""   # Emoji untuk badge MANAGEMENT
BADGE_STAFF      = ""   # Emoji untuk badge STAFF
BADGE_PREMIUM    = ""   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = ""   # Emoji untuk badge NO PREFIX
BADGE_USER       = ""   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = ""   # Icon untuk section Moderation
ICON_ROLE        = ""   # Icon untuk section Role & Voice
ICON_INFO        = ""   # Icon untuk section Info
ICON_TICKET      = ""   # Icon untuk section Ticket
ICON_LEVEL       = ""   # Icon untuk section Level & XP
ICON_GIVEAWAY    = ""   # Icon untuk section Giveaway
ICON_ANTISPAM    = ""   # Icon untuk section Antispam
ICON_LANGUAGE    = ""   # Icon untuk section Language
ICON_OWNER       = ""   # Icon untuk section Owner Only

# Status / result icons
ICON_SUCCESS     = ""   # Icon sukses (checklist, dll)
ICON_ERROR       = ""   # Icon error / gagal
ICON_WARNING     = ""   # Icon warning / peringatan
ICON_LOADING     = ""   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = ""   # Icon di header profile
ICON_BADGES      = ""   # Icon di ALL BADGES
ICON_COMMANDS    = ""   # Icon di Commands Runned
ICON_PREMIUM_TAG = ""   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = ""  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = ""  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "" # Icon reaksi giveaway (default 🎉 kalau kosong)
ICON_WINNER          = "" # Icon pengumuman pemenang

# ══════════════════════════════════════════════════════════════════
# HELPER FUNCTION
# ══════════════════════════════════════════════════════════════════

def e(emoji_str: str, fallback: str = "") -> str:
    """
    Return emoji kalau sudah diisi, fallback kalau masih kosong.
    Contoh: e(BADGE_FOUNDER, "👑") → "<:founder:123>" atau "👑"
    """
    return emoji_str if emoji_str.strip() else fallback
