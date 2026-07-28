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

BADGE_FOUNDER    = "<:owner:1531552182573203486>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:Dev:1531552304447098950>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:emoji_47:1528958972441137202>"   # Emoji untuk badge MANAGEMENT
BADGE_MODERATOR       = "<:emoji_68:1530536974723715222>"   # Emoji untuk badge MODERATOR — isi ID emoji lu di sini
BADGE_SERVER_MANAGER  = "<:emoji_49:1528959014304481311>"   # Emoji untuk badge SERVER MANAGER — isi ID emoji lu di sini
BADGE_STAFF      = "<:emoji_54:1528959142297997332>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:premium:1528961463094612110>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:emoji_51:1528919382389035018>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:users:1531551241132441722>"   # Emoji untuk badge USER
BADGE_MOONKEEPER = "<a:emoji_55:1528919570918670396>"   # Emoji untuk badge MOONKEEPER — isi ID emoji lu di sini (fallback: 🌙)

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:topgg_ico_bonk:1531543654785745067>"   # Icon untuk section Moderation
ICON_ROLE        = "<:topgg_ico_sparkles:1531544618779283517>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:topgg_ico_info:1531543563077419030>"   # Icon untuk section Info
ICON_TICKET      = "<:topgg_ico_note:1531544350100816034>"   # Icon untuk section Ticket
ICON_LEVEL       = "<:topgg_ico_chart:1531543437210419392>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:topgg_ico_tada:1531542901652324406>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<:topgg_ico_taskforce:1531544158928638042>"   # Icon untuk section Antispam
ICON_OWNER       = "<:topgg_ico_fire:1531544694356443176>"   # Icon untuk section Owner Only
ICON_BOOST       = "<:topgg_ico_rocket:1531543284529233983>>"   # Icon default notifikasi server boost — isi ID emoji boost lu di sini
ICON_ANTINUKE    = "<:topgg_ico_flag:1531548767986385007>"   # Icon untuk section & alert Anti-Nuke — isi ID emoji lu di sini
ICON_VERIFICATION = "<:topgg_ico_lock:1531543141423906867>"   # Icon untuk section & panel Verifikasi (captcha) — isi ID emoji lu di sini (fallback: 🔐)
ICON_IGNORE      = "<:topgg_ico_question:1531549041748480021>"
ICON_AUTOMOD     = "<:topgg_ico_bot:1531542791014846564>"
ICON_AUTORESPONSE = "<:topgg_ico_chat:1531547645313814560>"   # Icon untuk section Auto-Response — isi ID emoji lu di sini
ICON_AFK          = "<:topgg_ico_cookie:1531550441169617018>"   # Icon untuk section & notifikasi AFK — isi ID emoji lu di sini (fallback: 💤)
# Status / result icons
ICON_SUCCESS     = "<:topgg_opt_yes:1531543705989677069>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:topgg_opt_no:1531543760079556718>"   # Icon error / gagal
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
 
ICON_EMBED       = "<:topgg_ico_event:1531543951201534032>"   # Icon untuk section Embed Builder di help menu — isi ID emoji lu di sini (fallback: 🖼️)
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
