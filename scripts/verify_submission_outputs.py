"""Verify local F3 submission outputs before packaging."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

import numpy as np
import rasterio


ALL_SITE_IDS = [
    "fresno_site_1",
    "kern_site_1",
    "kings_site_1",
    "partner_site_1",
    "stanislaus_site_1",
    "tulare_site_1",
]

LIVE_MAP_LINK = "https://f3-orchard-stress-web.vercel.app"

CRITICAL_FIGURE_DIMENSIONS = {
    "kern_site_1_report_zone_map.png": (1000, 700),
    "stanislaus_site_1_report_zone_map.png": (1000, 700),
    "partner_site_1_report_zone_map.png": (1000, 700),
    "spatial_zone_maps.png": (1500, 900),
}

GROWER_WORK_ORDER_COLUMNS = {
    "site_id",
    "site_display_name",
    "work_order_rank",
    "zone_id",
    "priority_class",
    "approx_area_acres",
    "persistence_score",
    "indices_triggered",
    "valid_observation_count",
    "mean_relative_underperformance",
    "centroid_lat",
    "centroid_lon",
    "map_file",
    "comparison_instruction",
    "suggested_first_action",
    "estimated_visit_minutes",
    "records_to_check",
    "field_observations_to_make",
    "what_to_write_down",
    "overclaim_guardrail",
}

FIELD_VERIFICATION_COLUMNS = {
    "date",
    "scout_name",
    "site_id",
    "zone_id",
    "priority_class",
    "start_lat",
    "start_lon",
    "actual_minutes",
    "visible_canopy_difference",
    "compared_to_strong_reference",
    "field_memory_or_known_context",
    "irrigation_distribution_observation",
    "pest_or_disease_symptom_observation",
    "soil_or_water_movement_observation",
    "photos_taken",
    "finding_label",
    "followup_owner",
    "notes",
}

VALIDATION_SAMPLING_COLUMNS = {
    "site_id",
    "site_display_name",
    "sample_rank",
    "sample_type",
    "zone_id",
    "priority_class",
    "approx_area_acres",
    "persistence_score",
    "indices_triggered",
    "valid_observation_count",
    "mean_relative_underperformance",
    "start_lat",
    "start_lon",
    "map_file",
    "selection_reason",
    "comparison_instruction",
    "field_observations_to_make",
    "overclaim_guardrail",
}

PROHIBITED_CLAIM_PATTERNS = [
    re.compile(r"\bdiagnos(?:e|es|ed|ing|is)\b", re.IGNORECASE),
    re.compile(
        r"\b(yield loss|pest pressure|irrigation failure|soil problem|soil limitation|nutrient deficiency|nutrient status|tissue status|root cause)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bverified ground truth\b", re.IGNORECASE),
    re.compile(r"\bfull statistical accuracy\b", re.IGNORECASE),
    re.compile(
        r"\b(detects?|detected|maps?|mapped|confirms?|confirmed|predicts?|predicted)\b.{0,80}\b(disease|pests?|irrigation failure|yield loss|soil problem|nutrient deficiency|nutrient status|tissue status)\b",
        re.IGNORECASE,
    ),
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_fieldnames(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        return set(csv.DictReader(f).fieldnames or [])


def verify_required_columns(errors: list[str], path: Path, required_columns: set[str], label: str) -> None:
    assert_exists(errors, path, label)
    if not path.exists():
        return
    missing = required_columns - csv_fieldnames(path)
    if missing:
        fail(errors, f"{path.relative_to(path.parents[2])} missing columns: {sorted(missing)}")


def assert_exists(errors: list[str], path: Path, label: str) -> None:
    if not path.exists():
        fail(errors, f"Missing {label}: {path}")
    elif path.is_file() and path.stat().st_size == 0:
        fail(errors, f"Empty {label}: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_site_tables(errors: list[str], tables_dir: Path) -> None:
    summary_path = tables_dir / "spatial_zone_summary.csv"
    scouting_path = tables_dir / "scouting_priority_table.csv"
    assert_exists(errors, summary_path, "six-site spatial summary table")
    assert_exists(errors, scouting_path, "scouting priority table")

    summary_rows = read_csv(summary_path)
    summary_sites = {row.get("site", "") for row in summary_rows}
    for site in ALL_SITE_IDS:
        if site not in summary_sites:
            fail(errors, f"{site} missing from spatial_zone_summary.csv")

    if scouting_path.exists():
        required_cols = {
            "site_id",
            "zone_id",
            "approx_area_acres",
            "persistence_score",
            "indices_triggered",
            "valid_observation_count",
            "mean_relative_underperformance",
            "centroid_lat",
            "centroid_lon",
            "recommended_followup",
        }
        with scouting_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = required_cols - set(reader.fieldnames or [])
            if missing:
                fail(errors, f"scouting_priority_table.csv missing columns: {sorted(missing)}")


def verify_site_artifacts(errors: list[str], geodata_dir: Path, figures_dir: Path) -> None:
    for site in ALL_SITE_IDS:
        assert_exists(errors, figures_dir / f"{site}_report_zone_map.png", f"{site} high-resolution report map")
        assert_exists(errors, figures_dir / f"{site}_canopy_priority_overlay.png", f"{site} readable canopy priority overlay")
        assert_exists(errors, figures_dir / f"{site}_canopy_mask_diagnostic.png", f"{site} canopy diagnostic")
        assert_exists(errors, geodata_dir / f"{site}_zones.tif", f"{site} zone raster")
        assert_exists(errors, geodata_dir / f"{site}_zones.geojson", f"{site} zone GeoJSON")
        assert_exists(errors, geodata_dir / f"{site}_canopy_mask.tif", f"{site} canopy mask raster")
        assert_exists(errors, geodata_dir / f"{site}_underperformance_mask.tif", f"{site} underperformance mask raster")


def verify_critical_figure_dimensions(errors: list[str], figures_dir: Path) -> None:
    try:
        from PIL import Image
    except Exception as exc:
        fail(errors, f"PIL unavailable for critical figure dimension checks: {exc}")
        return

    for filename, (min_width, min_height) in CRITICAL_FIGURE_DIMENSIONS.items():
        path = figures_dir / filename
        assert_exists(errors, path, f"critical figure {filename}")
        if not path.exists():
            continue
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception as exc:
            fail(errors, f"Could not read critical figure dimensions for {filename}: {exc}")
            continue
        if width < min_width or height < min_height:
            fail(
                errors,
                f"{filename} is unexpectedly small ({width}x{height}); expected at least {min_width}x{min_height}",
            )


def verify_masks(errors: list[str], spatial_dir: Path) -> None:
    for site in ALL_SITE_IDS:
        canopy_path = spatial_dir / f"{site}_canopy_mask.tif"
        under_path = spatial_dir / f"{site}_underperformance_mask.tif"
        zones_path = spatial_dir / f"{site}_zones.tif"
        score_path = spatial_dir / f"{site}_underperformance_score.tif"
        if not (canopy_path.exists() and under_path.exists()):
            continue
        with rasterio.open(canopy_path) as canopy_src, rasterio.open(under_path) as under_src:
            canopy = canopy_src.read(1) > 0
            under = under_src.read(1) > 0
            if canopy.shape != under.shape:
                fail(errors, f"{site} canopy and underperformance masks have different shapes")
                continue
            outside = under & ~canopy
            if bool(outside.any()):
                fail(errors, f"{site} has {int(outside.sum())} underperformance pixels outside canopy mask")

        if zones_path.exists():
            with rasterio.open(canopy_path) as canopy_src, rasterio.open(zones_path) as zones_src:
                canopy = canopy_src.read(1) > 0
                zones = zones_src.read(1) > 0
                outside = zones & ~canopy
                if bool(outside.any()):
                    fail(errors, f"{site} has {int(outside.sum())} zone pixels outside canopy mask")

        if score_path.exists():
            with rasterio.open(canopy_path) as canopy_src, rasterio.open(score_path) as score_src:
                canopy = canopy_src.read(1) > 0
                score = score_src.read(1)
                finite_outside = np.isfinite(score) & ~canopy
                if bool(finite_outside.any()):
                    fail(errors, f"{site} has {int(finite_outside.sum())} finite score pixels outside canopy mask")


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(str(pdf_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def allowed_context(line: str) -> bool:
    lowered = line.lower()
    allowed_markers = [
        "not ",
        "no ",
        "do not",
        "does not",
        "cannot",
        "without",
        "field",
        "follow-up",
        "verification",
        "validation",
        "confirmation",
        "compare",
        "review",
        "signs",
        "variability",
        "limitations",
        "not claim",
        "would not claim",
        "required to determine cause",
        "not a diagnosis",
        "not as proof",
        "not a full",
        "guardrail",
    ]
    return any(marker in lowered for marker in allowed_markers)


def verify_no_prohibited_claims(errors: list[str], label: str, text: str) -> None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(pattern.search(stripped) for pattern in PROHIBITED_CLAIM_PATTERNS) and not allowed_context(stripped):
            fail(errors, f"Possible diagnostic overclaiming language in {label}: {stripped[:180]}")


def verify_no_local_paths(errors: list[str], paths: list[Path]) -> None:
    for path in paths:
        assert_exists(errors, path, path.name)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "C:/Users" in text or "C:\\Users" in text:
            fail(errors, f"{path.relative_to(path.parents[2])} contains a local C:/Users path")


def verify_readme_artifacts(errors: list[str], root: Path) -> None:
    readme_path = root / "README.md"
    assert_exists(errors, readme_path, "README.md")
    if not readme_path.exists():
        return
    text = readme_path.read_text(encoding="utf-8")
    match = re.search(r"## Submission Map\s+(.*?)(?:\n## |\Z)", text, re.DOTALL)
    if not match:
        match = re.search(r"## Current Best Artifacts\s+(.*?)(?:\n## |\Z)", text, re.DOTALL)
    if not match:
        fail(errors, "README.md missing Submission Map or Current Best Artifacts section")
        return
    artifact_section = match.group(1)
    for rel_path in re.findall(r"`([^`]+\.[A-Za-z0-9]+)`", artifact_section):
        if rel_path.startswith(("http://", "https://")):
            continue
        artifact_path = root / rel_path
        assert_exists(errors, artifact_path, f"README artifact {rel_path}")


def verify_markdown_links(errors: list[str], markdown_path: Path) -> None:
    assert_exists(errors, markdown_path, markdown_path.name)
    if not markdown_path.exists():
        return
    text = markdown_path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\[[^\]]*]\(([^)]+)\)", text):
        target = target.strip()
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:"))
            or "*" in target
        ):
            continue
        target = target.split("#", 1)[0]
        target = target.strip("<>")
        link_path = (markdown_path.parent / target).resolve()
        assert_exists(errors, link_path, f"Markdown link {target} in {markdown_path.relative_to(markdown_path.parents[1])}")


def verify_submission_packet(errors: list[str], root: Path) -> None:
    required_paths = [
        root / "requirements_workspace" / "README.md",
        root / "requirements_workspace" / "requirements_checklist.md",
        root / "requirements_workspace" / "reproducibility.md",
        root / "requirements_workspace" / "requirements.lock",
        root / "requirements_workspace" / "environment.yml",
        root / "requirements_workspace" / "reference" / "dc2-challenge" / "README.md",
        root / "submission" / "README.md",
        root / "submission" / "grower_quickstart.html",
        root / "submission" / "report" / "final_technical_report.pdf",
        root / "submission" / "report" / "judge_review_guide.md",
        root / "submission" / "report" / "presentation_report.md",
        root / "submission" / "tables" / "scouting_priority_table.csv",
        root / "submission" / "tables" / "spatial_zone_summary.csv",
        root / "submission" / "tables" / "zone_timeseries_all_sites.csv",
        root / "submission" / "figures" / "spatial_zone_maps.png",
        root / "submission" / "figures" / "pipeline_diagram.png",
        root / "submission" / "geodata" / "methodology_notes.json",
    ]
    for path in required_paths:
        assert_exists(errors, path, f"organized packet file {path.relative_to(root)}")

    for site in ALL_SITE_IDS:
        for suffix in [
            "_report_zone_map.png",
            "_canopy_priority_overlay.png",
            "_canopy_mask_diagnostic.png",
            "_zone_timeseries.png",
        ]:
            assert_exists(errors, root / "submission" / "figures" / f"{site}{suffix}", f"{site} submission figure {suffix}")
        for suffix in [
            "_zones.geojson",
            "_zones.tif",
            "_canopy_mask.tif",
            "_underperformance_mask.tif",
            "_underperformance_score.tif",
            "_valid_observation_count.tif",
        ]:
            assert_exists(errors, root / "submission" / "geodata" / f"{site}{suffix}", f"{site} submission geodata {suffix}")


def verify_grower_work_order_outputs(errors: list[str], root: Path, report_text: str) -> None:
    tables_dir = root / "submission" / "tables"
    report_dir = root / "submission" / "report"
    work_orders_path = tables_dir / "grower_work_orders.csv"
    field_form_path = tables_dir / "field_verification_form_template.csv"
    validation_plan_path = tables_dir / "validation_sampling_plan.csv"
    work_orders_md_path = report_dir / "grower_work_orders.md"

    verify_required_columns(errors, work_orders_path, GROWER_WORK_ORDER_COLUMNS, "grower work orders table")
    verify_required_columns(errors, field_form_path, FIELD_VERIFICATION_COLUMNS, "field verification form template")
    verify_required_columns(errors, validation_plan_path, VALIDATION_SAMPLING_COLUMNS, "validation sampling plan")
    assert_exists(errors, work_orders_md_path, "grower work orders markdown")

    if work_orders_path.exists():
        rows = read_csv(work_orders_path)
        sites = {row.get("site_id", "") for row in rows}
        for site in ALL_SITE_IDS:
            if site not in sites:
                fail(errors, f"{site} missing from grower_work_orders.csv")
        for site in ALL_SITE_IDS:
            site_rows = [row for row in rows if row.get("site_id") == site]
            if len(site_rows) > 5:
                fail(errors, f"{site} has more than five displayed work-order rows")
        kern_rows = [row for row in rows if row.get("site_id") == "kern_site_1"]
        if any(row.get("priority_class") == "Scout first" for row in kern_rows):
            fail(errors, "Kern work order should not include Scout first rows")

    if validation_plan_path.exists():
        plan_rows = read_csv(validation_plan_path)
        sample_types_by_site: dict[str, set[str]] = {}
        for row in plan_rows:
            sample_types_by_site.setdefault(row.get("site_id", ""), set()).add(row.get("sample_type", ""))
        for site in ALL_SITE_IDS:
            types = sample_types_by_site.get(site, set())
            if "Strong reference agreement sample" not in types:
                fail(errors, f"{site} validation plan missing Strong reference sample")
            if "Stable missed-signal check" not in types:
                fail(errors, f"{site} validation plan missing Stable sample")

    if work_orders_md_path.exists():
        md_text = work_orders_md_path.read_text(encoding="utf-8")
        lowered = md_text.lower()
        if "not a diagnosis tool" not in lowered and "does not assign cause from satellite imagery" not in lowered:
            fail(errors, "grower_work_orders.md missing non-diagnostic guardrail")
        if "route planning" in lowered or "route plan" in lowered:
            fail(errors, "grower_work_orders.md uses route-planning language without access geometry")
        if "kern site 1 is a small-boundary low-priority result" not in lowered:
            fail(errors, "grower_work_orders.md does not frame Kern as low-priority")
        if "partner site 1 is the clearest orchard-specific example" not in lowered:
            fail(errors, "grower_work_orders.md does not keep partner_site_1 as the clearest orchard-specific example")
        verify_no_prohibited_claims(errors, "grower_work_orders.md", md_text)

    verify_no_prohibited_claims(errors, "submission report/source text", report_text)
    verify_no_local_paths(
        errors,
        [
            root / "README.md",
            root / "submission" / "README.md",
            root / "submission" / "report" / "presentation_report.md",
            work_orders_md_path,
        ],
    )


def verify_stale_report_copy(errors: list[str], presentation_paths: list[Path]) -> None:
    stale_patterns = [
        "Processed three sites",
        "three-site",
        "--sites partner_site_1 kings_site_1 tulare_site_1",
        "C:/Users",
        "C:\\Users",
    ]
    for presentation_path in presentation_paths:
        assert_exists(errors, presentation_path, "presentation report")
        if not presentation_path.exists():
            continue
        text = presentation_path.read_text(encoding="utf-8")
        for pattern in stale_patterns:
            if pattern in text:
                fail(errors, f"{presentation_path.relative_to(presentation_path.parents[2])} contains stale text: {pattern}")


def verify_grower_quick_start(errors: list[str], root: Path, report_text: str) -> None:
    required_files = [
        root / "README.md",
        root / "submission" / "README.md",
        root / "submission" / "report" / "presentation_report.md",
    ]
    for path in required_files:
        assert_exists(errors, path, path.name)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "Grower Quick Start" not in text:
            fail(errors, f"{path.relative_to(root)} missing Grower Quick Start")
        if "Do not assign cause from the satellite layer alone" not in text:
            fail(errors, f"{path.relative_to(root)} missing satellite-layer cause guardrail")

    if "Grower Quick Start" not in report_text:
        fail(errors, "final report/source text missing Grower Quick Start")
    if "High confidence means" not in report_text and "good place to look first" not in report_text:
        fail(errors, "final report/source text missing plain-English confidence interpretation")
    if "Do not assign cause from the satellite layer alone" not in report_text:
        fail(errors, "final report/source text missing satellite-layer cause guardrail")
    for required in [
        LIVE_MAP_LINK,
        "Live field map",
        "Open the Vercel field map",
        "Choose a boundary",
        "use this PDF",
    ]:
        if required not in report_text:
            fail(errors, f"final report/source text missing live-map instruction: {required}")


def verify_quickstart_webpage(errors: list[str], root: Path) -> None:
    html_path = root / "submission" / "grower_quickstart.html"
    assert_exists(errors, html_path, "standalone grower quickstart webpage")
    if not html_path.exists():
        return
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    for required in [
        "Practical Example Field Brief",
        "Decision Tree",
        "Who Gets Which Output",
        "Canopy Guardrail",
        "Explorar primero",
        "data:image/png;base64",
        "field reality",
    ]:
        if required not in text:
            fail(errors, f"grower_quickstart.html missing required content: {required}")
    if "C:/Users" in text or "C:\\Users" in text:
        fail(errors, "grower_quickstart.html contains a local C:/Users path")


def verify_review_path(errors: list[str], root: Path, report_text: str) -> None:
    guide_path = root / "submission" / "report" / "judge_review_guide.md"
    assert_exists(errors, guide_path, "review guide")

    guide_text = guide_path.read_text(encoding="utf-8", errors="ignore") if guide_path.exists() else ""
    combined = "\n".join([guide_text, report_text])

    for required in [
        "Review Path",
        "Review Read",
        "Sentinel-2",
        "Is it reproducible?",
        "grower",
        "refinement path",
        "partner_site_1",
    ]:
        if required not in combined:
            fail(errors, f"review path missing required content: {required}")

    verify_no_local_paths(errors, [guide_path])
    verify_no_prohibited_claims(errors, "review guide", guide_text)


def verify_report_language(errors: list[str], report_path: Path, source_paths: list[Path]) -> str:
    assert_exists(errors, report_path, "final technical report PDF")
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())
    pdf_text = extract_pdf_text(report_path)
    text = "\n".join([source_text, pdf_text])
    root = Path(__file__).resolve().parents[1]

    for site in ALL_SITE_IDS:
        if site not in text and site.replace("_", " ").title() not in text:
            fail(errors, f"{site} missing from report source/text")
    if "strongest orchard-specific example" not in text:
        fail(errors, "partner_site_1 is not framed as the strongest orchard-specific example")
    if "Interpretation is cautious" not in text and "interpret cautiously" not in text:
        fail(errors, "public-site cautious interpretation language missing")
    if "operational trust signal" not in text and "Confidence is operational" not in text:
        fail(errors, "confidence/trust interpretation language missing")
    if "Zone Evidence Cards" not in text:
        fail(errors, "partner-site zone evidence cards language missing")
    if "Kern 1" not in text and "kern_site_1" not in text:
        fail(errors, "Kern 1 small-site interpretation missing")
    verify_grower_quick_start(errors, root, text)
    for required in [
        "Review Path",
        "Grower Decision Tree",
        "Practical Example Field Brief",
        "Field Feedback Loop",
        "How Additional Data Could Refine The Method",
        "Spanish Option",
        "followup_owner",
    ]:
        if required not in text:
            fail(errors, f"final report/source text missing grower-applicability addition: {required}")

    verify_no_prohibited_claims(errors, "final report/source text", text)
    return text


def verify_vault_assets(errors: list[str], root: Path, vault_dir: Path) -> None:
    submission_figures_dir = root / "submission" / "figures"
    vault_figures_dir = vault_dir / "figures"
    assert_exists(errors, vault_figures_dir, "vault figures directory")
    if vault_figures_dir.exists():
        for src in sorted(submission_figures_dir.glob("*.png")):
            if not src.is_file():
                continue
            dst = vault_figures_dir / src.name
            assert_exists(errors, dst, f"vault figure copy {src.name}")
            if dst.exists() and sha256_file(src) != sha256_file(dst):
                fail(errors, f"vault figure hash mismatch: {src.name}")

    deliverables_dir = vault_dir / "03 Deliverables"
    assert_exists(errors, deliverables_dir / "final_technical_report.pdf", "vault final technical report PDF")
    assert_exists(errors, deliverables_dir / "judge_review_guide.md", "vault review guide")
    assert_exists(errors, deliverables_dir / "spatial_zone_summary.csv", "vault spatial summary table")
    assert_exists(errors, deliverables_dir / "scouting_priority_table.csv", "vault scouting priority table")
    assert_exists(errors, deliverables_dir / "grower_work_orders.md", "vault grower work orders markdown")
    assert_exists(errors, deliverables_dir / "grower_quickstart.html", "vault grower quickstart webpage")
    assert_exists(errors, deliverables_dir / "grower_work_orders.csv", "vault grower work orders table")
    assert_exists(errors, deliverables_dir / "field_verification_form_template.csv", "vault field verification form template")
    assert_exists(errors, deliverables_dir / "validation_sampling_plan.csv", "vault validation sampling plan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=None,
        help="Optional Obsidian F3 project folder for downstream asset verification.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    geodata_dir = root / "submission" / "geodata"
    figures_dir = root / "submission" / "figures"
    tables_dir = root / "submission" / "tables"
    report_dir = root / "submission" / "report"
    report_path = report_dir / "final_technical_report.pdf"
    errors: list[str] = []

    verify_site_tables(errors, tables_dir)
    verify_site_artifacts(errors, geodata_dir, figures_dir)
    verify_critical_figure_dimensions(errors, figures_dir)
    verify_masks(errors, geodata_dir)
    verify_readme_artifacts(errors, root)
    verify_submission_packet(errors, root)
    for markdown_path in [
        root / "README.md",
        root / "submission" / "README.md",
        root / "submission" / "report" / "judge_review_guide.md",
        root / "requirements_workspace" / "README.md",
        root / "requirements_workspace" / "requirements_checklist.md",
    ]:
        verify_markdown_links(errors, markdown_path)
    verify_stale_report_copy(
        errors,
        [
            root / "submission" / "report" / "presentation_report.md",
        ],
    )
    verify_quickstart_webpage(errors, root)
    report_text = verify_report_language(
        errors,
        report_path,
        [
            root / "README.md",
            root / "requirements_workspace" / "requirements_checklist.md",
            root / "submission" / "README.md",
            root / "submission" / "report" / "judge_review_guide.md",
            root / "submission" / "report" / "presentation_report.md",
            root / "submission" / "report" / "grower_work_orders.md",
            root / "scripts" / "build_final_report_pdf.py",
        ],
    )
    verify_review_path(errors, root, report_text)
    verify_grower_work_order_outputs(errors, root, report_text)
    if args.vault_dir is not None:
        verify_vault_assets(errors, root, args.vault_dir)

    if errors:
        print("Submission verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Submission verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
