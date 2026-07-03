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

BADGE_FOUNDER    = "<:emoji_50:1522428696479268994>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_57:1522399082918969444>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_53:1522398735886319698>"   # Emoji untuk badge MANAGEMENT
BADGE_STAFF      = "<:emoji_60:1522404179661033604>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:emoji_63:1522444610239074397>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_51:1522398604562665573>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_55:1522429080023339028>"   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_52:1522428807418478783>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_57:1522429186860519483>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_48:1522398507066196059>"   # Icon untuk section Info
ICON_TICKET      = "<a:emoji_55:1522398979432775700>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_57:1522403174550343831>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_61:1522400637646671912>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_61:1522404287898976317>"   # Icon untuk section Antispam
ICON_LANGUAGE    = "<:emoji_59:1522399712563564595>"   # Icon untuk section Language
ICON_OWNER       = "<:emoji_56:1522402451104464946>"   # Icon untuk section Owner Only

# Status / result icons
ICON_SUCCESS     = "<:emoji_59:1522429663690100756>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_60:1522431940492398754>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_61:1522432288468762704>"   # Icon warning / peringatan
ICON_LOADING     = "<a:loading:1522215143830847602>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_54:1522429025471954994>"   # Icon di header profile
ICON_BADGES      = "<:emoji_54:1522407563147219074>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<:emoji_53:1522428945100705812>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<:emoji_63:1522444496799924274>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_54:1522398918694928664>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_55:1522411835725185186>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<a:A_Tada:1522215069470036010>" # Icon reaksi giveaway (default 🎉 kalau kosong)
ICON_WINNER          = "<a:emoji_53:1522406976632389855>" # Icon pengumuman pemenang

# ══════════════════════════════════════════════════════════════════
# HELPER FUNCTION
# ══════════════════════════════════════════════════════════════════

def e(emoji_str: str, fallback: str = "") -> str:
    """
    Return emoji kalau sudah diisi, fallback kalau masih kosong.
    Contoh: e(BADGE_FOUNDER, "👑") → "<:founder:123>" atau "👑"
    """
    return emoji_str if emoji_str.strip() else fallback
