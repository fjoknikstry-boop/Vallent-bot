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

BADGE_FOUNDER    = "<:emoji_46:1528958923472769186>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:emoji_50:1528959036626567258>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_47:1528958972441137202>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_54:1528959142297997332>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_49:1528959014304481311>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_47:1528958989470269540>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:premium:1528961463094612110>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_51:1528919382389035018>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:emoji_52:1528959097259688006>"   # Emoji untuk badge USER
BADGE_MOONKEEPER = "<a:emoji_55:1528919570918670396>"   # Emoji untuk badge MOONKEEPER — isi ID emoji lu di sini (fallback: 🌙)

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:emoji_28:1528929786511228939>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_33:1528929910100463666>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_49:1528947364189049012>"   # Icon untuk section Info
ICON_TICKET      = "<:emoji_47:1528941765749510284>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_35:1528930032989372708>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<a:emoji_51:1529240194920874164>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_44:1528941241453252638>"   # Icon untuk section Antispam
ICON_OWNER       = "<:emoji_11:1527088601240961094>"   # Icon untuk section Owner Only
ICON_BOOST       = "<a:emoji_50:1529240171311009802>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_31:1528929865267544164>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_VERIFICATION = "<:emoji_55:1529381471146479676>"   # Icon untuk section & panel Verifikasi (captcha) — isi ID emoji lu di sini (fallback: 🔐)
ICON_IGNORE      = "<:emoji_50:1528948003484864643>"
ICON_AUTOMOD     = "<:emoji_51:1528948381559296061>"
ICON_AUTORESPONSE = "<:emoji_42:1528941215330992280>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
ICON_AFK          = "<:emoji_36:1528930072386338926>"   # Icon untuk section & notifikasi AFK — isi ID emoji lu di sini (fallback: 💤)
# Status / result icons
ICON_SUCCESS     = "<:emoji_37:1528930134349058248>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_38:1528930169950310441>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_32:1528929890038972466>"   # Icon warning / peringatan
ICON_LOADING     = "<a:emoji_53:1529240301539954778>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:emoji_52:1528948967314817024>"   # Icon di header profile
ICON_BADGES      = "<a:emoji_47:1528089656783142993>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<a:music_2:1528961515879927949>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<a:emoji_52:1529240243167826021>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_53:1528949967207534702>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_53:1528949983645138984>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<:emoji_14:1527088695688302732>" # Icon reaksi giveaway (default 🎉 kalau kosong)
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
