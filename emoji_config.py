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
ICON_MODERATION  = "<:emoji_52:1529987703125442700>"   # Icon untuk section Moderation
ICON_ROLE        = "<:emoji_58:1529987879802241034>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:emoji_51:1529987677850702055>"   # Icon untuk section Info
ICON_TICKET      = "<:emoji_55:1529987766849376407>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:emoji_56:1529987791746760805>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:emoji_63:1529987959410004008>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:emoji_63:1529987994742816900>"   # Icon untuk section Antispam
ICON_OWNER       = "<:emoji_49:1529987523135410196>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:emoji_65:1529988809352151181>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:emoji_61:1529987932180582540>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_VERIFICATION = "<:emoji_50:1529987543813062898>"   # Icon untuk section & panel Verifikasi (captcha) — isi ID emoji lu di sini (fallback: 🔐)
ICON_IGNORE      = "<:emoji_59:1529987896189124842>"
ICON_AUTOMOD     = "<:emoji_57:1529987833354387577>"
ICON_AUTORESPONSE = "<:emoji_54:1529987747337732310>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
ICON_AFK          = "<:emoji_46:1529987166225039450>"   # Icon untuk section & notifikasi AFK — isi ID emoji lu di sini (fallback: 💤)
# Status / result icons
ICON_SUCCESS     = "<:emoji_37:1528930134349058248>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:emoji_38:1528930169950310441>"   # Icon error / gagal
ICON_WARNING     = "<:emoji_32:1528929890038972466>"   # Icon warning / peringatan
ICON_LOADING     = "<a:emoji_53:1529240301539954778>"   # Icon loading / proses

# ══════════════════════════════════════════════════════════════════
# BOT STATUS UPDATE ICONS (dipakai command `botstatus` — notif di channel
# status support server: online/maintenance/update/offline/degraded)
# ══════════════════════════════════════════════════════════════════
 
ICON_STATUS_ONLINE      = "<a:Status:1529931214054752427>"   # isi ID emoji lu di sini (fallback: 🟢)
ICON_STATUS_OFFLINE     = "<a:Offline:1529931159549776132>"   # isi ID emoji lu di sini (fallback: 🔴)
ICON_STATUS_MAINTENANCE = "<:yellow_status:1529931730935611526>"   # isi ID emoji lu di sini (fallback: 🟠)
ICON_STATUS_UPDATE      = "<a:online:1529932716529946645>"   # isi ID emoji lu di sini (fallback: 🔵)
ICON_STATUS_DEGRADED    = "<a:Loading:1529932224655527948>"   # isi ID emoji lu di sini (fallback: 🟡)

# ══════════════════════════════════════════════════════════════════
# EMBED BUILDER ICONS (dipakai command `embed` / `/embed` — help menu
# section icon & tombol Send di panel builder)
# ══════════════════════════════════════════════════════════════════
 
ICON_EMBED       = "<:emoji_53:1529987727452541180>"   # Icon untuk section Embed Builder di help menu — isi ID emoji lu di sini (fallback: 🖼️)
ICON_EMBED_SEND  = "<:emoji_59:1529943396615979119>"   # Icon untuk tombol Send di panel /embed — isi ID emoji lu di sini (fallback: ✅)
 
# Profile card icons
ICON_PROFILE     = "<:emoji_52:1528948967314817024>"   # Icon di header profile
ICON_BADGES      = "<a:emoji_47:1528089656783142993>"   # Icon di ALL BADGES
ICON_COMMANDS    = "<a:music_2:1528961515879927949>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<a:emoji_52:1529240243167826021>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:emoji_53:1528949967207534702>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:emoji_53:1528949983645138984>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<a:emoji_51:1529240194920874164>" # Icon reaksi giveaway (default 🎉 kalau kosong)
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
