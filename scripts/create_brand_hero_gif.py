from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "demo" / "gifs"
OUT_PATH = OUT_DIR / "mailmind_brand_hero.gif"
PREVIEW_PATH = OUT_DIR / "mailmind_brand_hero_preview.png"
KEYFRAMES_PATH = OUT_DIR / "mailmind_brand_hero_keyframes.png"

W, H = 800, 451
SCALE = 2
FRAMES = 88
DURATION_MS = 84


INK = (13, 25, 39)
MINT = (52, 132, 121)
SOFT_MINT = (220, 244, 239)
PAPER = (248, 250, 247)
LINE = (190, 208, 205)
TEXT_MUTED = (78, 98, 110)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size * SCALE)
    return ImageFont.load_default()


FONT_TITLE = font(48, True)
FONT_SUBTITLE = font(16)
FONT_CARD = font(14, True)
FONT_SMALL = font(11)
FONT_MICRO = font(10)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease_out(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def window(t: float, start: float, end: float) -> float:
    return ease_in_out((t - start) / (end - start))


def pulse_window(t: float, start: float, peak: float, end: float) -> float:
    return window(t, start, peak) * (1 - window(t, peak, end))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t)


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], max(0, min(255, alpha))


def draw_background(draw: ImageDraw.ImageDraw) -> None:
    top = (252, 253, 251)
    bottom = (235, 244, 242)
    for y in range(H * SCALE):
        r = y / (H * SCALE - 1)
        color = tuple(int(lerp(top[i], bottom[i], r)) for i in range(3))
        draw.line((0, y, W * SCALE, y), fill=color + (255,))
    spacing = 48 * SCALE
    for x in range(0, W * SCALE + spacing, spacing):
        draw.line((x, 0, x, H * SCALE), fill=(20, 44, 58, 10), width=1)
    for y in range(0, H * SCALE + spacing, spacing):
        draw.line((0, y, W * SCALE, y), fill=(20, 44, 58, 8), width=1)


def composite_layer(canvas: Image.Image, layer: Image.Image) -> Image.Image:
    return Image.alpha_composite(canvas, layer)


def rounded(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(tuple(int(v) for v in box), radius=radius * SCALE, fill=fill, outline=outline, width=width * SCALE)


def draw_logo(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, alpha: int = 255) -> None:
    if alpha <= 3:
        return
    s = size * SCALE
    x = cx * SCALE - s / 2
    y = cy * SCALE - s / 2
    a = max(0, min(255, alpha))
    dark = rgba(INK, a)
    mint = (232, 248, 244, a)
    white = (255, 255, 255, a)

    rounded(draw, (x, y, x + s, y + s), int(size * 0.2), dark)

    def p(px: float, py: float) -> tuple[int, int]:
        return int(x + px * s), int(y + py * s)

    draw.polygon([p(0.23, 0.25), p(0.77, 0.25), p(0.50, 0.51)], fill=mint)
    draw.line([p(0.23, 0.25), p(0.50, 0.53), p(0.77, 0.25)], fill=dark, width=max(1, int(size * 0.065 * SCALE)), joint="curve")
    draw.polygon(
        [
            p(0.23, 0.27),
            p(0.50, 0.53),
            p(0.77, 0.27),
            p(0.77, 0.74),
            p(0.65, 0.74),
            p(0.65, 0.49),
            p(0.50, 0.66),
            p(0.35, 0.49),
            p(0.35, 0.74),
            p(0.23, 0.74),
        ],
        fill=white,
    )
    draw.line([p(0.23, 0.27), p(0.50, 0.53), p(0.77, 0.27)], fill=dark, width=max(1, int(size * 0.052 * SCALE)), joint="curve")


def draw_card_shadow(canvas: Image.Image, box: tuple[float, float, float, float], radius: int, alpha: int) -> Image.Image:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    dx = 0
    dy = 10 * SCALE
    rounded(sd, (box[0] * SCALE + dx, box[1] * SCALE + dy, box[2] * SCALE + dx, box[3] * SCALE + dy), radius, (13, 25, 39, alpha))
    return composite_layer(canvas, shadow.filter(ImageFilter.GaussianBlur(12 * SCALE)))


def draw_email_card(canvas: Image.Image, x: float, y: float, label: str, alpha: int, scale: float = 1.0) -> Image.Image:
    if alpha <= 3:
        return canvas
    w, h = 148 * scale, 44 * scale
    box = (x, y, x + w, y + h)
    canvas = draw_card_shadow(canvas, box, 14, int(alpha * 0.08))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rounded(d, (box[0] * SCALE, box[1] * SCALE, box[2] * SCALE, box[3] * SCALE), 14, (255, 255, 255, int(alpha * 0.92)), (184, 205, 201, int(alpha * 0.75)))
    ix, iy = (x + 13) * SCALE, (y + 12) * SCALE
    d.rounded_rectangle((ix, iy, ix + 20 * SCALE, iy + 20 * SCALE), radius=6 * SCALE, fill=(220, 244, 239, alpha))
    d.line((ix + 5 * SCALE, iy + 7 * SCALE, ix + 10 * SCALE, iy + 12 * SCALE, ix + 15 * SCALE, iy + 7 * SCALE), fill=rgba(MINT, alpha), width=2 * SCALE)
    d.text(((x + 43) * SCALE, (y + 10) * SCALE), label, font=FONT_CARD, fill=rgba(INK, alpha))
    d.line(((x + 43) * SCALE, (y + 30) * SCALE, (x + 118) * SCALE, (y + 30) * SCALE), fill=(108, 132, 142, int(alpha * 0.55)), width=1 * SCALE)
    return composite_layer(canvas, layer)


def draw_output_card(canvas: Image.Image, x: float, y: float, title: str, body: str, alpha: int, accent: tuple[int, int, int]) -> Image.Image:
    if alpha <= 3:
        return canvas
    w, h = 174, 58
    box = (x, y, x + w, y + h)
    canvas = draw_card_shadow(canvas, box, 15, int(alpha * 0.07))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rounded(d, (box[0] * SCALE, box[1] * SCALE, box[2] * SCALE, box[3] * SCALE), 15, (255, 255, 255, int(alpha * 0.94)), (178, 202, 198, int(alpha * 0.82)))
    d.rounded_rectangle(((x + 13) * SCALE, (y + 14) * SCALE, (x + 36) * SCALE, (y + 37) * SCALE), radius=7 * SCALE, fill=accent + (int(alpha * 0.22),))
    d.ellipse(((x + 20) * SCALE, (y + 21) * SCALE, (x + 29) * SCALE, (y + 30) * SCALE), fill=accent + (alpha,))
    d.text(((x + 47) * SCALE, (y + 10) * SCALE), title, font=FONT_CARD, fill=rgba(INK, alpha))
    d.text(((x + 47) * SCALE, (y + 31) * SCALE), body, font=FONT_SMALL, fill=rgba(TEXT_MUTED, int(alpha * 0.9)))
    return composite_layer(canvas, layer)


def draw_processing_ring(draw: ImageDraw.ImageDraw, t: float, cx: float, cy: float, size: float, alpha: int) -> None:
    if alpha <= 3:
        return
    sweep = 40 + 260 * ease_in_out((math.sin(t * math.tau * 1.7) + 1) / 2)
    bbox = (
        (cx - size / 2) * SCALE,
        (cy - size / 2) * SCALE,
        (cx + size / 2) * SCALE,
        (cy + size / 2) * SCALE,
    )
    draw.arc(bbox, start=-90, end=-90 + sweep, fill=(72, 180, 164, alpha), width=3 * SCALE)


def draw_status_pill(canvas: Image.Image, text: str, x: float, y: float, alpha: int) -> Image.Image:
    if alpha <= 3:
        return canvas
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    tb = d.textbbox((0, 0), text, font=FONT_SMALL)
    w = (tb[2] - tb[0]) / SCALE + 36
    h = 28
    rounded(d, (x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE), 14, (232, 248, 244, int(alpha * 0.95)), (162, 205, 197, int(alpha * 0.85)))
    d.ellipse(((x + 12) * SCALE, (y + 10) * SCALE, (x + 18) * SCALE, (y + 16) * SCALE), fill=(52, 132, 121, alpha))
    d.text(((x + 25) * SCALE, (y + 7) * SCALE), text, font=FONT_SMALL, fill=rgba(INK, alpha))
    return composite_layer(canvas, layer)


def draw_text_center(draw: ImageDraw.ImageDraw, text: str, y: float, font_obj, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    draw.text(((W * SCALE - (bbox[2] - bbox[0])) / 2, y * SCALE), text, font=font_obj, fill=fill)


def draw_frame(i: int) -> Image.Image:
    t = i / (FRAMES - 1)
    canvas = Image.new("RGBA", (W * SCALE, H * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas, "RGBA")
    draw_background(d)

    # Soft center stage.
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.ellipse((170 * SCALE, 42 * SCALE, 635 * SCALE, 388 * SCALE), fill=(89, 155, 145, 24))
    canvas = composite_layer(canvas, glow.filter(ImageFilter.GaussianBlur(34 * SCALE)))

    # Input emails arrive from left, then shrink into the hub.
    email_specs = [
        ("deadline", 0.10, 132),
        ("reply", 0.18, 190),
        ("attachment", 0.26, 248),
    ]
    for label, start, y in email_specs:
        enter = ease_out((t - start) / 0.18)
        absorb = ease_in_out((t - 0.37) / 0.17)
        base_x = lerp(-175, 144, enter)
        x = lerp(base_x, 345, absorb)
        card_y = lerp(y, 190, absorb)
        scale = lerp(1.0, 0.35, absorb)
        alpha = int(245 * enter * (1 - absorb))
        canvas = draw_email_card(canvas, x, card_y, label, alpha, scale)

    # Logo hub.
    logo_in = ease_out((t - 0.05) / 0.18)
    process = pulse_window(t, 0.34, 0.52, 0.76)
    logo_size = 112 + 6 * math.sin(process * math.pi)
    canvas = draw_card_shadow(canvas, (344 - logo_size / 2, 186 - logo_size / 2, 344 + logo_size / 2, 186 + logo_size / 2), 23, int(42 * logo_in))
    d = ImageDraw.Draw(canvas, "RGBA")
    draw_logo(d, 344, 186, logo_size, int(255 * logo_in))
    draw_processing_ring(d, t, 344, 186, logo_size + 22, int(210 * process))
    canvas = draw_status_pill(canvas, "Local-first processing", 278, 268, int(230 * process))

    # Output capability cards.
    outputs = [
        ("Tasks", "Extract deadlines", (505, 120), (52, 132, 121), 0.50),
        ("AI Search", "Grounded answers", (520, 190), (72, 109, 201), 0.57),
        ("PII Guard", "Redact before LLM", (505, 260), (127, 94, 176), 0.64),
    ]
    for title, body, (x, y), accent, start in outputs:
        show = ease_out((t - start) / 0.18)
        slide_x = lerp(x + 34, x, show)
        canvas = draw_output_card(canvas, slide_x, y, title, body, int(245 * show), accent)

    # Brand lockup.
    d = ImageDraw.Draw(canvas, "RGBA")
    title_in = ease_out((t - 0.70) / 0.16)
    title_y = lerp(348, 326, title_in)
    if title_in > 0.02:
        draw_text_center(d, "MailMind", title_y, FONT_TITLE, rgba(INK, int(255 * title_in)))
    sub_in = ease_out((t - 0.78) / 0.14)
    if sub_in > 0.02:
        draw_text_center(d, "Local-first Gmail intelligence", 389, FONT_SUBTITLE, rgba(TEXT_MUTED, int(225 * sub_in)))

    micro_in = ease_out((t - 0.82) / 0.13)
    if micro_in > 0.02:
        micro = "Created for MailMind"
        mb = d.textbbox((0, 0), micro, font=FONT_MICRO)
        d.text((W * SCALE - (mb[2] - mb[0]) - 22 * SCALE, H * SCALE - 25 * SCALE), micro, font=FONT_MICRO, fill=(92, 105, 115, int(150 * micro_in)))

    return canvas.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")


def save_keyframes() -> None:
    indices = [0, 16, 30, 44, 62, 87]
    frames = [draw_frame(idx).resize((400, 226), Image.Resampling.LANCZOS) for idx in indices]
    canvas = Image.new("RGB", (1200, 452), "white")
    for idx, frame in enumerate(frames):
        canvas.paste(frame, ((idx % 3) * 400, (idx // 3) * 226))
    canvas.save(KEYFRAMES_PATH)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = [draw_frame(i) for i in range(FRAMES)]
    frames[-1].save(PREVIEW_PATH)
    save_keyframes()
    gif_frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=96) for frame in frames]
    gif_frames[0].save(
        OUT_PATH,
        save_all=True,
        append_images=gif_frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"{OUT_PATH.relative_to(ROOT)} ({OUT_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    print(PREVIEW_PATH.relative_to(ROOT))
    print(KEYFRAMES_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
