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

FONT FALLBACK CHAIN — kenapa ini penting:
Font utama (BigShoulders / Outfit) itu font Latin biasa, banyak karakter
yang gak ke-cover (Cyrillic, Yunani, Arab, Thai, emoji, dll) — kalau
dipaksa render bakal jadi kotak "tofu" putih. Username Discord bisa
berisi HAMPIR APAPUN, jadi setiap karakter dicek satu-satu: kalau font
utama gak punya glyph-nya, otomatis lempar ke font fallback yang cocok
(NotoSans utk Cyrillic/Yunani/Vietnam, NotoSansArabic, NotoSansThai,
NotoEmoji utk emoji). Kalau semua fallback juga gak punya, baru barulah
dibiarkan tofu (kasus sangat jarang — misal aksara langka).
"""

import io
import logging
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger("rank_card")

# ══════════════════════════════════════════════════════════════════
# ASSETS
# ══════════════════════════════════════════════════════════════════

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_BASE_DIR, "assets", "fonts")

F_DISPLAY = os.path.join(_FONT_DIR, "BigShoulders-Bold.ttf")
F_BOLD    = os.path.join(_FONT_DIR, "Outfit-Bold.ttf")
F_REG     = os.path.join(_FONT_DIR, "Outfit-Regular.ttf")

# Font fallback, urut dari yang paling mungkin kepakai. Semua ini variable
# font satu file yang nyimpen banyak ketebalan (axis "wght"), jadi kita
# tinggal set beratnya on-the-fly gak perlu file terpisah per bold/regular.
_FALLBACK_FONTS = [
    os.path.join(_FONT_DIR, "NotoSans-Var.ttf"),        # Latin extended, Cyrillic, Yunani, Vietnam, dst
    os.path.join(_FONT_DIR, "NotoSansArabic-Var.ttf"),  # Arab
    os.path.join(_FONT_DIR, "NotoSansThai-Var.ttf"),    # Thai
    os.path.join(_FONT_DIR, "NotoEmoji-Var.ttf"),       # Emoji (monokrom outline, bukan colored)
]

_font_cache: dict = {}
_cmap_cache: dict = {}

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load font dasar (Latin) dengan cache + fallback ke default PIL font
    kalau file-nya gak ketemu — biar card tetap kegenerate (walau kurang
    cantik) daripada bikin command crash total."""
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except Exception as e:
            log.warning(f"Font gagal dimuat ({path}): {e} — pakai fallback default.")
            _font_cache[key] = ImageFont.load_default(size=size)
    return _font_cache[key]

def _get_cmap(path: str) -> set:
    """Daftar codepoint yang beneran punya glyph di font tersebut — dicek
    sekali per font lalu di-cache, karena baca cmap itu operasi yang agak
    berat kalau diulang tiap karakter."""
    if path not in _cmap_cache:
        try:
            from fontTools.ttLib import TTFont as _TTFont
            _cmap_cache[path] = set(_TTFont(path, fontNumber=0).getBestCmap().keys())
        except Exception as e:
            log.warning(f"Gagal baca cmap {path}: {e}")
            _cmap_cache[path] = set()
    return _cmap_cache[path]

def _load_variable(path: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    """Load font fallback (variable font) di berat tertentu, dengan cache."""
    key = (path, size, weight)
    if key not in _font_cache:
        try:
            f = ImageFont.truetype(path, size)
            try:
                f.set_variation_by_axes([weight] if len(f.get_variation_axes()) == 1 else [weight, 100])
            except Exception:
                pass
            _font_cache[key] = f
        except Exception as e:
            log.warning(f"Font fallback gagal dimuat ({path}): {e}")
            _font_cache[key] = ImageFont.load_default(size=size)
    return _font_cache[key]

def _resolve_font(ch: str, primary_path: str, size: int, bold: bool):
    """Cari font pertama (utama, lalu fallback berurutan) yang punya glyph
    buat karakter ini. Kalau gak ada satupun yang cocok, tetap kembalikan
    font utama (best effort — tofu box, tapi command gak crash)."""
    if ch.isspace() or ord(ch) in _get_cmap(primary_path):
        return _font(primary_path, size)
    weight = 700 if bold else 400
    for fb_path in _FALLBACK_FONTS:
        if os.path.exists(fb_path) and ord(ch) in _get_cmap(fb_path):
            return _load_variable(fb_path, size, weight)
    return _font(primary_path, size)

def _runs(text: str, primary_path: str, size: int, bold: bool = True):
    """Pecah teks jadi potongan-potongan (substring, font) — tiap potongan
    pakai satu font yang sama, biar hemat draw call dan render-nya rapi."""
    runs, cur_font, cur_text = [], None, ""
    for ch in text:
        f = _resolve_font(ch, primary_path, size, bold)
        if f is cur_font:
            cur_text += ch
        else:
            if cur_text:
                runs.append((cur_text, cur_font))
            cur_font, cur_text = f, ch
    if cur_text:
        runs.append((cur_text, cur_font))
    return runs

def draw_text(draw: ImageDraw.ImageDraw, xy, text: str, primary_path: str, size: int, fill, bold: bool = True) -> None:
    """Ganti draw.text() biasa — otomatis lempar tiap karakter yang gak
    ke-cover font utama ke font fallback yang punya glyph-nya."""
    x, y = xy
    for t, f in _runs(text, primary_path, size, bold):
        draw.text((x, y), t, font=f, fill=fill)
        x += draw.textlength(t, font=f)

def text_width(draw: ImageDraw.ImageDraw, text: str, primary_path: str, size: int, bold: bool = True) -> float:
    """Ganti draw.textlength() biasa — ngukur lebar teks yang mixed-font."""
    return sum(draw.textlength(t, font=f) for t, f in _runs(text, primary_path, size, bold))

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

# Premium variants — swapped in wherever a normal card uses the crimson
# palette, so a premium card reads as gold-themed top to bottom instead of
# "red card with a gold ring slapped on".
GOLD_DARK    = (110, 80, 8)     # premium equivalent of DARK_RED (border/blood)
GOLD_BG_TOP  = (16, 12, 4)      # premium equivalent of BG_TOP
GOLD_BG_BTM  = (42, 28, 4)      # premium equivalent of BG_BOTTOM

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

def _draw_diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color) -> None:
    """Ikon diamond digambar langsung (bukan karakter font) — dipakai buat
    tag PREMIUM MEMBER supaya gak pernah jadi kotak tofu apapun font-nya."""
    draw.polygon([(cx, cy - r), (cx + r * 0.72, cy), (cx, cy + r), (cx - r * 0.72, cy)], fill=color)

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
# TACTICAL-CARD PRIMITIVES — distinctive shapes so cards don't read as a
# generic template: angled corner cut, hex avatar frame, HUD corner ticks,
# a huge low-opacity "VX" wordmark, and a fine grain texture for depth.
# ══════════════════════════════════════════════════════════════════

BLOOD  = (90, 4, 12)
SILVER = (192, 192, 200)
BRONZE = (205, 127, 50)

def _noise_texture(size, opacity: int = 8) -> Image.Image:
    w, h = size
    n = Image.effect_noise((w, h), 24).convert("L")
    alpha = Image.new("L", (w, h), opacity)
    return Image.merge("RGBA", (n, n, n, alpha))

def _hex_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    cx = cy = size / 2
    r = size / 2
    pts = [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    d.polygon(pts, fill=255)
    return mask

def _hex_avatar(avatar_img: Image.Image, diameter: int, ring_color, ring_width: int = 6) -> Image.Image:
    """Hexagonal avatar frame — distinctive alternative to the standard
    circle-crop every rank-card bot uses."""
    avatar_img = avatar_img.convert("RGBA").resize((diameter, diameter), Image.LANCZOS)
    inner_mask = _hex_mask(diameter)
    inner = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    inner.paste(avatar_img, (0, 0), inner_mask)

    ring_size  = diameter + ring_width * 2
    outer_mask = _hex_mask(ring_size)
    ring_layer = Image.new("RGBA", (ring_size, ring_size), (*ring_color, 255))
    ring_layer.putalpha(outer_mask)

    hole_mask = Image.new("L", (ring_size, ring_size), 0)
    hole_mask.paste(inner_mask, (ring_width, ring_width))
    ring_alpha = ring_layer.split()[3]
    ring_layer.putalpha(ImageChops.subtract(ring_alpha, hole_mask))

    final = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    final.paste(ring_layer, (0, 0), ring_layer)
    final.paste(inner, (ring_width, ring_width), inner)
    return final

def _flame_tongue(draw: ImageDraw.ImageDraw, cx: float, cy: float, angle_deg: float, length: float, width: float, color, alpha: int) -> None:
    """Draw one teardrop-shaped 'flame tongue' rooted at (cx, cy), pointing
    outward at angle_deg. Layering several of these at different lengths
    and colors (dark red outer -> orange -> yellow tip) and blurring the
    result is what sells the 'fire' look without needing an animated GIF."""
    ang = math.radians(angle_deg)
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx  # perpendicular unit vector, for the tongue's base width
    tip    = (cx + dx * length, cy + dy * length)
    base_l = (cx + px * width / 2, cy + py * width / 2)
    base_r = (cx - px * width / 2, cy - py * width / 2)
    mid_l  = (cx + dx * length * 0.35 + px * width * 0.6, cy + dy * length * 0.35 + py * width * 0.6)
    mid_r  = (cx + dx * length * 0.35 - px * width * 0.6, cy + dy * length * 0.35 - py * width * 0.6)
    draw.polygon([base_l, mid_l, tip, mid_r, base_r], fill=(*color, alpha))

def _fire_aura(diameter: int, ring_width: int) -> Image.Image:
    """Stylized static flame flicker hugging a premium avatar's ring — short
    tongues (deep red outer layer, orange mid layer, yellow-white inner tip)
    kept tight to the border, then lightly Gaussian-blurred so it reads as
    fire licking the edge rather than a big radiating sunburst. Deterministic
    (no randomness) so re-rendering the same card looks the same every time."""
    pad  = max(int(diameter * 0.16), 14)
    size = diameter + ring_width * 2 + pad * 2
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx = cy = size / 2
    base_r = diameter / 2 + ring_width + 2

    n = 30
    for i in range(n):
        angle = 360 / n * i
        # smooth deterministic variation (harmonics) so tongues differ in
        # length/width without looking like a perfectly uniform ring
        wobble = (math.sin(i * 2.7) + math.sin(i * 1.3) * 0.6 + 1.6) / 3.2
        length = base_r * (0.14 + 0.16 * wobble)
        width  = base_r * (0.11 + 0.05 * ((math.cos(i * 1.9) + 1) / 2))
        sx = cx + math.cos(math.radians(angle)) * base_r
        sy = cy + math.sin(math.radians(angle)) * base_r
        _flame_tongue(draw, sx, sy, angle, length * 1.1,  width * 1.5,  (120, 10, 0),   80)   # outer red
        _flame_tongue(draw, sx, sy, angle, length * 0.8,  width * 1.0,  (255, 90, 10),  120)  # mid orange
        _flame_tongue(draw, sx, sy, angle, length * 0.5,  width * 0.55, (255, 205, 70), 160)  # inner yellow tip

    return layer.filter(ImageFilter.GaussianBlur(2.5))

def _corner_bracket(draw: ImageDraw.ImageDraw, x, y, size, color, flip_x=False, flip_y=False, width=3):

    dx = -1 if flip_x else 1
    dy = -1 if flip_y else 1
    draw.line([(x, y), (x + dx * size, y)], fill=color, width=width)
    draw.line([(x, y), (x, y + dy * size)], fill=color, width=width)

def _diagonal_clip_mask(w: int, h: int, cut: int = 46) -> Image.Image:
    """Card silhouette with the top-right corner sliced off at an angle —
    breaks up the 'plain rounded rectangle' silhouette every card uses."""
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (w - cut, 0), (w, cut), (w, h), (0, h)], fill=255)
    return mask

def _vx_watermark(size, opacity: int = 15) -> Image.Image:
    """Huge, faint 'VX' wordmark bleeding off the top-right — a branding
    fingerprint unique to this bot rather than a generic gradient card."""
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = _font(F_DISPLAY, int(h * 0.9))
    txt = "VX"
    tw = d.textlength(txt, font=f)
    d.text((w - tw * 0.55, -h * 0.22), txt, font=f, fill=(255, 255, 255, opacity))
    return layer.rotate(-8, resample=Image.BICUBIC)

def _segmented_bar(draw: ImageDraw.ImageDraw, x, y, w, h, pct, segments, track_color, fill_color, gap=3):
    """HUD-style tick-segmented bar instead of a plain smooth gradient pill."""
    seg_w  = (w - gap * (segments - 1)) / segments
    filled = max(0.0, min(pct, 1.0)) * segments
    for i in range(segments):
        sx = x + i * (seg_w + gap)
        draw.rectangle([sx, y, sx + seg_w, y + h], fill=track_color)
        amt = max(0.0, min(1.0, filled - i))
        if amt > 0:
            draw.rectangle([sx, y, sx + seg_w * amt, y + h], fill=fill_color)

def _card_base(W: int, H: int, cut: int = 48, blood_xy=None, premium: bool = False) -> Image.Image:
    """Shared background stack for both cards: gradient + blood glow +
    VX watermark + grain texture, clipped to the angled card silhouette.
    `premium=True` swaps the whole palette to gold instead of crimson, so
    a premium card is unmistakably different at a glance, not just the
    avatar ring."""
    bg_top    = GOLD_BG_TOP if premium else BG_TOP
    bg_bottom = GOLD_BG_BTM if premium else BG_BOTTOM
    border    = GOLD_DARK   if premium else DARK_RED
    corner    = GOLD        if premium else CRIMSON
    blood     = GOLD_DARK   if premium else BLOOD

    base = _vertical_gradient((W, H), bg_top, bg_bottom).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    bx, by = blood_xy or (-180, H - 220)
    gd.ellipse([bx, by, bx + 560, by + 460], fill=(*blood, 80))
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, _vx_watermark((W, H)))
    base = Image.alpha_composite(base, _noise_texture((W, H)))
    clip = _diagonal_clip_mask(W, H, cut=cut)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(base, (0, 0), clip)
    draw = ImageDraw.Draw(canvas)
    draw.line([(0, 0), (W - cut, 0)], fill=(*border, 255), width=3)
    draw.line([(W - cut, 0), (W, cut)], fill=(*border, 255), width=3)
    draw.line([(W, cut), (W, H)], fill=(*border, 255), width=3)
    draw.line([(W, H), (0, H)], fill=(*border, 255), width=3)
    draw.line([(0, H), (0, 0)], fill=(*border, 255), width=3)
    _corner_bracket(draw, 16, 16, 24, (*corner, 220))
    _corner_bracket(draw, 16, H - 16, 24, (*corner, 220), flip_y=True)
    return canvas

def _flatten(canvas: Image.Image) -> io.BytesIO:
    out = Image.new("RGB", canvas.size, (8, 4, 5))
    out.paste(canvas, (0, 0), canvas)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf

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
    W, H = 934, 300
    cut  = 50
    accent = GOLD if is_premium else CRIMSON
    canvas = _card_base(W, H, cut=cut, premium=is_premium)
    draw   = ImageDraw.Draw(canvas)

    av = _safe_avatar(avatar_bytes)
    ring_color = accent
    avatar_d = 168
    hexring  = _hex_avatar(av, avatar_d, ring_color, ring_width=6)
    ax, ay = 50, (H - hexring.height) // 2
    if is_premium:
        aura = _fire_aura(avatar_d, ring_width=6)
        aura_pos = (int(ax + hexring.width / 2 - aura.width / 2), int(ay + hexring.height / 2 - aura.height / 2))
        canvas.paste(aura, aura_pos, aura)
    canvas.paste(hexring, (ax, ay), hexring)

    draw = ImageDraw.Draw(canvas)
    text_x = ax + hexring.width + 40
    max_w  = W - text_x - 70

    f_small = _font(F_BOLD, 22)
    f_tiny  = _font(F_REG, 18)
    f_xp    = _font(F_BOLD, 20)

    uname   = username.upper()
    name_y  = 36
    size    = 50
    while text_width(draw, uname, F_DISPLAY, size) > max_w and size > 26:
        size -= 2
    draw_text(draw, (text_x, name_y), uname, F_DISPLAY, size, WHITE)
    draw.rectangle([text_x, name_y + size + 2, text_x + 50, name_y + size + 6], fill=(*accent, 255))

    sub_y = name_y + size + 16
    if is_premium:
        _draw_diamond(draw, text_x + 7, sub_y + 11, 8, GOLD)
        draw.text((text_x + 20, sub_y), "PREMIUM MEMBER", font=f_small, fill=GOLD)
        sub_y += 28

    rl_y = sub_y + 6
    draw.text((text_x, rl_y), "RANK", font=f_tiny, fill=MUTED)
    rank_w = draw.textlength("RANK ", font=f_tiny)
    draw.text((text_x + rank_w, rl_y - 3), f"#{rank}", font=f_small, fill=WHITE)
    lvl_x = text_x + rank_w + draw.textlength(f"#{rank}", font=f_small) + 36
    draw.text((lvl_x, rl_y), "LEVEL", font=f_tiny, fill=MUTED)
    lvl_w = draw.textlength("LEVEL ", font=f_tiny)
    draw.text((lvl_x + lvl_w, rl_y - 3), str(level), font=f_small, fill=(*accent, 255))

    bar_y = rl_y + 42
    bar_w = W - text_x - 90
    bar_h = 22
    _segmented_bar(draw, text_x, bar_y, bar_w, bar_h, cur_xp / max(need_xp, 1), 20, (35, 16, 18), accent, gap=3)

    xp_text = f"{cur_xp:,} / {need_xp:,} XP"
    xp_w = draw.textlength(xp_text, font=f_xp)
    draw.text((text_x + bar_w - xp_w, bar_y - 26), xp_text, font=f_xp, fill=WHITE)


    footer = f"TOTAL XP {total_xp:,}   //   MESSAGES {messages:,}"
    draw.text((text_x, bar_y + bar_h + 16), footer, font=f_tiny, fill=MUTED)

    _watermark(draw, canvas.size)
    return _flatten(canvas)

# ══════════════════════════════════════════════════════════════════
# LEVEL-UP CARD — dipakai di notifikasi level up otomatis
# ══════════════════════════════════════════════════════════════════

def render_levelup_card(avatar_bytes: bytes, username: str, old_level: int, new_level: int, is_premium: bool = False, role_names: list | None = None) -> io.BytesIO:
    W, H = 934, 282
    bg_top    = GOLD_BG_TOP if is_premium else (18, 4, 6)
    bg_bottom = GOLD_BG_BTM if is_premium else (48, 6, 10)
    accent    = GOLD if is_premium else CRIMSON
    border    = GOLD_DARK if is_premium else DARK_RED
    card = _vertical_gradient((W, H), bg_top, bg_bottom).convert("RGBA")

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = 160, H // 2
    for r, a in [(230, 26), (170, 40), (110, 60)]:
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*accent, a))
    card = Image.alpha_composite(card, glow)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=22, outline=(*border, 255), width=3)

    av = _safe_avatar(avatar_bytes)
    ring_color = (*accent, 255)
    avatar_d = 176
    avatar_ring = _circle_avatar(av, avatar_d, ring_color, ring_width=7)
    ax, ay = 60, (H - avatar_ring.height) // 2
    if is_premium:
        aura = _fire_aura(avatar_d, ring_width=7)
        aura_pos = (int(ax + avatar_ring.width / 2 - aura.width / 2), int(ay + avatar_ring.height / 2 - aura.height / 2))
        card.paste(aura, aura_pos, aura)
    card.paste(avatar_ring, (ax, ay), avatar_ring)

    draw = ImageDraw.Draw(card)
    text_x = ax + avatar_ring.width + 50
    max_w  = W - text_x - 40

    f_tag = _font(F_BOLD, 26)
    tag_txt = "LEVEL UP  ·  PREMIUM" if is_premium else "LEVEL UP"
    draw.text((text_x, 46), tag_txt, font=f_tag, fill=(*accent, 255))

    # Level progression, e.g. "LEVEL 6  ➔  LEVEL 7" — auto-shrinks to fit
    prog_txt = f"LEVEL {old_level}  \u2192  LEVEL {new_level}"
    size = 64
    while text_width(draw, prog_txt, F_DISPLAY, size) > max_w and size > 30:
        size -= 2
    draw_text(draw, (text_x, 82), prog_txt, F_DISPLAY, size, WHITE)

    sub  = f"{username} reached a new level!"
    ssize = 30
    while text_width(draw, sub, F_BOLD, ssize) > max_w and ssize > 16:
        ssize -= 2
    draw_text(draw, (text_x, 190), sub, F_BOLD, ssize, MUTED)

    if role_names:
        role_txt = "\U0001F381 Unlocked: " + ", ".join(role_names)  # 🎁
        rsize = 22
        while text_width(draw, role_txt, F_BOLD, rsize) > max_w and rsize > 14:
            rsize -= 2
        draw_text(draw, (text_x, 226), role_txt, F_BOLD, rsize, GOLD)

    draw = ImageDraw.Draw(card)
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

# ══════════════════════════════════════════════════════════════════
# LEADERBOARD CARD — dipakai di command `leaderboard` / `/leaderboard`
# ══════════════════════════════════════════════════════════════════

def _truncate(draw: ImageDraw.ImageDraw, text: str, path: str, size: int, max_w: int) -> str:
    if text_width(draw, text, path, size) <= max_w:
        return text
    while text and text_width(draw, text + "…", path, size) > max_w:
        text = text[:-1]
    return text + "…" if text else "…"

def render_leaderboard_card(guild_name: str, entries: list) -> io.BytesIO:
    """entries: list of dict {rank, avatar_bytes, name, level, xp} — urut dari #1,
    maksimal ditampilin 10 baris."""
    entries  = entries[:10]
    W        = 800
    row_h    = 66
    header_h = 100
    cut      = 44
    H = header_h + row_h * max(len(entries), 1) + 30

    canvas = _card_base(W, H, cut=cut, blood_xy=(-180, -180))
    draw   = ImageDraw.Draw(canvas)

    f_meta = _font(F_REG, 15)
    f_rank = _font(F_DISPLAY, 24)

    title = _truncate(draw, "XP LEADERBOARD", F_DISPLAY, 34, W - 64)
    draw_text(draw, (32, 24), title, F_DISPLAY, 34, WHITE)
    draw.rectangle([33, 62, 90, 65], fill=(*CRIMSON, 255))
    sub = _truncate(draw, guild_name.upper(), F_REG, 17, W - 64)
    draw_text(draw, (32, 72), sub, F_REG, 17, MUTED, bold=False)

    if not entries:
        f_empty = _font(F_REG, 22)
        draw.text((32, header_h + 10), "No XP data yet.", font=f_empty, fill=MUTED)

    rank_colors = {1: GOLD, 2: SILVER, 3: BRONZE}
    y = header_h
    name_max_w = W - 86 - 62 - 16 - 130
    for e in entries:
        rank   = e["rank"]
        accent = rank_colors.get(rank, CRIMSON)
        if rank <= 3:
            draw.rectangle([14, y + 3, W - 14, y + row_h - 3], fill=(*accent, 22))
            draw.rectangle([14, y + 3, 18, y + row_h - 3], fill=(*accent, 255))

        rank_str = f"#{rank}"
        rw = draw.textlength(rank_str, font=f_rank)
        draw.text((56 - rw / 2, y + row_h / 2 - 14), rank_str, font=f_rank, fill=accent if rank <= 3 else MUTED)

        av = _safe_avatar(e["avatar_bytes"])
        ring_color = accent if rank <= 3 else CRIMSON
        avatar_d = 46
        hexring  = _hex_avatar(av, avatar_d, ring_color, ring_width=3)
        ax = 86
        ay = y + (row_h - hexring.height) // 2
        canvas.paste(hexring, (ax, ay), hexring)

        name_x   = ax + hexring.width + 16
        name_txt = _truncate(draw, e["name"], F_BOLD, 21, name_max_w)
        draw_text(draw, (name_x, y + 9), name_txt, F_BOLD, 21, WHITE)
        draw.text((name_x, y + 35), f"LVL {e['level']}", font=f_meta, fill=MUTED)

        xp_str = f"{e['xp']:,} XP"
        xp_w = text_width(draw, xp_str, F_BOLD, 21)
        draw_text(draw, (W - 32 - xp_w - cut * 0.3, y + row_h / 2 - 11), xp_str, F_BOLD, 21, WHITE)

        y += row_h

    draw = ImageDraw.Draw(canvas)
    _watermark(draw, canvas.size)
    return _flatten(canvas)
