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

    f_small = _font(F_BOLD, 24)
    f_tiny  = _font(F_REG, 20)
    f_xp    = _font(F_BOLD, 22)

    name_y = 40
    uname  = username.upper()
    max_w  = W - text_x - 56
    size   = 52
    while text_width(draw, uname, F_DISPLAY, size) > max_w and size > 26:
        size -= 2
    draw_text(draw, (text_x, name_y), uname, F_DISPLAY, size, WHITE)

    sub_y = name_y + 60
    if is_premium:
        _draw_diamond(draw, text_x + 8, sub_y + 15, 9, GOLD)
        draw.text((text_x + 24, sub_y), "PREMIUM MEMBER", font=f_small, fill=GOLD)
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

def render_levelup_card(avatar_bytes: bytes, username: str, old_level: int, new_level: int, is_premium: bool = False, role_names: list | None = None) -> io.BytesIO:
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
    max_w  = W - text_x - 40

    f_tag = _font(F_BOLD, 26)
    draw.text((text_x, 46), "LEVEL UP", font=f_tag, fill=(*CRIMSON, 255))

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

SILVER = (192, 192, 200)
BRONZE = (205, 127, 50)

def _truncate(draw: ImageDraw.ImageDraw, text: str, path: str, size: int, max_w: int) -> str:
    if text_width(draw, text, path, size) <= max_w:
        return text
    while text and text_width(draw, text + "…", path, size) > max_w:
        text = text[:-1]
    return text + "…" if text else "…"

def render_leaderboard_card(guild_name: str, entries: list) -> io.BytesIO:
    """entries: list of dict {rank, avatar_bytes, name, level, xp} — urut dari #1,
    maksimal ditampilin 10 baris."""
    entries = entries[:10]
    W = 760
    row_h = 68
    header_h = 96
    H = header_h + row_h * max(len(entries), 1) + 24

    card = _vertical_gradient((W, H), BG_TOP, BG_BOTTOM).convert("RGBA")
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=22, outline=(*DARK_RED, 255), width=3)

    f_meta  = _font(F_REG, 16)
    f_rank  = _font(F_DISPLAY, 26)

    title = _truncate(draw, "XP LEADERBOARD", F_DISPLAY, 36, W - 60)
    draw_text(draw, (30, 22), title, F_DISPLAY, 36, WHITE)
    sub = _truncate(draw, guild_name, F_REG, 18, W - 60)
    draw_text(draw, (30, 64), sub, F_REG, 18, MUTED, bold=False)

    if not entries:
        f_empty = _font(F_REG, 22)
        draw.text((30, header_h + 10), "Belum ada data XP.", font=f_empty, fill=MUTED)

    rank_colors = {1: GOLD, 2: SILVER, 3: BRONZE}
    y = header_h
    name_max_w = W - 90 - 66 - 18 - 140  # sisa ruang setelah avatar & sebelum angka XP
    for e in entries:
        rank   = e["rank"]
        accent = rank_colors.get(rank, CRIMSON)
        if rank <= 3:
            draw.rounded_rectangle([16, y + 4, W - 16, y + row_h - 4], radius=14, fill=(*accent, 26))

        rank_str = f"#{rank}"
        rw = draw.textlength(rank_str, font=f_rank)
        draw.text((60 - rw / 2, y + row_h / 2 - 16), rank_str, font=f_rank, fill=accent if rank <= 3 else MUTED)

        av = _safe_avatar(e["avatar_bytes"])
        avatar_d = 48
        ring_color = (*accent, 255) if rank <= 3 else (*CRIMSON, 180)
        ring = _circle_avatar(av, avatar_d, ring_color, ring_width=3)
        ax = 90
        ay = y + (row_h - ring.height) // 2
        card.paste(ring, (ax, ay), ring)

        name_x = ax + ring.width + 18
        name_txt = _truncate(draw, e["name"], F_BOLD, 22, name_max_w)
        draw_text(draw, (name_x, y + 10), name_txt, F_BOLD, 22, WHITE)
        draw.text((name_x, y + 38), f"Level {e['level']}", font=f_meta, fill=MUTED)

        xp_str = f"{e['xp']:,} XP"
        xp_w = text_width(draw, xp_str, F_BOLD, 22)
        draw_text(draw, (W - 30 - xp_w, y + row_h / 2 - 12), xp_str, F_BOLD, 22, WHITE)

        y += row_h

    draw = ImageDraw.Draw(card)
    _watermark(draw, card.size)

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
