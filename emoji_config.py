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

BADGE_FOUNDER    = "<:emoji_58:1522615540500398080>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_56:1522618679358132264>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_54:1522618599468961903>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_53:1522689662769037493>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_55:1522689748785959024>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_55:1522618640397111507>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:emoji_63:1522588934498943016>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_56:1522684281560764577>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_58:1522626657658212362>"   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_52:1522428807418478783>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_57:1522429186860519483>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_48:1522398507066196059>"   # Icon untuk section Info
ICON_TICKET      = "<a:emoji_55:1522398979432775700>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_57:1522403174550343831>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_51:1522428728355979435>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_61:1522404287898976317>"   # Icon untuk section Antispam
ICON_LANGUAGE    = "<:emoji_59:1522399712563564595>"   # Icon untuk section Language
ICON_OWNER       = "<:emoji_56:1522402451104464946>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:emoji_56:1522694857913667684>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_59:1522400572228108389>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
# Status / result icons
ICON_SUCCESS     = "<:emoji_59:1522429663690100756>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_60:1522431940492398754>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_61:1522432288468762704>"   # Icon warning / peringatan
ICON_LOADING     = "<a:loading:1522215143830847602>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_54:1522429025471954994>"   # Icon di header profile
ICON_BADGES      = "<a:emoji_57:1522620020167938159>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<:emoji_53:1522428945100705812>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<:emoji_63:1522444496799924274>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_54:1522627571798380674>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_55:1522627616224313414>"  # Icon tombol Close Ticket

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
