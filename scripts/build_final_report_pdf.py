"""
Build a concise PDF technical report for the F3 orchard underperformance submission.

The report generator uses only local outputs already produced by
build_spatial_zones.py. It is intentionally simple and reproducible so the
PDF can be rebuilt without a desktop publishing tool.
"""

from __future__ import annotations

import argparse
import csv
import textwrap
from collections.abc import Iterable
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch


plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 9.4,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

REPORT_TITLE = "Canopy Signal To Scouting Action"
REPORT_OVERVIEW_TITLE = "Report Overview"
PRODUCT_NAME = "Persistent Orchard Underperformance Mapper"
CHALLENGE_LINE = "F3 Innovate Data Challenge #2 | Satellite-Based Orchard Stress Mapping"
GITHUB_LINK = "https://github.com/tienonic/f3innovate-project-submission"
LIVE_MAP_LINK = "https://f3-orchard-stress-web.vercel.app"
AUTHOR_NAME = "Nicholas Melnichenko"
AUTHOR_AFFILIATION = "UC Davis"
AUTHOR_CONTACT = "think@ucdavis.edu"
SUBMISSION_LABEL = "Final Technical Report"
SUBMISSION_DATE = "May 2026"
THESIS_TEXT = (
    "This submission is a scouting-priority aid, not a diagnosis tool. It uses Sentinel-2 vegetation evidence to find canopy areas that repeatedly underperform relative to the site's own eligible-canopy baseline, then turns that signal into maps, coordinates, and follow-up data."
)
THESIS_TEXT_2 = (
    "Canopy data can work technically and still fail in practice if it is not trusted enough, cheap enough in staff time, clearly accountable, or tied to real operations. The goal is not to make a dramatic map; it is to make a conservative, auditable, and useful guide for where to look first before any cause is assigned."
)
BODY_FONT = "Arial"
HEADING_FONT = "Arial"
PAGE_SIZE = (8.5, 11)

PAPER_COLOR = "#FAF9F4"
INK = "#17211F"
MUTED = "#53645F"
GRID = "#D8DDD4"
PANEL = "#FFFFFF"
PANEL_ALT = "#F3F5EF"
SCOUT = "#A33A35"
MONITOR = "#D89A2B"
STABLE = "#AAB7A0"
STRONG = "#2E6F5E"
ACCENT = "#2F6F8F"
ATT_EDGE = "#111111"
ATT_BLUE = "#D7E8EF"
ATT_BEIGE = "#F2E4CF"
ATT_GREEN = "#E5EEDD"
ATT_PINK = "#F2E1DF"
ATT_GRAY = "#E8EAEE"
ATT_YELLOW = "#F6F3D9"

PAGE_DESCRIPTIONS = {
    REPORT_OVERVIEW_TITLE: "Final report overview and hero orchard example.",
    "Executive Summary": "What the submission does, what it does not claim, and why it is useful.",
    "Review Path": "Review order for technical and grower-use evaluation.",
    "Workflow: From Satellite Scene To Field Worklist": "How raw Sentinel-2 scenes become conservative scouting priorities.",
    "All Six Sites": "Overview map for the six submitted challenge boundaries.",
    "Kern 1 Zoomed Map": "Small-boundary public-site example with intentionally conservative results.",
    "Stanislaus 1 Visual Public-Site Example": "Readable public-site example with cautious interpretation.",
    "Partner Site 1 Detail": "Primary orchard-specific proof point and field-scouting map.",
    "Strong Reference Versus Priority Zone Time Series": "Vegetation-index comparison between strong reference and weak zones.",
    "Canopy Mask Guardrail": "Check that priority zones are clipped to eligible canopy before scoring.",
    "Six-Site Summary": "Readable acreage summary for all submitted sites.",
    "How To Trust A Zone": "Operational confidence rules for using the map without overclaiming.",
    "How To Read A Zone Card": "Plain-English guide to the partner-site evidence cards.",
    "Partner Site 1 Zone Evidence Cards": "Top partner-site scout-first polygons as a ranked field worklist.",
    "Grower Decision Tree": "Bounded grower workflow from map prompt to field evidence.",
    "Practical Example Field Brief": "Short English and Spanish field-facing explanation.",
    "Field Feedback Loop": "How field notes feed threshold calibration without assigning cause.",
    "How Additional Data Could Refine The Method": "How optional records could improve confidence without changing the product into a diagnosis tool.",
    "How The Map Becomes Field Follow-Up": "How the map becomes a practical scouting follow-up packet.",
    "Design For Grower Adoption": "How the output fits existing grower and advisor workflows.",
    "Refinement With Grower Data": "What local records would improve the next version.",
    "Methodology": "Technical method summary for imagery, masking, baselines, and scoring.",
    "Grower Use And Limitations": "How to use the tool and what the current run cannot infer.",
}

ALL_SITE_IDS = [
    "partner_site_1",
    "fresno_site_1",
    "kern_site_1",
    "kings_site_1",
    "stanislaus_site_1",
    "tulare_site_1",
]
PARTNER_SITE_ID = "partner_site_1"
PAGE_NUMBER = 0
TOC_LINKS: list[tuple[int, int, tuple[float, float, float, float]]] = []


def wrap_lines(text: str, width: int = 94) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width))
    return lines


def add_text_block(
    ax,
    text: str,
    x: float,
    y: float,
    size: float = 10,
    width: int = 94,
    line_gap: float = 0.035,
    color: str = INK,
    weight: str = "normal",
) -> float:
    for line in wrap_lines(text, width):
        ax.text(x, y, line, fontsize=size, va="top", family=BODY_FONT, color=color, weight=weight)
        y -= line_gap
    return y


def reset_page_numbers() -> None:
    global PAGE_NUMBER
    PAGE_NUMBER = 0


def next_page_number() -> int:
    global PAGE_NUMBER
    PAGE_NUMBER += 1
    return PAGE_NUMBER


def header_description(title: str) -> str:
    if title in PAGE_DESCRIPTIONS:
        return PAGE_DESCRIPTIONS[title]
    if "High-Resolution Map" in title:
        return "Full-page readable zone map for field review."
    if "Canopy And Priority Overlay" in title:
        return "Single-panel check of canopy eligibility versus priority zones."
    return "Report section summary."


def setup_page(title: str, landscape: bool = False, title_size: float | None = None):
    page_no = next_page_number()
    page_size = (PAGE_SIZE[1], PAGE_SIZE[0]) if landscape else PAGE_SIZE
    fig = plt.figure(figsize=page_size, facecolor=PAPER_COLOR)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_autoscale_on(False)
    ax.axis("off")
    left = 0.07
    right = 0.93
    ax.text(
        left,
        0.957,
        title,
        fontsize=title_size or 17.5,
        weight="semibold",
        va="top",
        color=INK,
        family=HEADING_FONT,
    )
    ax.text(right, 0.982, f"Live map: {LIVE_MAP_LINK}", fontsize=6.4, color=ACCENT, va="top", ha="right", url=LIVE_MAP_LINK)
    ax.text(right, 0.968, f"GitHub: {GITHUB_LINK}", fontsize=6.0, color=MUTED, va="top", ha="right", url=GITHUB_LINK)
    ax.text(left, 0.925, header_description(title), fontsize=7.6, color=MUTED, va="top")
    ax.plot([left, right], [0.905, 0.905], color=GRID, linewidth=1.1)
    ax.text(right, 0.035, f"Page {page_no}", fontsize=6.9, color=MUTED, ha="right")
    return fig, ax


def image_shape(image_path: Path) -> tuple[int, int] | None:
    if not image_path.exists():
        return None
    image = mpimg.imread(image_path)
    height, width = image.shape[:2]
    return width, height


def add_image_fit(
    fig,
    ax,
    image_path: Path,
    left: float,
    top: float,
    max_width: float,
    max_height: float,
) -> float:
    shape = image_shape(image_path)
    if shape is None:
        ax.text(left + 0.03, top - 0.18, f"Missing figure: {image_path.name}", fontsize=12, color=INK)
        return top - max_height

    image_width, image_height = shape
    image_aspect = image_width / max(1, image_height)
    fig_width, fig_height = fig.get_size_inches()
    width = max_width
    height = (width * fig_width) / image_aspect / fig_height
    if height > max_height:
        height = max_height
        width = (height * fig_height * image_aspect) / fig_width
    x = left + (max_width - width) / 2
    bottom = top - height
    img_ax = fig.add_axes([x, bottom, width, height])
    img_ax.set_zorder(0)
    ax.set_zorder(1)
    ax.patch.set_alpha(0)
    img_ax.imshow(mpimg.imread(image_path), interpolation="nearest")
    img_ax.axis("off")
    return bottom


def save_fixed_page(pdf: PdfPages, fig) -> None:
    pdf.savefig(fig, dpi=300)
    plt.close(fig)


def draw_card(
    ax,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    facecolor: str = PANEL,
    edgecolor: str = GRID,
    title_color: str = INK,
    body_color: str = MUTED,
    title_size: float = 10,
    body_size: float = 8.0,
    body_width: int = 34,
    line_gap: float = 0.021,
) -> None:
    ax.add_patch(
        plt.Rectangle(
            (x, y),
            width,
            height,
            linewidth=0.8,
            edgecolor=edgecolor,
            facecolor=facecolor,
        )
    )
    ax.text(
        x + 0.016,
        y + height - 0.026,
        title,
        fontsize=title_size,
        weight="semibold",
        va="top",
        color=title_color,
        family=HEADING_FONT,
    )
    add_text_block(
        ax,
        body,
        x + 0.016,
        y + height - 0.058,
        size=body_size,
        width=body_width,
        line_gap=line_gap,
        color=body_color,
    )


def add_centered_lines(
    ax,
    text: str,
    cx: float,
    cy: float,
    width: int,
    size: float,
    line_gap: float,
    weight: str = "normal",
    color: str = INK,
    family: str = BODY_FONT,
    zorder: int = 4,
) -> None:
    lines = wrap_lines(text, width)
    start_y = cy + (len(lines) - 1) * line_gap / 2
    for idx, line in enumerate(lines):
        ax.text(
            cx,
            start_y - idx * line_gap,
            line,
            fontsize=size,
            weight=weight,
            color=color,
            ha="center",
            va="center",
            family=family,
            zorder=zorder,
        )


def draw_attention_box(
    ax,
    cx: float,
    cy: float,
    width: float,
    height: float,
    title: str,
    body: str = "",
    facecolor: str = ATT_BLUE,
    title_size: float = 8.8,
    body_size: float = 7.0,
    wrap_width: int = 24,
    linewidth: float = 1.7,
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (cx - width / 2, cy - height / 2),
            width,
            height,
            boxstyle="round,pad=0.006,rounding_size=0.008",
            linewidth=linewidth,
            edgecolor=ATT_EDGE,
            facecolor=facecolor,
            zorder=2,
        )
    )
    if body:
        ax.text(
            cx,
            cy + height * 0.22,
            title,
            fontsize=title_size,
            weight="semibold",
            color=INK,
            ha="center",
            va="center",
            family=HEADING_FONT,
            zorder=4,
        )
        add_centered_lines(ax, body, cx, cy - height * 0.20, wrap_width, body_size, 0.014, color=INK)
    else:
        add_centered_lines(
            ax,
            title,
            cx,
            cy,
            wrap_width,
            title_size,
            0.017,
            weight="semibold",
            family=HEADING_FONT,
        )


def draw_attention_frame(ax, x: float, y: float, width: float, height: float, label: str = "") -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.010,rounding_size=0.025",
            linewidth=1.9,
            edgecolor=ATT_EDGE,
            facecolor="#F7F7F7",
            zorder=0,
        )
    )
    if label:
        ax.text(x + width + 0.018, y + height * 0.50, label, fontsize=14, color=ATT_EDGE, va="center", family=BODY_FONT)


def draw_attention_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str = "",
    rad: float = 0.0,
    linewidth: float = 1.6,
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "->",
            "color": ATT_EDGE,
            "lw": linewidth,
            "shrinkA": 3,
            "shrinkB": 3,
            "mutation_scale": 13,
            "connectionstyle": f"arc3,rad={rad}",
        },
        zorder=3,
    )
    if label:
        lx = (start[0] + end[0]) / 2
        ly = (start[1] + end[1]) / 2
        ax.text(
            lx,
            ly + 0.020,
            label,
            fontsize=7.2,
            color=INK,
            ha="center",
            va="center",
            family=BODY_FONT,
            bbox={"boxstyle": "round,pad=0.12", "facecolor": PAPER_COLOR, "edgecolor": "none", "alpha": 0.94},
            zorder=5,
        )


def draw_wrapped_table(
    ax,
    x: float,
    y_top: float,
    width: float,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    wrap_widths: list[int],
    font_size: float = 7.4,
    header_size: float = 7.6,
    line_gap: float = 0.018,
    row_pad: float = 0.014,
) -> float:
    total = sum(col_widths)
    widths = [width * (col / total) for col in col_widths]
    x_positions = [x]
    for col_width in widths[:-1]:
        x_positions.append(x_positions[-1] + col_width)

    header_h = 0.044
    ax.add_patch(plt.Rectangle((x, y_top - header_h), width, header_h, facecolor="#E8EFEA", edgecolor=GRID, linewidth=0.8))
    for idx, header in enumerate(headers):
        ax.text(
            x_positions[idx] + 0.008,
            y_top - 0.014,
            header,
            fontsize=header_size,
            weight="semibold",
            va="top",
            color=INK,
            family=HEADING_FONT,
        )

    y = y_top - header_h
    for row_idx, row in enumerate(rows):
        wrapped = [wrap_lines(str(cell), wrap_widths[col_idx]) for col_idx, cell in enumerate(row)]
        max_lines = max(len(lines) for lines in wrapped)
        row_h = max(0.046, row_pad * 2 + max_lines * line_gap)
        face = PANEL if row_idx % 2 == 0 else "#F7F8F4"
        ax.add_patch(plt.Rectangle((x, y - row_h), width, row_h, facecolor=face, edgecolor=GRID, linewidth=0.55))
        for col_idx, lines in enumerate(wrapped):
            cell_x = x_positions[col_idx]
            cell_w = widths[col_idx]
            ax.plot([cell_x, cell_x], [y, y - row_h], color=GRID, linewidth=0.45)
            text_x = cell_x + 0.008
            text_y = y - row_pad
            ha = "left"
            if col_idx > 0 and all(part.replace(".", "", 1).replace("%", "").replace(",", "").isdigit() for part in str(row[col_idx]).split()):
                ha = "right"
                text_x = cell_x + cell_w - 0.008
            for line in lines:
                ax.text(text_x, text_y, line, fontsize=font_size, va="top", ha=ha, color=INK, family=BODY_FONT)
                text_y -= line_gap
        ax.plot([x + width, x + width], [y, y - row_h], color=GRID, linewidth=0.45)
        y -= row_h
    return y


def save_text_page(pdf: PdfPages, title: str, sections: list[tuple[str, str]]) -> None:
    fig, ax = setup_page(title)
    y = 0.89
    for heading, text in sections:
        if heading:
            ax.text(0.07, y, heading, fontsize=11.4, weight="semibold", va="top", color=INK, family=HEADING_FONT)
            y -= 0.035
        y = add_text_block(ax, text, 0.07, y, size=10, color=INK)
        y -= 0.025
    save_fixed_page(pdf, fig)


def save_image_page(pdf: PdfPages, title: str, image_path: Path, caption: str, landscape: bool = False) -> None:
    del landscape
    fig, ax = setup_page(title)
    text_bottom = add_text_block(
        ax,
        caption,
        0.07,
        0.865,
        size=9.0,
        width=92,
        line_gap=0.024,
        color=INK,
    )
    image_top = min(0.775, text_bottom - 0.030)
    add_image_fit(fig, ax, image_path, 0.055, image_top, 0.89, max(0.42, image_top - 0.105))
    save_fixed_page(pdf, fig)


def image_is_landscape(image_path: Path, threshold: float = 1.25) -> bool:
    if not image_path.exists():
        return False
    img = mpimg.imread(image_path)
    height, width = img.shape[:2]
    return (width / max(1, height)) >= threshold


def save_full_image_page(pdf: PdfPages, title: str, image_path: Path, caption: str, landscape: bool | None = None) -> None:
    use_landscape = image_is_landscape(image_path, threshold=1.65) if landscape is None else landscape
    fig, ax = setup_page(title, landscape=use_landscape)
    text_bottom = add_text_block(ax, caption, 0.055, 0.865, size=8.6, width=96, line_gap=0.022, color=INK)
    image_top = min(0.790, text_bottom - 0.025)
    add_image_fit(fig, ax, image_path, 0.045, image_top, 0.91, max(0.46, image_top - 0.100))
    save_fixed_page(pdf, fig)


def save_review_path_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("Review Path")

    y = 0.89
    y = add_text_block(
        ax,
        "Read this submission as a complete applied-agtech packet: a reproducible Sentinel-2 pipeline, a canopy-limited "
        "scouting-priority method, a grower-facing decision workflow, and portable outputs that a user can inspect without "
        "running the code first.",
        0.07,
        y,
        size=10.2,
        width=94,
    )

    y -= 0.012
    card_x = 0.07
    card_y = y - 0.165
    card_w = 0.86
    card_h = 0.125
    ax.add_patch(
        plt.Rectangle(
            (card_x, card_y),
            card_w,
            card_h,
            linewidth=0.8,
            edgecolor=GRID,
            facecolor="#EEF4F5",
        )
    )
    ax.text(
        card_x + 0.016,
        card_y + card_h - 0.026,
        "Live field map",
        fontsize=10.0,
        weight="semibold",
        va="top",
        color=INK,
        family=HEADING_FONT,
    )
    link_y = card_y + card_h - 0.058
    ax.text(
        card_x + 0.016,
        link_y,
        "Open the site",
        fontsize=8.0,
        va="top",
        color=ACCENT,
        family=BODY_FONT,
        url=LIVE_MAP_LINK,
    )
    add_text_block(
        ax,
        "Choose a boundary, inspect Scout first and Strong reference zones, then use this PDF for the method, caveats, and field follow-up instructions.",
        card_x + 0.016,
        link_y - 0.028,
        size=8.0,
        width=112,
        line_gap=0.020,
        color=MUTED,
    )

    ax.text(0.07, y - 0.205, "Review order", fontsize=11, weight="semibold", va="top", color=INK)
    y -= 0.240
    review_steps = [
        ("1", "Narrative pages", "Start here for the method, maps, guardrails, and field workflow."),
        ("2", "Live map", "Open the Vercel field map to inspect zones visually, then return to this report for interpretation."),
        ("3", "Scouting table", "Inspect ranked zones, centroids, persistence, triggered indices, and follow-up guidance."),
        ("4", "Partner map", "Use partner_site_1 as the clearest orchard-specific example."),
    ]
    for number, label, text in review_steps:
        ax.add_patch(plt.Rectangle((0.07, y - 0.047), 0.052, 0.04, facecolor=INK, edgecolor="none"))
        ax.text(0.096, y - 0.027, number, fontsize=10, weight="bold", color="white", ha="center", va="center")
        ax.text(0.14, y - 0.004, label, fontsize=10.5, weight="semibold", va="top", color=INK)
        add_text_block(ax, text, 0.14, y - 0.026, size=8.8, width=80, line_gap=0.024)
        y -= 0.072

    bottom_y = max(0.195, y - 0.055)
    ax.text(0.07, bottom_y, "Bottom line", fontsize=11, weight="semibold", va="top", color=INK)
    add_text_block(
        ax,
        "The packet is meant to be read as an applied orchard scouting product: transparent method, practical field workflow, "
        "clear limitations, and artifacts that work in both GitHub and grower/advisor workflows.",
        0.07,
        bottom_y - 0.045,
        size=10,
        width=94,
    )

    save_fixed_page(pdf, fig)


def save_pipeline_workflow_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("Workflow: From Satellite Scene To Field Worklist")
    intro = (
        "Read left to right, top to bottom. The important design choice is the order: exclude bad pixels, limit scoring to canopy, "
        "compare each site against itself, then turn the map into a field worklist."
    )
    add_text_block(ax, intro, 0.07, 0.865, size=9.4, width=94, line_gap=0.026)

    draw_attention_frame(ax, 0.115, 0.310, 0.315, 0.445)
    draw_attention_frame(ax, 0.570, 0.310, 0.315, 0.445)
    ax.text(0.130, 0.776, "1. Filter and mask", fontsize=9.0, weight="semibold", color=INK, family=HEADING_FONT, va="top")
    ax.text(0.585, 0.776, "2. Score and rank", fontsize=9.0, weight="semibold", color=INK, family=HEADING_FONT, va="top")

    left_x = 0.272
    right_x = 0.728
    ys = [0.690, 0.585, 0.480, 0.375]
    left_nodes = [
        ("Site boundaries", "local baseline only", ATT_PINK),
        ("Sentinel-2 L2A", "2021-2024 summer scenes", ATT_GRAY),
        ("Clear-pixel filter", "cloud, shadow, water, no-data removed", ATT_GREEN),
        ("Canopy guardrail", "score canopy before acreage", ATT_YELLOW),
    ]
    right_nodes = [
        ("Vegetation evidence", "NDVI, NDMI, NDRE, EVI2", ATT_BLUE),
        ("Within-site score", "site compared with itself", ATT_BEIGE),
        ("Priority zones", "scout first, monitor, stable, strong", ATT_GREEN),
        ("Field worklist", "centroids, prompts, feedback fields", ATT_PINK),
    ]
    for cy, (title, body, face) in zip(ys, left_nodes, strict=True):
        draw_attention_box(ax, left_x, cy, 0.205, 0.065, title, body, face, title_size=8.4, body_size=6.8, wrap_width=22)
    for cy, (title, body, face) in zip(ys, right_nodes, strict=True):
        draw_attention_box(ax, right_x, cy, 0.205, 0.065, title, body, face, title_size=8.4, body_size=6.8, wrap_width=22)

    for upper, lower in zip(ys[:-1], ys[1:], strict=True):
        draw_attention_arrow(ax, (left_x, upper - 0.038), (left_x, lower + 0.038))
        draw_attention_arrow(ax, (right_x, upper - 0.038), (right_x, lower + 0.038))
    draw_attention_arrow(ax, (left_x + 0.112, ys[-1]), (right_x - 0.112, ys[0]), rad=0.16)

    draw_attention_box(
        ax,
        0.500,
        0.190,
        0.610,
        0.085,
        "Grower-facing output",
        "The result is not a diagnosis. It is a prioritized, auditable queue: where to walk first, what to compare, what records to check, and what to write down.",
        "#FFFFFF",
        title_size=9.2,
        body_size=7.2,
        wrap_width=70,
        linewidth=1.9,
    )
    draw_attention_arrow(ax, (right_x, ys[-1] - 0.040), (0.500, 0.238), rad=0.10)
    save_fixed_page(pdf, fig)


def read_summary(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def resolve_scouting_table(spatial_dir: Path, out_path: Path) -> Path | None:
    return first_existing(
        [
            spatial_dir / "scouting_priority_table.csv",
            spatial_dir.parent / "tables" / "scouting_priority_table.csv",
            out_path.parent / "scouting_priority_table.csv",
            out_path.parent.parent / "tables" / "scouting_priority_table.csv",
            Path("output/report/scouting_priority_table.csv"),
        ]
    )


def ordered_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    row_by_site = {row.get("site", ""): row for row in rows}
    ordered = [row_by_site[site] for site in ALL_SITE_IDS if site in row_by_site]
    ordered.extend(row for row in rows if row.get("site", "") not in ALL_SITE_IDS)
    return ordered


def site_title(site: str) -> str:
    if site == PARTNER_SITE_ID:
        return "Partner Site 1 Orchard-Specific Example"
    if site == "kern_site_1":
        return "Kern 1 Public Boundary"
    return f"{site.replace('_', ' ').title()} Public Boundary"


def report_section_titles() -> list[str]:
    titles = [
        "Title Page",
        "Table of Contents",
        REPORT_OVERVIEW_TITLE,
        "Executive Summary",
        "Review Path",
        "Workflow: From Satellite Scene To Field Worklist",
        "All Six Sites",
        "Kern 1 Zoomed Map",
        "Stanislaus 1 Visual Public-Site Example",
        "Partner Site 1 Detail",
        "Strong Reference Versus Priority Zone Time Series",
        "Canopy Mask Guardrail",
        "Six-Site Summary",
        "How To Trust A Zone",
        "How To Read A Zone Card",
        "Partner Site 1 Zone Evidence Cards",
        "Grower Decision Tree",
        "Practical Example Field Brief",
        "Field Feedback Loop",
        "How Additional Data Could Refine The Method",
        "How The Map Becomes Field Follow-Up",
        "Design For Grower Adoption",
        "Refinement With Grower Data",
    ]
    for site in ALL_SITE_IDS:
        titles.append(f"{site_title(site)} - High-Resolution Map")
        titles.append(f"{site.replace('_', ' ').title()} Canopy And Priority Overlay")
    titles.extend(["Methodology", "Grower Use And Limitations"])
    return titles


def site_caption(site: str) -> str:
    if site == PARTNER_SITE_ID:
        return (
            "Partner site 1 is the strongest orchard-specific example. The map highlights persistent within-site "
            "underperformance as scouting-priority and monitor zones after clear-pixel filtering and canopy masking."
        )
    if site == "kern_site_1":
        return (
            "Kern 1 is a very small public boundary with 19.62 eligible canopy acres and no scout-first acreage "
            "in this run. It is shown as a zoomed, readable map because the full boundary is too small in the six-site "
            "overview. This is an intentionally conservative result: the method does not force a priority zone when "
            "persistent multi-index evidence is weak. Interpretation remains cautious because crop and management context are unverified."
        )
    return (
        f"{site.replace('_', ' ').title()} is included to show the pipeline across the full challenge boundary set. "
        "Interpretation is cautious because the public boundary crop context may be mixed or unverified; mapped zones are "
        "scouting priorities for field follow-up, not cause labels."
    )


def save_title_page(pdf: PdfPages) -> None:
    page_no = next_page_number()
    fig = plt.figure(figsize=PAGE_SIZE, facecolor=PAPER_COLOR)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.07, 0.905, SUBMISSION_LABEL.upper(), fontsize=9.4, weight="semibold", color=ACCENT, family=HEADING_FONT)
    ax.text(0.07, 0.815, REPORT_TITLE, fontsize=28, weight="semibold", color=INK, family=HEADING_FONT, va="top")
    ax.text(0.07, 0.730, PRODUCT_NAME, fontsize=14.0, color=ACCENT, family=HEADING_FONT, weight="semibold", va="top")
    ax.text(0.07, 0.690, CHALLENGE_LINE, fontsize=10.2, color=MUTED, family=BODY_FONT, va="top")

    ax.text(0.07, 0.615, AUTHOR_NAME, fontsize=10.8, color=INK, family=HEADING_FONT, va="top")
    ax.text(0.07, 0.585, f"{AUTHOR_AFFILIATION} | {SUBMISSION_LABEL} | {SUBMISSION_DATE}", fontsize=9.2, color=MUTED, family=HEADING_FONT, va="top")
    ax.text(0.07, 0.555, AUTHOR_CONTACT, fontsize=9.0, color=MUTED, family=HEADING_FONT, va="top")
    ax.text(0.07, 0.525, f"Live app: {LIVE_MAP_LINK}", fontsize=9.0, color=ACCENT, family=HEADING_FONT, va="top", url=LIVE_MAP_LINK)

    ax.text(0.07, 0.445, "What This Is", fontsize=12.2, weight="semibold", color=INK, family=HEADING_FONT, va="top")
    y = add_text_block(ax, THESIS_TEXT, 0.07, 0.405, size=9.2, width=108, line_gap=0.023, color=INK)
    add_text_block(ax, THESIS_TEXT_2, 0.07, y - 0.014, size=9.2, width=108, line_gap=0.023, color=INK)

    ax.plot([0.07, 0.93], [0.080, 0.080], color=GRID, linewidth=1.0)
    ax.text(0.07, 0.055, f"GitHub: {GITHUB_LINK}", fontsize=7.0, color=MUTED, family=BODY_FONT, url=GITHUB_LINK)
    ax.text(0.93, 0.030, f"Page {page_no}", fontsize=6.9, color=MUTED, ha="right")
    save_fixed_page(pdf, fig)


def save_table_of_contents_page(pdf: PdfPages, titles: list[str]) -> None:
    TOC_LINKS.clear()
    page_no = next_page_number()
    fig = plt.figure(figsize=PAGE_SIZE, facecolor=PAPER_COLOR)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.07, 0.930, "Table of Contents", fontsize=20, weight="semibold", color=INK, family=HEADING_FONT, va="top")
    ax.plot([0.07, 0.93], [0.887, 0.887], color=GRID, linewidth=1.0)

    entries = [(idx + 1, title) for idx, title in enumerate(titles)]
    rows_per_col = (len(entries) + 1) // 2
    columns = [(0.07, 0.445), (0.535, 0.395)]
    y_start = 0.842
    row_gap = 0.030

    for col_idx, (x, width) in enumerate(columns):
        col_entries = entries[col_idx * rows_per_col : (col_idx + 1) * rows_per_col]
        for row_idx, (target_page, title) in enumerate(col_entries):
            y = y_start - row_idx * row_gap
            ax.text(x, y, title, fontsize=8.0, color=INK, family=BODY_FONT, va="top")
            ax.text(x + width, y, str(target_page), fontsize=8.0, color=ACCENT, family=BODY_FONT, va="top", ha="right")
            TOC_LINKS.append((page_no - 1, target_page - 1, (x, y + 0.008, x + width, y - 0.020)))

    ax.text(0.93, 0.035, f"Page {page_no}", fontsize=6.9, color=MUTED, ha="right")
    save_fixed_page(pdf, fig)


def apply_pdf_navigation(pdf_path: Path, titles: list[str]) -> None:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyMuPDF is required to add clickable report navigation.") from exc

    doc = fitz.open(pdf_path)
    if doc.page_count != len(titles):
        doc.close()
        raise ValueError(f"PDF page count {doc.page_count} does not match section list {len(titles)}")

    doc.set_toc([(1, title, idx + 1) for idx, title in enumerate(titles)])
    page_width, page_height = PAGE_SIZE[0] * 72, PAGE_SIZE[1] * 72
    for toc_page_index, target_page_index, (x0, y_top, x1, y_bottom) in TOC_LINKS:
        if toc_page_index >= doc.page_count or target_page_index >= doc.page_count:
            continue
        rect = fitz.Rect(x0 * page_width, (1 - y_top) * page_height, x1 * page_width, (1 - y_bottom) * page_height)
        doc[toc_page_index].insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": target_page_index})

    tmp_path = pdf_path.with_suffix(".nav.tmp.pdf")
    doc.save(tmp_path, deflate=True)
    doc.close()
    tmp_path.replace(pdf_path)


def save_cover_page(pdf: PdfPages, figures_dir: Path, rows: list[dict[str, str]]) -> None:
    fig, ax = setup_page(REPORT_OVERVIEW_TITLE, title_size=20)
    ax.text(0.07, 0.875, PRODUCT_NAME, fontsize=12.5, color=ACCENT, va="top", family=HEADING_FONT, weight="semibold")
    ax.text(0.07, 0.845, CHALLENGE_LINE, fontsize=9.6, color=MUTED, va="top")
    ax.text(0.07, 0.820, "Grower-grade scientific brief for orchard scouting priority.", fontsize=9.6, color=MUTED, va="top")
    ax.text(0.07, 0.796, f"Live field map: {LIVE_MAP_LINK}", fontsize=9.0, color=ACCENT, va="top", family=BODY_FONT, url=LIVE_MAP_LINK)
    add_text_block(
        ax,
        "A reproducible Sentinel-2 pipeline that turns persistent within-orchard underperformance into a ranked scouting worklist before any cause is assigned.",
        0.07,
        0.744,
        size=9.5,
        width=88,
        line_gap=0.025,
        color=INK,
    )
    draw_card(
        ax,
        0.07,
        0.590,
        0.86,
        0.108,
        "How to use the live map with this report",
        "Open the Vercel map, choose a site, inspect Scout first zones against Strong reference zones, then use this PDF to interpret confidence, limits, and field feedback steps.",
        facecolor="#EEF4F5",
        title_size=9.5,
        body_size=7.4,
        body_width=112,
        line_gap=0.018,
    )

    cards = [
        ("Vegetation evidence", "NDVI, NDMI, NDRE, and EVI2 across 2021-2024 summer imagery.", "#EEF3ED"),
        ("Canopy eligibility", "Priority pixels are clipped to persistent eligible canopy before scoring.", "#F4EFE4"),
        ("Scouting output", "Scout first, compare strong reference, check records, then record the finding.", "#EEF2F7"),
    ]
    x = 0.07
    for title, body, color in cards:
        draw_card(ax, x, 0.445, 0.265, 0.125, title, body, facecolor=color, body_width=29, body_size=7.5, line_gap=0.018)
        x += 0.295

    image_path = figures_dir / "partner_site_1_report_zone_map.png"
    image_bottom = add_image_fit(fig, ax, image_path, 0.09, 0.380, 0.82, 0.245)

    partner_row = next((row for row in rows if row.get("site") == PARTNER_SITE_ID), {})
    scout = partner_row.get("investigate_acres_est", "17.00")
    canopy = partner_row.get("eligible_canopy_acres_est", partner_row.get("total_acres_est", "88.83"))
    caption_y = max(0.165, image_bottom - 0.018)
    ax.text(0.07, caption_y, "Hero example: partner_site_1", fontsize=10.5, weight="semibold", color=INK, va="top", family=HEADING_FONT)
    add_text_block(
        ax,
        f"Partner site is the clearest orchard-specific example: {scout} scout-first acres inside {canopy} eligible canopy acres. Public sites are labeled cautiously.",
        0.07,
        caption_y - 0.030,
        size=8.6,
        width=105,
        line_gap=0.022,
        color=MUTED,
    )
    save_fixed_page(pdf, fig)


def save_trust_page(pdf: PdfPages, rows: list[dict[str, str]]) -> None:
    fig, ax = setup_page("How To Trust A Zone")
    y = 0.885
    y = add_text_block(
        ax,
        "Read confidence as a practical field-use signal. It tells a grower which mapped zones deserve attention first; it does not identify the cause or estimate loss.",
        0.07,
        y,
        size=9.4,
        width=92,
        line_gap=0.027,
    )
    y -= 0.02

    cards = [
        (
            "Stronger Read",
            "More clear observations, repeated evidence across years, agreement across several indices, and pixels inside the canopy mask.",
            0.07,
            y - 0.19,
            0.26,
            0.18,
            "#E8F2EE",
        ),
        (
            "Use Caution",
            "Public boundaries, tiny patches, and monitor-level zones are still useful prompts, but they need field and record context.",
            0.37,
            y - 0.19,
            0.26,
            0.18,
            "#F6F0E4",
        ),
        (
            "Kern 1",
            "The small public boundary has no scout-first acreage. That is a useful conservative result, not necessarily a failed map.",
            0.67,
            y - 0.19,
            0.26,
            0.18,
            "#EEF2F7",
        ),
    ]
    for heading, text, x, y_bottom, width, height, color in cards:
        ax.add_patch(plt.Rectangle((x, y_bottom), width, height, facecolor=color, edgecolor="#A7B0BA", linewidth=0.8))
        ax.text(x + 0.016, y_bottom + height - 0.024, heading, fontsize=10, weight="semibold", va="top")
        add_text_block(ax, text, x + 0.016, y_bottom + height - 0.052, size=7.6, width=27, line_gap=0.019)

    ordered = ordered_summary_rows(rows)
    table_rows = []
    for row in ordered:
        site = row.get("site", "")
        mapped_acres = as_float(row.get("total_acres_est"))
        scout_acres = as_float(row.get("investigate_acres_est"))
        median_conf = row.get("median_confidence", "")
        if site == PARTNER_SITE_ID:
            trust = "Strongest orchard\nspecific read"
        elif site == "kern_site_1":
            trust = "Small-site\nlow-priority read"
        else:
            trust = "Cautious public\nboundary read"
        table_rows.append([site, f"{mapped_acres:.2f}", f"{scout_acres:.2f}", median_conf, trust])

    draw_wrapped_table(
        ax,
        0.055,
        0.49,
        0.89,
        ["Site", "Canopy ac", "Scout-first ac", "Median conf.", "Trust read"],
        table_rows,
        [0.24, 0.14, 0.17, 0.14, 0.25],
        [20, 9, 10, 10, 18],
        font_size=7.2,
        header_size=7.4,
        line_gap=0.017,
    )

    save_fixed_page(pdf, fig)


def save_zone_card_reading_guide(pdf: PdfPages) -> None:
    save_text_page(
        pdf,
        "How To Read A Zone Card",
        [
            (
                "Purpose",
                "Zone cards turn the map into a short field worklist. They explain why each partner-site polygon is worth field follow-up without assigning cause from satellite imagery.",
            ),
            (
                "Fields",
                "Area = approximate field footprint. Persistence = how repeatedly the zone appeared weak across years. Indices triggered = which vegetation signals agreed. Valid obs = how many clear observations supported the zone. Mean relative underperformance = strength of the weaker signal relative to the site's own canopy baseline. Centroid = starting point for field follow-up, not a cause point.",
            ),
            (
                "Confidence",
                "High confidence means good place to look first. It does not mean known cause. Low confidence means do not overreact; use the zone as a prompt for comparison and records review.",
            ),
        ],
    )


def save_zone_evidence_cards(pdf: PdfPages, scouting_rows: list[dict[str, str]]) -> None:
    partner_rows = [
        row
        for row in scouting_rows
        if row.get("site_id") == PARTNER_SITE_ID and row.get("priority_class", "").lower() == "scout first"
    ]
    partner_rows.sort(
        key=lambda row: (
            as_float(row.get("persistence_score")),
            as_float(row.get("approx_area_acres")),
            as_float(row.get("mean_relative_underperformance")),
        ),
        reverse=True,
    )
    partner_rows = partner_rows[:5]

    fig, ax = setup_page("Partner Site 1 Zone Evidence Cards")
    y = 0.885
    intro = (
        "These are the top partner-site field targets from submission/tables/scouting_priority_table.csv. They are not cause labels; they are a short ranked worklist for where to look first. Full coordinates and index fields remain in that CSV."
    )
    y = add_text_block(ax, intro, 0.07, y, size=9.4, width=92, line_gap=0.027)
    y -= 0.015

    if not partner_rows:
        ax.text(0.08, y, "No partner-site scout-first rows were found in the scouting-priority table.", fontsize=11, va="top")
        save_fixed_page(pdf, fig)
        return

    card_height = 0.122
    for idx, row in enumerate(partner_rows, start=1):
        y_top = y - (idx - 1) * (card_height + 0.012)
        y_bottom = y_top - card_height
        ax.add_patch(plt.Rectangle((0.07, y_bottom), 0.86, card_height, facecolor="#FFFFFF", edgecolor="#A7B0BA", linewidth=0.8))
        zone_short = row.get("zone_id", "").replace("partner_site_1_", "")
        ax.add_patch(plt.Rectangle((0.07, y_bottom), 0.195, card_height, facecolor=PANEL_ALT, edgecolor="#A7B0BA", linewidth=0.0))
        ax.plot([0.265, 0.265], [y_bottom, y_top], color="#A7B0BA", linewidth=0.55)
        ax.plot([0.650, 0.650], [y_bottom + 0.012, y_top - 0.012], color=GRID, linewidth=0.55)
        ax.text(0.085, y_top - 0.018, f"{idx}.", fontsize=9.4, weight="semibold", va="top", color=ACCENT, family=HEADING_FONT)
        ax.text(0.113, y_top - 0.018, zone_short, fontsize=9.4, weight="semibold", va="top", color=INK, family=HEADING_FONT)

        persistence = as_float(row.get("persistence_score"))
        valid_obs = as_float(row.get("valid_observation_count"))
        triggered = row.get("indices_triggered", "")
        index_count = len([part for part in triggered.split(";") if part.strip()])
        if persistence >= 0.85 and valid_obs >= 8 and index_count >= 4:
            trust_read = "High signal strength"
        elif persistence >= 0.50 and index_count >= 3:
            trust_read = "Moderate signal strength"
        else:
            trust_read = "Cautious signal strength"

        centroid = f"Start: {as_float(row.get('centroid_lat')):.6f}, {as_float(row.get('centroid_lon')):.6f}"
        add_text_block(ax, centroid, 0.085, y_top - 0.052, size=6.9, width=20, line_gap=0.015, color=MUTED)

        metrics = [
            ("AREA", f"{as_float(row.get('approx_area_acres')):.2f} ac"),
            ("PERSIST.", f"{persistence:.2f}"),
            ("OBS.", f"{valid_obs:.0f}"),
            ("WEAK", f"{as_float(row.get('mean_relative_underperformance')):.2f}"),
        ]
        mx0, my0 = 0.287, y_top - 0.028
        for m_idx, (label, value) in enumerate(metrics):
            mx = mx0 + m_idx * 0.088
            ax.text(mx, my0, label, fontsize=6.3, color=MUTED, va="top", family=BODY_FONT)
            ax.text(mx, my0 - 0.018, value, fontsize=8.5, weight="semibold", color=INK, va="top", family=BODY_FONT)
        ax.text(0.287, y_bottom + 0.026, "Signals: NDVI, NDMI, NDRE, EVI2", fontsize=7.1, color=MUTED, va="bottom", family=BODY_FONT)

        ax.text(0.670, y_top - 0.014, "Trust read", fontsize=7.4, weight="semibold", color=INK, va="top", family=HEADING_FONT)
        ax.text(0.670, y_top - 0.035, trust_read, fontsize=8.0, color=ACCENT, va="top", family=BODY_FONT)
        add_text_block(
            ax,
            "Scout, compare reference canopy, then check records before assigning cause.",
            0.670,
            y_top - 0.059,
            size=7.4,
            width=29,
            line_gap=0.017,
            color=INK,
        )

    save_fixed_page(pdf, fig)


def save_grower_decision_tree_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("Grower Decision Tree")
    intro = (
        "Use this as a field route: start from the mapped zone, compare against stronger nearby canopy, check records, then record one feedback label. The map ranks where to inspect first; it does not assign cause."
    )
    add_text_block(ax, intro, 0.07, 0.865, size=9.1, width=94, line_gap=0.024, color=INK)

    draw_attention_box(
        ax,
        0.500,
        0.735,
        0.340,
        0.058,
        "Zone evidence card",
        "start with Scout first centroid",
        ATT_PINK,
        title_size=8.7,
        body_size=6.8,
        wrap_width=32,
    )
    draw_attention_box(
        ax,
        0.500,
        0.635,
        0.300,
        0.070,
        "Walk mapped zone",
        "look for visible canopy difference",
        ATT_BLUE,
        title_size=8.3,
        body_size=6.8,
        wrap_width=24,
    )
    draw_attention_box(
        ax,
        0.500,
        0.535,
        0.300,
        0.070,
        "Compare reference",
        "nearby Strong canopy is the field control",
        ATT_BEIGE,
        title_size=8.3,
        body_size=6.8,
        wrap_width=25,
    )
    draw_attention_box(
        ax,
        0.500,
        0.435,
        0.300,
        0.070,
        "Add records",
        "irrigation, PCA, replant, management history",
        ATT_GREEN,
        title_size=8.3,
        body_size=6.7,
        wrap_width=25,
    )
    draw_attention_box(
        ax,
        0.500,
        0.335,
        0.340,
        0.080,
        "Decision read",
        "visible difference plus record context?",
        ATT_YELLOW,
        title_size=8.4,
        body_size=6.8,
        wrap_width=32,
    )
    draw_attention_box(
        ax,
        0.245,
        0.220,
        0.215,
        0.074,
        "No visible difference",
        "record no action or revisit later",
        ATT_GRAY,
        title_size=8.0,
        body_size=6.6,
        wrap_width=24,
    )
    draw_attention_box(
        ax,
        0.500,
        0.220,
        0.230,
        0.074,
        "Monitor / unclear",
        "keep notes and photos; do not force a cause label",
        "#FFFFFF",
        title_size=8.0,
        body_size=6.5,
        wrap_width=26,
    )
    draw_attention_box(
        ax,
        0.755,
        0.220,
        0.215,
        0.074,
        "Known concern",
        "assign owner only after evidence agrees",
        ATT_GREEN,
        title_size=8.0,
        body_size=6.6,
        wrap_width=24,
    )
    draw_attention_box(
        ax,
        0.500,
        0.100,
        0.590,
        0.070,
        "Feedback label",
        "confirmed concern, known context, no action, revisit later, or missed signal",
        ATT_PINK,
        title_size=8.3,
        body_size=6.7,
        wrap_width=68,
    )

    draw_attention_arrow(ax, (0.500, 0.703), (0.500, 0.674))
    draw_attention_arrow(ax, (0.500, 0.598), (0.500, 0.574))
    draw_attention_arrow(ax, (0.500, 0.498), (0.500, 0.474))
    draw_attention_arrow(ax, (0.500, 0.398), (0.500, 0.376))
    draw_attention_arrow(ax, (0.430, 0.300), (0.245, 0.259), rad=0.04)
    draw_attention_arrow(ax, (0.500, 0.292), (0.500, 0.259))
    draw_attention_arrow(ax, (0.570, 0.300), (0.755, 0.259), rad=-0.04)
    draw_attention_arrow(ax, (0.245, 0.183), (0.395, 0.136), rad=0.04)
    draw_attention_arrow(ax, (0.500, 0.183), (0.500, 0.136))
    draw_attention_arrow(ax, (0.755, 0.183), (0.605, 0.136), rad=-0.04)

    save_fixed_page(pdf, fig)


def save_five_sentence_field_brief_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("Practical Example Field Brief")
    intro = (
        "The same field instruction is kept in English and Spanish so the scouting task can move from map review to crew execution without changing the caveat."
    )
    add_text_block(ax, intro, 0.07, 0.865, size=9.1, width=94, line_gap=0.024, color=INK)

    left_x = 0.07
    right_x = 0.535
    top = 0.765
    col_w = 0.395
    col_h = 0.490
    for x in (left_x, right_x):
        ax.add_patch(plt.Rectangle((x, top - col_h), col_w, col_h, facecolor="#FFFFFF", edgecolor=GRID, linewidth=0.75))

    english = [
        "1. This map only tells us where canopy repeatedly looked weaker than the same site's baseline.",
        "2. Start with the Scout first coordinate and compare it with a nearby Strong reference area.",
        "3. In the field, check visible canopy, irrigation distribution, pest or disease symptoms, soil or water movement, and recent records.",
        "4. Send findings, photos, and notes to the farm manager, PCA/crop advisor, or irrigation lead depending on what is observed.",
        "5. Record confirmed concern, known context, no action, or revisit later so the next model run can learn from field reality.",
    ]
    spanish = [
        "1. Este mapa solo indica donde el dosel se vio repetidamente mas debil que la linea base del mismo sitio.",
        "2. Empiece con la coordenada de Explorar primero y comparela con una zona cercana de Referencia fuerte.",
        "3. En el campo, revise el dosel visible, la distribucion del riego, sintomas de plagas o enfermedad, movimiento de suelo o agua, y registros recientes.",
        "4. Envie hallazgos, fotos y notas al encargado del rancho, asesor agricola/PCA, o responsable de riego segun lo observado.",
        "5. Registre problema confirmado, contexto conocido, sin accion, o revisar despues para que la siguiente corrida del modelo aprenda de la realidad del campo.",
    ]

    ax.text(left_x + 0.018, top - 0.028, "English", fontsize=10.4, weight="semibold", color=INK, va="top", family=HEADING_FONT)
    ax.text(right_x + 0.018, top - 0.028, "Spanish Option", fontsize=10.4, weight="semibold", color=INK, va="top", family=HEADING_FONT)
    ax.text(
        right_x + 0.160,
        top - 0.029,
        "for bilingual crew handoffs",
        fontsize=7.4,
        style="italic",
        color=MUTED,
        va="top",
        family=BODY_FONT,
    )

    y_left = top - 0.070
    for item in english:
        y_left = add_text_block(ax, item, left_x + 0.018, y_left, size=8.25, width=43, line_gap=0.020, color=INK)
        y_left -= 0.014

    y_right = top - 0.070
    for item in spanish:
        y_right = add_text_block(ax, item, right_x + 0.018, y_right, size=8.05, width=42, line_gap=0.020, color=INK)
        y_right -= 0.014

    ax.add_patch(plt.Rectangle((0.07, 0.160), 0.86, 0.080, facecolor=PANEL_ALT, edgecolor=GRID, linewidth=0.75))
    add_text_block(
        ax,
        "For bilingual crew handoffs, the same process is easier to read in both languages: where to look, what to compare, what evidence to collect, and how to avoid turning a satellite signal into a cause label.",
        0.09,
        0.215,
        size=8.1,
        width=94,
        line_gap=0.019,
        color=INK,
    )
    save_fixed_page(pdf, fig)


def save_field_feedback_loop_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("Field Feedback Loop")
    y = 0.885
    intro = (
        "A useful grower tool needs a low-burden way to learn from manual verification. The submitted packet includes a field feedback "
        "template and validation sampling plan so the next version can measure whether Scout first zones were useful field targets."
    )
    y = add_text_block(ax, intro, 0.07, y, size=9.8, width=96, line_gap=0.03)
    y -= 0.025

    rows = [
        ["Confirmed concern", "Record photos, visible difference, records checked, and followup_owner.", "Keep threshold; compare recurring causes only after field evidence."],
        ["Known context", "Record replant, variety, block edge, management history, or expected difference.", "Downgrade repeated context artifacts or mask them if they are not actionable."],
        ["No action", "Record no visible difference and no supporting record evidence.", "Track as false alert; raise threshold or require stronger multi-index agreement."],
        ["Revisit later", "Record access limits, unclear symptoms, or missing records.", "Keep as monitor/revisit instead of forcing a cause or treatment."],
        ["Missed signal", "If Strong/Stable area looks weak in field, record it as a missed-signal check.", "Inspect canopy mask, timing window, index mix, and confidence rule."],
    ]
    table_bottom = draw_wrapped_table(
        ax,
        0.055,
        0.715,
        0.89,
        ["Field result", "What to write down", "How the next model uses it"],
        rows,
        [0.22, 0.39, 0.39],
        [18, 38, 38],
        font_size=7.3,
        header_size=7.6,
        line_gap=0.018,
    )

    notes_y = table_bottom - 0.030
    next_y = add_text_block(
        ax,
        "Minimum feedback fields: zone_id, scout_name, actual_minutes, visible_canopy_difference, compared_to_strong_reference, records checked, photos_taken, finding_label, followup_owner, and notes.",
        0.07,
        notes_y,
        size=8.9,
        width=98,
        line_gap=0.026,
        color=INK,
    )
    add_text_block(
        ax,
        "The feedback loop is not a full accuracy study. It is a practical trust loop: confirmed-useful rate, false-alert rate, reference-agreement rate, and missed-signal checks.",
        0.07,
        next_y - 0.034,
        size=8.9,
        width=98,
        line_gap=0.026,
        color=INK,
    )
    save_fixed_page(pdf, fig)


def save_grower_work_order_page(pdf: PdfPages) -> None:
    fig, ax = setup_page("How The Map Becomes Field Follow-Up")
    add_text_block(
        ax,
        "The work order turns the ranked map into a simple field sequence: choose a zone, locate it, compare it with a stronger reference area, then record what was actually found.",
        0.07,
        0.865,
        size=9.5,
        width=94,
        line_gap=0.025,
    )

    draw_attention_frame(ax, 0.080, 0.535, 0.840, 0.225)
    nodes = [
        (0.180, "Pick zone", "top Scout first row or zone_id", ATT_PINK),
        (0.395, "Locate it", "centroid_lat and centroid_lon", ATT_BLUE),
        (0.610, "Compare", "walk polygon plus Strong reference", ATT_BEIGE),
        (0.825, "Record", "label finding and owner", ATT_GREEN),
    ]
    for cx, title, body, face in nodes:
        draw_attention_box(ax, cx, 0.650, 0.158, 0.102, title, body, face, title_size=8.4, body_size=6.8, wrap_width=19)
    for start_x, end_x in [(0.260, 0.315), (0.475, 0.530), (0.690, 0.745)]:
        draw_attention_arrow(ax, (start_x, 0.650), (end_x, 0.650), linewidth=1.7)

    draw_attention_box(
        ax,
        0.500,
        0.405,
        0.720,
        0.120,
        "How a grower finds the zone",
        "Use the evidence-card zone_id or submission/tables/scouting_priority_table.csv, then enter the centroid latitude/longitude in a phone map or GPS. The polygon marks the area to walk, not a row-by-row route.",
        "#FFFFFF",
        title_size=9.0,
        body_size=7.2,
        wrap_width=86,
        linewidth=1.8,
    )
    draw_attention_arrow(ax, (0.500, 0.598), (0.500, 0.470))

    draw_attention_box(
        ax,
        0.500,
        0.220,
        0.720,
        0.095,
        "Boundary",
        "The submitted data do not include roads, gates, irrigation sets, or access lanes, so the packet identifies where to start scouting but does not claim a physical route or treatment.",
        ATT_GRAY,
        title_size=8.7,
        body_size=7.0,
        wrap_width=86,
        linewidth=1.8,
    )
    draw_attention_arrow(ax, (0.500, 0.342), (0.500, 0.272))
    save_fixed_page(pdf, fig)


def save_refinement_with_grower_data_page(pdf: PdfPages) -> None:
    save_text_page(
        pdf,
        "Refinement With Grower Data",
        [
            (
                "Field Scouting Labels",
                "If each visited zone came back with confirmed concern, known context, no action, revisit later, or missed-signal labels, the thresholds could be tuned around what was actually useful in the field.",
            ),
            (
                "Irrigation And Management Records",
                "If irrigation sets, repairs, varieties, planting age, spray history, pruning, and replant records were available, repeated weak signals could be separated from expected management patterns.",
            ),
            (
                "Yield Or Quality Data",
                "If yield maps, bin counts, packout, or quality observations were available, the model could be checked against outcomes instead of only against vegetation-signal persistence.",
            ),
            (
                "Grower Relevance",
                "With those data, the next version would be more accurate and more relevant: fewer false alerts, better local calibration, clearer confidence levels, and work orders that match how the grower already manages the block.",
            ),
        ],
    )


def save_results_table(pdf: PdfPages, rows: list[dict[str, str]]) -> None:
    fig, ax = setup_page("Six-Site Summary")
    if not rows:
        ax.text(0.08, 0.82, "No spatial summary table found.", fontsize=11)
        save_fixed_page(pdf, fig)
        return

    add_text_block(
        ax,
        "The six challenge boundaries were processed with the same canopy-limited workflow. Partner Site 1 is the strongest orchard-specific proof point; the public boundaries show coverage and are interpreted cautiously.",
        0.07,
        0.865,
        size=9.5,
        width=94,
        line_gap=0.026,
    )

    ordered = ordered_summary_rows(rows)
    table_rows = []
    for row in ordered[:6]:
        site = row.get("site", "")
        label = site.replace("_", " ").title()
        if site == PARTNER_SITE_ID:
            status = "orchard-specific proof point"
        elif site == "kern_site_1":
            status = "small conservative public read"
        else:
            status = "public-boundary coverage read"
        table_rows.append(
            [
                label,
                status,
                f"{as_float(row.get('total_acres_est')):.1f}",
                f"{as_float(row.get('investigate_acres_est')):.1f}",
                f"{as_float(row.get('monitor_acres_est')):.1f}",
                f"{as_float(row.get('strong_acres_est')):.1f}",
            ]
        )

    draw_wrapped_table(
        ax,
        0.055,
        0.710,
        0.89,
        ["Site", "Read", "Canopy ac", "Scout-first ac", "Monitor ac", "Strong ref ac"],
        table_rows,
        [0.20, 0.27, 0.13, 0.14, 0.13, 0.13],
        [17, 27, 9, 9, 9, 9],
        font_size=7.8,
        header_size=7.8,
        line_gap=0.018,
        row_pad=0.015,
    )

    add_text_block(
        ax,
        "All acreage values are eligible-canopy pixels only. The table output remains available as CSV; this page is deliberately larger and more readable for PDF review.",
        0.07,
        0.245,
        size=8.6,
        width=94,
        line_gap=0.022,
        color=MUTED,
    )
    save_fixed_page(pdf, fig)


def build_report(args: argparse.Namespace) -> None:
    figures_dir = Path(args.figures_dir)
    spatial_dir = Path(args.spatial_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    reset_page_numbers()

    rows = ordered_summary_rows(read_summary(spatial_dir / "spatial_zone_summary.csv"))
    scouting_table_path = resolve_scouting_table(spatial_dir, out_path)
    scouting_rows = read_csv_rows(scouting_table_path) if scouting_table_path else []
    section_titles = report_section_titles()

    with PdfPages(out_path) as pdf:
        save_title_page(pdf)
        save_table_of_contents_page(pdf, section_titles)
        save_cover_page(pdf, figures_dir, rows)
        save_text_page(
            pdf,
            "Executive Summary",
            [
                (
                    "",
                    "This submission converts free Sentinel-2 L2A imagery into grower-facing orchard scouting-priority zones. The method identifies parts of each site that persistently underperform relative to the same site's own eligible-canopy baseline across NDVI, NDMI, NDRE, and EVI2.",
                ),
                (
                    "Decision Product",
                    "The output is a grower triage layer that does not necessarily assign cause from the satellite images. Zones identified as Scout first should be visited first, then Monitor zones next. Stable zones provide within-site context, and Strong reference zones provide comparison areas for field follow-up.",
                ),
                (
                    "Trust And Confidence",
                    "Confidence is treated as an operational trust signal, not proof of cause. Stronger zones have enough clear observations, multi-index agreement, persistence across years, and eligible-canopy support. Public-boundary results are intentionally labeled cautious.",
                ),
                (
                    "Values-Aware Use",
                    "Persistent Orchard Underperformance Mapper is a scouting-priority aid for growers, PCAs, crop advisors, and field crews. It converts multi-date Sentinel-2 vegetation evidence into conservative canopy-limited zones that can be checked against field memory, block maps, PCA notes, irrigation records, management records, and in-person scouting.",
                ),
            ],
        )
        save_review_path_page(pdf)
        save_pipeline_workflow_page(pdf)
        save_image_page(
            pdf,
            "All Six Sites",
            figures_dir / "spatial_zone_maps.png",
            "Six-site output overview. Non-canopy pixels are excluded from scoring and shown neutrally or transparently. Public-site interpretation is cautious because crop context may be mixed or unverified.",
            landscape=True,
        )
        save_image_page(
            pdf,
            "Kern 1 Zoomed Map",
            figures_dir / "kern_site_1_report_zone_map.png",
            site_caption("kern_site_1"),
            landscape=True,
        )
        save_image_page(
            pdf,
            "Stanislaus 1 Visual Public-Site Example",
            figures_dir / "stanislaus_site_1_report_zone_map.png",
            "Stanislaus 1 is included as a visually rich public-site example. It is useful for presentation and inspection, but interpretation remains cautious because crop and management context are unverified.",
            landscape=True,
        )
        save_image_page(
            pdf,
            "Partner Site 1 Detail",
            figures_dir / "partner_site_1_report_zone_map.png",
            site_caption("partner_site_1"),
            landscape=True,
        )
        save_image_page(
            pdf,
            "Strong Reference Versus Priority Zone Time Series",
            figures_dir / "partner_site_1_zone_timeseries.png",
            "The strong reference zone and scout-first zone are compared across multiple vegetation signals. Persistence across years is what makes the layer more useful for grower triage than a one-date NDVI screenshot.",
            landscape=True,
        )
        save_image_page(
            pdf,
            "Canopy Mask Guardrail",
            figures_dir / "partner_site_1_canopy_mask_diagnostic.png",
            "The canopy eligibility check makes a central guardrail visible: non-canopy areas are excluded before baselines, persistence scoring, zone polygons, and acreage summaries. This reduces the chance that roads, canals, bare ground, water, or field margins become false scouting-priority zones.",
            landscape=False,
        )
        save_results_table(pdf, rows)
        save_trust_page(pdf, rows)
        save_zone_card_reading_guide(pdf)
        save_zone_evidence_cards(pdf, scouting_rows)
        save_grower_decision_tree_page(pdf)
        save_five_sentence_field_brief_page(pdf)
        save_field_feedback_loop_page(pdf)
        save_text_page(
            pdf,
            "How Additional Data Could Refine The Method",
            [
                (
                    "Not Used In This Run",
                    "The submitted product stays focused on Sentinel-2 canopy-limited persistent underperformance and scouting priority. This run does not ingest CIMIS, ERA5, OpenET, SSURGO, DEM, yield, irrigation, pest, disease, tissue, or soil-lab datasets.",
                ),
                (
                    "Where Additional Data Would Fit",
                    "Additional data would be added after the canopy-priority layer as explanatory context, not as automatic diagnosis. Weather and ET records could guide irrigation-record review; SSURGO or soil tests could flag soil-variability questions; DEM or slope could suggest drainage questions; grower records could separate expected management differences from unexpected weak canopy signals.",
                ),
                (
                    "Safe Workflow",
                    "First map persistent canopy underperformance, then compare it with additional records, then send a scout to verify what is actually happening. Added datasets would need clear dates, field boundaries, resolution notes, and grower context before they could refine confidence.",
                ),
                (
                    "What Still Cannot Be Claimed",
                    "Even with public context layers, the tool would not turn satellite and public data alone into specific agronomic explanations or outcome claims.",
                ),
            ],
        )
        save_grower_work_order_page(pdf)
        save_text_page(
            pdf,
            "Design For Grower Adoption",
            [
                (
                    "One Structured Signal In Existing Practice",
                    "Field memory is always important. The mapper is designed to reduce cognitive burden by adding one structured scouting signal to existing grower and advisor practices, alongside PCA reports, irrigation records, spreadsheets, notes, and local knowledge. The key output is a ranked scouting-priority table and map that helps decide where to look first.",
                ),
                (
                    "Local Control And Portability",
                    "Outputs are deliberately portable: PDF for review, CSV for spreadsheet workflows, GeoJSON for GIS tools, and GeoTIFF rasters for reproducible spatial analysis. The method uses transparent thresholds and open Sentinel-2 inputs instead of a black-box model that would be difficult for a grower or advisor to audit.",
                ),
                (
                    "Assumption Transparency",
                    "The report states what the system can and cannot infer. It detects persistent underperformance relative to eligible canopy pixels inside each site. It does not assign agronomic causes or estimate yield impacts from satellite imagery. Public sites are treated cautiously because crop context may be mixed or unverified.",
                ),
            ],
        )
        save_refinement_with_grower_data_page(pdf)
        for site in ALL_SITE_IDS:
            save_full_image_page(
                pdf,
                f"{site_title(site)} - High-Resolution Map",
                figures_dir / f"{site}_report_zone_map.png",
                site_caption(site),
            )
            save_full_image_page(
                pdf,
                f"{site.replace('_', ' ').title()} Canopy And Priority Overlay",
                figures_dir / f"{site}_canopy_priority_overlay.png",
                "Single-panel readability view: eligible canopy is shown separately from scout-first and monitor zones. Priority colors are clipped to the canopy mask, so roads, canals, bare ground, water, and field margins are not labeled as orchard stress from satellite imagery.",
            )
        save_text_page(
            pdf,
            "Methodology",
            [
                (
                    "Clear-Pixel Filtering",
                    "The pipeline uses Sentinel-2 L2A surface reflectance and keeps only valid observations. When SCL is available, no-data, defective, cloud shadow, cloud, cirrus, snow/ice, and water classes are excluded before vegetation indices are computed.",
                ),
                (
                    "Canopy Eligibility",
                    "The canopy mask is built from multi-date evidence: minimum clear observations, NDVI median, NDVI 75th percentile, and an EVI2 75th-percentile backup. Baseline statistics, persistence scoring, zone maps, and acreage estimates use eligible canopy pixels only.",
                ),
                (
                    "Within-Site Baseline",
                    "NDVI, NDMI, NDRE, and EVI2 are robustly standardized relative to each site's own eligible-canopy seasonal distribution. This detects persistent underperformance relative to local site context instead of comparing different orchards or public patches directly.",
                ),
                (
                    "Persistent Multi-Index Underperformance",
                    "A pixel becomes a scout-first zone only when underperformance is persistent across years, supported by multiple indices, and observed with sufficient confidence. Small isolated patches are filtered so the final output reads more like a management-zone layer than pixel noise.",
                ),
            ],
        )
        save_text_page(
            pdf,
            "Grower Use And Limitations",
            [
                (
                    "Grower Workflow",
                    "Use these maps to prioritize scouting. Field verification is required to determine cause. A grower or advisor can visit scout-first zones, compare them against nearby strong reference zones, and review canopy condition, irrigation distribution, pest signs, soil variability, and management records.",
                ),
                (
                    "Limitations",
                    "There is no verified yield ground truth, no pest or disease confirmation, no irrigation-system data, no soil or tissue validation, and no management-record validation in this run. Public sites may be mixed or unverified, so their maps are scouting-priority examples rather than orchard-specific conclusions.",
                ),
                (
                    "Reproducibility",
                    "The pipeline is script-based and uses open data sources. Rebuild instructions, spatial outputs, figures, methodology notes, and the scouting-priority table are produced locally from the same scripts.",
                ),
            ],
        )
    apply_pdf_navigation(out_path, section_titles)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final F3 technical report PDF.")
    parser.add_argument("--figures-dir", default="output/figures")
    parser.add_argument("--spatial-dir", default="output/spatial")
    parser.add_argument("--output", default="submission/report/final_technical_report.pdf")
    return parser.parse_args()


def main() -> None:
    build_report(parse_args())


if __name__ == "__main__":
    main()
