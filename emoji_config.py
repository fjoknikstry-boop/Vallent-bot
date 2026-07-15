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

BADGE_FOUNDER    = "<:emoji_55:1527095333992140920>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_10:1527088574330048544>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_12:1527088640449056870>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_28:1527089200871116820>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_15:1527088729682874439>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_39:1527089881333891153>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:emoji_17:1527088794602442832>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_24:1527089054204694618>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_55:1527095812763549766>"   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_38:1527089831618805770>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_53:1527091577661689957>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_54:1527099482750320750>"   # Icon untuk section Info
ICON_TICKET      = "<:emoji_27:1527089156516352132>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_55:1527093348517548044>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_14:1527088695688302732>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_30:1527089301052063835>"   # Icon untuk section Antispam
ICON_OWNER       = "<:emoji_11:1527088601240961094>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:emoji_50:1527090427793117315>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_18:1527088833634631911>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_IGNORE      = "<:emoji_55:1527094266453823560>"
ICON_AUTOMOD     = "<:emoji_40:1527089925046931516>"
ICON_AUTORESPONSE = "<:emoji_13:1527088666269192317>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
# Status / result icons
ICON_SUCCESS     = "<:emoji_22:1527088976635363469>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_52:1527091518073081927>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_23:1527089024454623326>"   # Icon warning / peringatan
ICON_LOADING     = "<:emoji_45:1527090183772831865>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_44:1527090110422585484>"   # Icon di header profile
ICON_BADGES      = "<:emoji_55:1527094599368179722>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<:emoji_36:1527089697409601748>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<:emoji_29:1527089263861043240>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_43:1527090067535954152>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_42:1527090028541509722>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<:emoji_25:1527089098513191053>" # Icon reaksi giveaway (default 🎉 kalau kosong)
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
