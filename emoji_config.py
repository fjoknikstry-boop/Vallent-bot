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

BADGE_FOUNDER    = "<:emoji_22:1528921865773518848>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_53:1528919486848172154>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_55:1528951862571827210>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_57:1528919682286092360>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_56:1528951893198372874>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_52:1528919429717561354>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:emoji_40:1528941101543591998>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_51:1528919382389035018>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_20:1528921287043584092>"   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_28:1528929786511228939>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_33:1528929910100463666>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_49:1528947364189049012>"   # Icon untuk section Info
ICON_TICKET      = "<:emoji_35:1528930032989372708>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_18:1527829456071168191>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_41:1528941125438541904>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_48:1528942175545593967>"   # Icon untuk section Antispam
ICON_OWNER       = "<:emoji_40:1527830518115336313>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:emoji_42:1528941192493142107>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_31:1528929865267544164>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_IGNORE      = "<:emoji_45:1528941265368907877>"
ICON_AUTOMOD     = "<:emoji_51:1528948381559296061>"
ICON_AUTORESPONSE = "<:emoji_42:1528941215330992280>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
ICON_AFK          = "<:emoji_36:1528930072386338926>"   # Icon untuk section & notifikasi AFK — isi ID emoji lu di sini (fallback: 💤)
# Status / result icons
ICON_SUCCESS     = "<:emoji_37:1528930134349058248>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_38:1528930169950310441>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_32:1528929890038972466>"   # Icon warning / peringatan
ICON_LOADING     = "<:emoji_29:1528929806392229929>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_52:1528948967314817024>"   # Icon di header profile
ICON_BADGES      = "<a:emoji_47:1528089656783142993>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<a:emoji_58:1528919841660993648>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<a:emoji_56:1528919602699047062>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_53:1528949967207534702>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_53:1528949983645138984>"  # Icon tombol Close Ticket

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
