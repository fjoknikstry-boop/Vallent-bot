"""
VALLENT EXS — Rank Card Renderer
===================================
Generate rank-card & level-up card gambar secara LOKAL pakai Pillow — gak
gantung ke API pihak ketiga (some-random-api.com dkk) yang gampang down /
kena rate limit. Style-nya dark red/crimson, ngikutin branding VALLENT EXS.

Font di-bundle sendiri di assets/fonts/ (lisensi SIL OFL, boleh
didistribusikan ulang) biar tampilannya konsisten di mesin manapun bot
di-deploy (Railway, VPS, lokal, dll) — gak tergantung font apa yang
kebetulan ke-install di OS host.
"""

import io
import logging
import os

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("rank_card")

# ══════════════════════════════════════════════════════════════════
# ASSETS
# ══════════════════════════════════════════════════════════════════

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_BASE_DIR, "assets", "fonts")

F_DISPLAY = os.path.join(_FONT_DIR, "BigShoulders-Bold.ttf")
F_BOLD    = os.path.join(_FONT_DIR, "Outfit-Bold.ttf")
F_REG     = os.path.join(_FONT_DIR, "Outfit-Regular.ttf")

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load font dengan cache + fallback ke default PIL font kalau file-nya
    gak ketemu (misal folder assets/ kelewat pas deploy) — biar card tetap
    kegenerate (walau kurang cantik) daripada bikin command crash total."""
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except Exception as e:
            log.warning(f"Font gagal dimuat ({path}): {e} — pakai fallback default.")
            _font_cache[key] = ImageFont.load_default(size=size)
    return _font_cache[key]

# ══════════════════════════════════════════════════════════════════
# PALETTE — samain sama COLOR_* di vallent.py
# ══════════════════════════════════════════════════════════════════

CRIMSON   = (220, 20, 60)
DARK_RED  = (139, 0, 0)
BG_TOP    = (14, 8, 9)
BG_BOTTOM = (35, 8, 10)
WHITE     = (245, 245, 245)
MUTED     = (170, 150, 150)
GOLD      = (245, 158, 11)

# ══════════════════════════════════════════════════════════════════
# PRIMITIVES
# ══════════════════════════════════════════════════════════════════

def _vertical_gradient(size, top, bottom) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        base.putpixel((0, y), tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3)))
    return base.resize((w, h))

def _horizontal_gradient(size, left, right) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (w, 1))
    for x in range(w):
        t = x / max(w - 1, 1)
        base.putpixel((x, 0), tuple(int(left[c] + (right[c] - left[c]) * t) for c in range(3)))
    return base.resize((w, h))

def _rounded_mask(size, radius) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask

def _safe_avatar(avatar_bytes: bytes) -> Image.Image:
    """Kalau avatar gagal di-decode (network error, format aneh, dll), pakai
    placeholder abu-abu polos daripada bikin seluruh card gagal digenerate."""
    try:
        return Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except Exception:
        placeholder = Image.new("RGBA", (256, 256), (45, 45, 45, 255))
        ImageDraw.Draw(placeholder).ellipse([48, 40, 208, 200], fill=(90, 90, 90, 255))
        return placeholder

def _circle_avatar(avatar_img: Image.Image, diameter: int, ring_color, ring_width: int = 6) -> Image.Image:
    avatar_img = avatar_img.convert("RGBA").resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(avatar_img, (0, 0), mask)
    ring_size = diameter + ring_width * 2
    ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([0, 0, ring_size, ring_size], fill=ring_color)
    rd.ellipse([ring_width, ring_width, ring_width + diameter, ring_width + diameter], fill=(0, 0, 0, 0))
    ring.paste(out, (ring_width, ring_width), out)
    return ring

def _draw_progress_bar(card_img: Image.Image, x, y, w, h, pct, track_color, fill_left, fill_right):
    draw = ImageDraw.Draw(card_img)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=track_color)
    pct = max(0.0, min(pct, 1.0))
    fill_w = max(int(w * pct), h) if pct > 0.01 else 0
    if fill_w > 0:
        grad = _horizontal_gradient((fill_w, h), fill_left, fill_right)
        mask = _rounded_mask((fill_w, h), h // 2)
        card_img.paste(grad, (x, y), mask)

# ══════════════════════════════════════════════════════════════════
# RANK CARD — dipakai di command `rank` / `/rank`
# ══════════════════════════════════════════════════════════════════

def render_rank_card(
    avatar_bytes: bytes,
    username: str,
    level: int,
    rank: int,
    cur_xp: int,
    need_xp: int,
    total_xp: int,
    is_premium: bool = False,
    messages: int = 0,
) -> io.BytesIO:
    W, H = 934, 282
    card = _vertical_gradient((W, H), BG_TOP, BG_BOTTOM).convert("RGBA")

    # aksen garis diagonal tipis di sisi kanan
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(-2, 6):
        xx = W - 60 + i * 70
        od.polygon([(xx, 0), (xx + 30, 0), (xx - 60, H), (xx - 90, H)], fill=(139, 0, 0, 16))
    card = Image.alpha_composite(card, overlay)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=22, outline=(*DARK_RED, 255), width=3)

    av = _safe_avatar(avatar_bytes)
    ring_color = (*GOLD, 255) if is_premium else (*CRIMSON, 255)
    avatar_d = 168
    avatar_ring = _circle_avatar(av, avatar_d, ring_color, ring_width=6)
    ax, ay = 46, (H - avatar_ring.height) // 2
    card.paste(avatar_ring, (ax, ay), avatar_ring)

    draw = ImageDraw.Draw(card)
    text_x = ax + avatar_ring.width + 36

    f_name  = _font(F_DISPLAY, 52)
    f_small = _font(F_BOLD, 24)
    f_tiny  = _font(F_REG, 20)
    f_xp    = _font(F_BOLD, 22)

    name_y = 40
    uname  = username.upper()
    max_w  = W - text_x - 56
    size   = 52
    while draw.textlength(uname, font=f_name) > max_w and size > 26:
        size  -= 2
        f_name = _font(F_DISPLAY, size)
    draw.text((text_x, name_y), uname, font=f_name, fill=WHITE)

    sub_y = name_y + 60
    if is_premium:
        draw.text((text_x, sub_y), "★ PREMIUM MEMBER", font=f_small, fill=GOLD)
        sub_y += 30

    rl_y = sub_y + 4
    draw.text((text_x, rl_y), "RANK", font=f_tiny, fill=MUTED)
    rank_w = draw.textlength("RANK ", font=f_tiny)
    draw.text((text_x + rank_w, rl_y - 3), f"#{rank}", font=f_small, fill=WHITE)
    lvl_x = text_x + rank_w + draw.textlength(f"#{rank}", font=f_small) + 40
    draw.text((lvl_x, rl_y), "LEVEL", font=f_tiny, fill=MUTED)
    lvl_w = draw.textlength("LEVEL ", font=f_tiny)
    draw.text((lvl_x + lvl_w, rl_y - 3), str(level), font=f_small, fill=(*CRIMSON, 255))

    bar_y = rl_y + 46
    bar_w = W - text_x - 56
    bar_h = 26
    _draw_progress_bar(card, text_x, bar_y, bar_w, bar_h, cur_xp / max(need_xp, 1), (40, 18, 20), DARK_RED, CRIMSON)

    draw = ImageDraw.Draw(card)
    xp_text = f"{cur_xp:,} / {need_xp:,} XP"
    xp_w = draw.textlength(xp_text, font=f_xp)
    draw.text((text_x + bar_w - xp_w, bar_y - 30), xp_text, font=f_xp, fill=WHITE)

    footer = f"Total XP: {total_xp:,} • Messages: {messages:,}"
    draw.text((text_x, bar_y + bar_h + 14), footer, font=f_tiny, fill=MUTED)

    _watermark(draw, card.size)

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════
# LEVEL-UP CARD — dipakai di notifikasi level up otomatis
# ══════════════════════════════════════════════════════════════════

def render_levelup_card(avatar_bytes: bytes, username: str, new_level: int, is_premium: bool = False) -> io.BytesIO:
    W, H = 934, 282
    card = _vertical_gradient((W, H), (18, 4, 6), (48, 6, 10)).convert("RGBA")

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = 160, H // 2
    for r, a in [(230, 26), (170, 40), (110, 60)]:
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 20, 60, a))
    card = Image.alpha_composite(card, glow)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=22, outline=(*DARK_RED, 255), width=3)

    av = _safe_avatar(avatar_bytes)
    ring_color = (*GOLD, 255) if is_premium else (*CRIMSON, 255)
    avatar_d = 176
    avatar_ring = _circle_avatar(av, avatar_d, ring_color, ring_width=7)
    ax, ay = 60, (H - avatar_ring.height) // 2
    card.paste(avatar_ring, (ax, ay), avatar_ring)

    draw = ImageDraw.Draw(card)
    text_x = ax + avatar_ring.width + 50

    f_tag  = _font(F_BOLD, 26)
    f_huge = _font(F_DISPLAY, 84)
    f_name = _font(F_BOLD, 30)

    draw.text((text_x, 46), "LEVEL UP", font=f_tag, fill=(*CRIMSON, 255))
    draw.text((text_x, 82), f"LEVEL {new_level}", font=f_huge, fill=WHITE)

    sub = f"{username} reached a new level!"
    max_w = W - text_x - 40
    size  = 30
    f_sub = f_name
    while draw.textlength(sub, font=f_sub) > max_w and size > 16:
        size -= 2
        f_sub = _font(F_BOLD, size)
    draw.text((text_x, 190), sub, font=f_sub, fill=MUTED)

    _watermark(draw, card.size)

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

def _watermark(draw: ImageDraw.ImageDraw, size):
    W, H = size
    wm_font = _font(F_BOLD, 16)
    watermark = "VALLENT EXS"
    wm_w = draw.textlength(watermark, font=wm_font)
    draw.text((W - wm_w - 24, H - 32), watermark, font=wm_font, fill=(120, 60, 60))
