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

BADGE_FOUNDER    = "<:emoji_32:1527830120008515715>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_8:1527829144333979679>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_25:1527829696471896105>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_50:1527832954624147608>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_48:1527832768254443588>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_50:1527834360970084573>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:emoji_10:1527829194879275158>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_41:1527831613533065457>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_9:1527829167490732155>"   # Emoji untuk badge USER
BADGE_MOONKEEPER = "<:emoji_58:1528966956068376627>"   # Emoji untuk badge MOONKEEPER — isi ID emoji lu di sini (fallback: 🌙)

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_42:1527831657376387182>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_55:1527837668652749002>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_37:1527830297151016960>"   # Icon untuk section Info
ICON_TICKET      = "<:emoji_42:1527831634714562651>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_18:1527829456071168191>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_46:1527831774036496567>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_24:1527829637697110096>"   # Icon untuk section Antispam
ICON_OWNER       = "<:emoji_40:1527830518115336313>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:emoji_51:1527836174331150407>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_19:1527829486576472186>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_IGNORE      = "<:emoji_28:1527829762884767936>"
ICON_AUTOMOD     = "<:emoji_24:1527829666428223679>"
ICON_AUTORESPONSE = "<:emoji_44:1527831691706634481>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
ICON_AFK          = ""   # Icon untuk section & notifikasi AFK — isi ID emoji lu di sini (fallback: 💤)
# Status / result icons
ICON_SUCCESS     = "<:emoji_27:1527829730181775481>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_35:1527830232281645217>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_39:1527830327945592912>"   # Icon warning / peringatan
ICON_LOADING     = "<:emoji_51:1527836192572178512>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_12:1527829243495452732>"   # Icon di header profile
ICON_BADGES      = "<a:emoji_47:1528089656783142993>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<:emoji_47:1527831886225997884>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<:emoji_15:1527829369559453937>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_43:1527090067535954152>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_54:1527837640576077875>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<:emoji_14:1527088695688302732>" # Icon reaksi giveaway (default 🎉 kalau kosong)
ICON_WINNER          = "<:emoji_11:1527088601240961094>" # Icon pengumuman pemenang

# ══════════════════════════════════════════════════════════════════
# HELPER FUNCTION
# ══════════════════════════════════════════════════════════════════

def e(emoji_str: str, fallback: str = "") -> str:
    """
    Return emoji kalau sudah diisi, fallback kalau masih kosong.
    Contoh: e(BADGE_FOUNDER, "👑") → "<:founder:123>" atau "👑"
    """
    return emoji_str if emoji_str.strip() else fallback
