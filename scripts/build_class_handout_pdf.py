"""Build the one-page class handout PDF from current submission figures."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = Path.home() / "Documents" / "vault" / "Projects" / "F3 Data Challenge"

PAGE_W, PAGE_H = 3300, 2550
MARGIN = 110
GAP = 65
HEADER_H = 265
COL_W = (PAGE_W - 2 * MARGIN - GAP) // 2
ROW_H = (PAGE_H - MARGIN - HEADER_H - GAP - 70) // 2
KEY_SCALE = 0.70

HANDOUT_IMAGES = [
    {
        "asset": "stanislaus_site_1_report_zone_map.png",
        "title": "Stanislaus 1",
        "caption": "A visually rich public-site example. Interpret cautiously because crop context is unverified.",
    },
    {
        "asset": "spatial_zone_maps.png",
        "title": "All six sites",
        "caption": "Same pipeline across every challenge boundary. Public sites are context-limited.",
    },
    {
        "asset": "partner_site_1_report_zone_map.png",
        "title": "Partner orchard",
        "caption": "Clearest orchard-specific example. Scout first zones are field-worklist starts.",
    },
    {
        "asset": "color_key.png",
        "title": "How to read the colors",
        "caption": "The map ranks where to look first. It does not diagnose cause.",
        "is_key": True,
    },
]

EXTRA_HANDOUT_ASSETS = [
    "partner_site_1_canopy_priority_overlay.png",
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    line_gap: int = 8,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    line_height = draw.textbbox((0, 0), "Ag", font=font)[3] + line_gap
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height
    return y


def create_color_key(path: Path) -> None:
    key_w, key_h = 1500, 1000
    img = Image.new("RGB", (key_w, key_h), "#ffffff")
    draw = ImageDraw.Draw(img)
    title_font = load_font(58, bold=True)
    label_font = load_font(39, bold=True)
    text_font = load_font(33)
    draw.text((70, 56), "Scouting priority color key", fill="#1f2933", font=title_font)

    rows = [
        ("#B42318", "Scout first", "Walk here first."),
        ("#F79009", "Monitor", "Check if there is time."),
        ("#A6C8A0", "Stable", "No priority from this map alone."),
        ("#1A7F37", "Strong reference", "Compare against this area."),
    ]
    y = 185
    for color, label, meaning in rows:
        draw.rounded_rectangle((80, y, 210, y + 88), radius=18, fill=color, outline="#243b53", width=3)
        draw.text((245, y - 2), label, fill="#1f2933", font=label_font)
        draw.text((245, y + 45), meaning, fill="#334e68", font=text_font)
        y += 142

    draw.line((75, 800, key_w - 75, 800), fill="#bcccdc", width=4)
    draw_wrapped(
        draw,
        "Main point: this is a field worklist. It shows where to scout first, not what caused the difference.",
        (80, 830),
        text_font,
        "#1f2933",
        key_w - 160,
        10,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def copy_handout_assets(figures_dir: Path, assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)
    for existing_png in assets_dir.glob("*.png"):
        existing_png.unlink()
    asset_names = [
        item["asset"]
        for item in HANDOUT_IMAGES
        if not item.get("is_key")
    ] + EXTRA_HANDOUT_ASSETS
    for asset_name in asset_names:
        src = figures_dir / asset_name
        if not src.exists():
            raise FileNotFoundError(f"Missing handout source image: {src}")
        shutil.copy2(src, assets_dir / asset_name)
    create_color_key(assets_dir / "color_key.png")


def paste_image_fit(page: Image.Image, img_path: Path, box: tuple[int, int, int, int], is_key: bool) -> None:
    img = Image.open(img_path).convert("RGB")
    x0, y0, x1, y1 = box
    max_w = x1 - x0
    max_h = y1 - y0
    if is_key:
        max_w = int(max_w * KEY_SCALE)
        max_h = int(max_h * KEY_SCALE)
    scale = min(max_w / img.width, max_h / img.height)
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    paste_x = x0 + ((x1 - x0) - new_size[0]) // 2
    paste_y = y0 + ((y1 - y0) - new_size[1]) // 2
    page.paste(img, (paste_x, paste_y))


def build_pdf(assets_dir: Path, output_path: Path) -> None:
    page = Image.new("RGB", (PAGE_W, PAGE_H), "#f7f9fb")
    draw = ImageDraw.Draw(page)
    title_font = load_font(82, bold=True)
    subtitle_font = load_font(39)
    card_title_font = load_font(42, bold=True)
    caption_font = load_font(28)

    draw.text((MARGIN, 62), "Orchard Scouting Maps", fill="#102a43", font=title_font)
    draw.text(
        (MARGIN, 165),
        "Satellite imagery cannot tell a grower what is wrong. It can show where to scout first.",
        fill="#334e68",
        font=subtitle_font,
    )

    positions = [
        (MARGIN, HEADER_H, MARGIN + COL_W, HEADER_H + ROW_H),
        (MARGIN + COL_W + GAP, HEADER_H, MARGIN + 2 * COL_W + GAP, HEADER_H + ROW_H),
        (MARGIN, HEADER_H + ROW_H + GAP, MARGIN + COL_W, HEADER_H + 2 * ROW_H + GAP),
        (
            MARGIN + COL_W + GAP,
            HEADER_H + ROW_H + GAP,
            MARGIN + 2 * COL_W + GAP,
            HEADER_H + 2 * ROW_H + GAP,
        ),
    ]

    for item, (x0, y0, x1, y1) in zip(HANDOUT_IMAGES, positions):
        draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill="#ffffff", outline="#cbd5e1", width=3)
        draw.text((x0 + 28, y0 + 22), item["title"], fill="#102a43", font=card_title_font)
        image_box = (x0 + 28, y0 + 90, x1 - 28, y1 - 94)
        paste_image_fit(page, assets_dir / item["asset"], image_box, bool(item.get("is_key")))
        draw_wrapped(
            draw,
            item["caption"],
            (x0 + 28, y1 - 78),
            caption_font,
            "#334e68",
            x1 - x0 - 56,
            6,
        )

    draw.text(
        (MARGIN, PAGE_H - 62),
        "Persistent Orchard Underperformance Mapper | F3 Innovate Data Challenge #2",
        fill="#627d98",
        font=load_font(27),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.save(output_path, "PDF", resolution=300.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=ROOT / "submission" / "figures",
        help="Source submission figures directory.",
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=DEFAULT_VAULT_DIR,
        help="Obsidian F3 project folder.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    speech_dir = args.vault_dir / "04 Speech Materials"
    assets_dir = speech_dir / "Handout Assets"
    output_path = speech_dir / "F3 Class Handout - Print.pdf"
    copy_handout_assets(args.figures_dir, assets_dir)
    build_pdf(assets_dir, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
