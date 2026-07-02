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

BADGE_FOUNDER    = "<:Coowner:1522213410773794877>"   # Emoji untuk badge FOUNDER
BADGE_DEVELOPER  = "<:staff_red:1522211962153336863>"   # Emoji untuk badge DEVELOPER
BADGE_MANAGEMENT = "<:Red_Star:1522212285874045049>"   # Emoji untuk badge MANAGEMENT
BADGE_STAFF      = "<:roles:1522207871037735022>"   # Emoji untuk badge STAFF
BADGE_PREMIUM    = "<:premium:1522207934174593044>"   # Emoji untuk badge PREMIUM
BADGE_NOPREFIX   = "<:potassium:1522209119157882960>"   # Emoji untuk badge NO PREFIX
BADGE_USER       = "<:friend:1522208555753803858>"   # Emoji untuk badge USER

# ══════════════════════════════════════════════════════════════════
# UI / SECTION EMOJI (untuk help, info, dll)
# ══════════════════════════════════════════════════════════════════

# Section headers di !vx help
ICON_MODERATION  = "<:Staff:1522207707493433526>"   # Icon untuk section Moderation
ICON_ROLE        = "<a:music_2:1522289402058113225>"   # Icon untuk section Role & Voice
ICON_INFO        = "<:Commands:1522207444087078954>"   # Icon untuk section Info
ICON_TICKET      = "<a:kenji_chat:1522290686727291001>"   # Icon untuk section Ticket
ICON_LEVEL       = "<a:Walking:1522213874320019477>"   # Icon untuk section Level & XP
ICON_GIVEAWAY    = "<:gift:1522208233698230333>"   # Icon untuk section Giveaway
ICON_ANTISPAM    = "<a:offical_sarkar:1522208889670602846>"   # Icon untuk section Antispam
ICON_LANGUAGE    = "<a:globe:1522214311194394788>"   # Icon untuk section Language
ICON_OWNER       = "<:owner:1522208043994058903>"   # Icon untuk section Owner Only

# Status / result icons
ICON_SUCCESS     = "<:tick:1522208142438563900>"   # Icon sukses (checklist, dll)
ICON_ERROR       = "<:cross:1522209867157344406>"   # Icon error / gagal
ICON_WARNING     = "<:warn:1522210433933639844>"   # Icon warning / peringatan
ICON_LOADING     = "<a:loading:1522215143830847602>"   # Icon loading / proses

# Profile card icons
ICON_PROFILE     = "<:author:1522209388537053194>"   # Icon di header profile
ICON_BADGES      = "<a:HeadMod:1478516188681338880> "   # Icon di ALL BADGES
ICON_COMMANDS    = "<:settings:1522216254448992317>"   # Icon di Commands Runned
ICON_PREMIUM_TAG = "<a:emoji_773:1522210263821062301>"   # Icon di keterangan premium

# Ticket icons
ICON_TICKET_OPEN  = "<:email:1522217434319159448>"  # Icon tombol Open Ticket
ICON_TICKET_CLOSE = "<:home:1522217893184405667>"  # Icon tombol Close Ticket

# Giveaway icons
ICON_GIVEAWAY_REACT = "<a:A_Tada:1522215069470036010>" # Icon reaksi giveaway (default 🎉 kalau kosong)
ICON_WINNER          = "<:Trophy:1522215598052999251>" # Icon pengumuman pemenang

# ══════════════════════════════════════════════════════════════════
# HELPER FUNCTION
# ══════════════════════════════════════════════════════════════════

def e(emoji_str: str, fallback: str = "") -> str:
    """
    Return emoji kalau sudah diisi, fallback kalau masih kosong.
    Contoh: e(BADGE_FOUNDER, "👑") → "<:founder:123>" atau "👑"
    """
    return emoji_str if emoji_str.strip() else fallback
