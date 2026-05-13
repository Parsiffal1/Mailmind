from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "docs" / "demo" / "screenshots"
GIF_DIR = ROOT / "docs" / "demo" / "gifs"
OUTPUT_SIZE = (1200, 675)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_LABEL = _font(24, bold=True)
FONT_SMALL = _font(18)


def load_screenshot(name: str) -> Image.Image:
    path = SCREENSHOT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing screenshot: {path}")
    return Image.open(path).convert("RGB")


def crop_cover(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)
    width = right - left
    height = bottom - top
    target_ratio = OUTPUT_SIZE[0] / OUTPUT_SIZE[1]
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        delta = (width - new_width) // 2
        left += delta
        right = left + new_width
    else:
        new_height = int(width / target_ratio)
        delta = (height - new_height) // 2
        top += delta
        bottom = top + new_height

    return image.crop((left, top, right, bottom)).resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)


def crossfade(a: Image.Image, b: Image.Image, steps: int) -> list[Image.Image]:
    return [Image.blend(a, b, index / (steps - 1)) for index in range(steps)]


def add_badge(image: Image.Image, title: str, subtitle: str | None = None) -> Image.Image:
    canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    padding_x = 26
    padding_y = 20
    title_box = draw.textbbox((0, 0), title, font=FONT_LABEL)
    subtitle_box = draw.textbbox((0, 0), subtitle or "", font=FONT_SMALL)
    width = max(title_box[2], subtitle_box[2]) + padding_x * 2
    height = 62 if subtitle is None else 92
    x = 28
    y = 28

    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=20,
        fill=(10, 22, 38, 220),
        outline=(178, 214, 205, 140),
        width=2,
    )
    draw.text((x + padding_x, y + 16), title, font=FONT_LABEL, fill=(246, 250, 255, 255))
    if subtitle:
        draw.text((x + padding_x, y + 52), subtitle, font=FONT_SMALL, fill=(198, 212, 227, 255))

    return Image.alpha_composite(canvas, overlay).convert("P", palette=Image.Palette.ADAPTIVE)


def save_gif(path: Path, frames: list[Image.Image], duration: int = 110) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )


def make_hero_ai_search() -> Path:
    overview = load_screenshot("01_tasks_overview.png")
    answer = load_screenshot("02_ai_search_answer.png")

    frame_a = crop_cover(overview, (110, 0, 1600, 840))
    frame_b = crop_cover(answer, (110, 0, 1600, 840))
    frame_c = crop_cover(answer, (120, 70, 1600, 800))

    frames: list[Image.Image] = []
    frames.extend([add_badge(frame_a, "MailMind command center", "Sample Gmail data only")] * 8)
    frames.extend(add_badge(frame, "Ask anything with AI", "Email bodies + PDF attachments") for frame in crossfade(frame_a, frame_b, 10))
    frames.extend([add_badge(frame_b, "Grounded AI answer", "Sources stay visible beside the response")] * 16)
    frames.extend(add_badge(frame, "Hybrid RAG retrieval", "BM25 + vector search + reranking") for frame in crossfade(frame_b, frame_c, 10))
    frames.extend([add_badge(frame_c, "Ready for a GitHub README", "Synthetic demo, no real inbox content")] * 16)

    out = GIF_DIR / "hero_ai_search.gif"
    save_gif(out, frames)
    return out


def make_documents() -> Path:
    documents = load_screenshot("03_indexed_sources.png")
    settings = load_screenshot("05_settings_privacy_rag.png")

    frame_a = crop_cover(documents, (120, 120, 1580, 920))
    frame_b = crop_cover(settings, (150, 190, 1580, 960))

    frames: list[Image.Image] = []
    frames.extend([add_badge(frame_a, "Indexed sources", "PDF attachments and email bodies") for _ in range(16)])
    frames.extend(add_badge(frame, "Configurable RAG sources", "Choose email, PDFs, or both") for frame in crossfade(frame_a, frame_b, 12))
    frames.extend([add_badge(frame_b, "Local-first AI search", "BGE-M3 embeddings stored locally") for _ in range(16)])

    out = GIF_DIR / "documents_and_settings.gif"
    save_gif(out, frames)
    return out


def make_privacy() -> Path:
    settings = load_screenshot("04_settings.png")
    privacy = load_screenshot("05_settings_privacy_rag.png")

    frame_a = crop_cover(settings, (120, 120, 1580, 920))
    frame_b = crop_cover(privacy, (120, 220, 1580, 980))

    frames: list[Image.Image] = []
    frames.extend([add_badge(frame_a, "Settings for local control", "Scheduler, Telegram, LLM, and privacy") for _ in range(14)])
    frames.extend(add_badge(frame, "PII Guard", "Off or placeholder rehydration mode") for frame in crossfade(frame_a, frame_b, 12))
    frames.extend([add_badge(frame_b, "User-controlled privacy", "Claude can receive original text or placeholders") for _ in range(16)])

    out = GIF_DIR / "privacy_settings.gif"
    save_gif(out, frames)
    return out


def main() -> None:
    outputs = [make_hero_ai_search(), make_documents(), make_privacy()]
    for path in outputs:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"{path.relative_to(ROOT)} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
