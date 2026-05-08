"""Build low-burden grower work orders from submitted scouting-priority outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLES_DIR = ROOT / "submission" / "tables"
DEFAULT_GEODATA_DIR = ROOT / "submission" / "geodata"
DEFAULT_REPORT_DIR = ROOT / "submission" / "report"

SITE_ORDER = [
    "partner_site_1",
    "fresno_site_1",
    "kern_site_1",
    "kings_site_1",
    "stanislaus_site_1",
    "tulare_site_1",
]

VISIT_BASE_MINUTES = 12
VISIT_MINUTES_PER_ACRE = 4
VISIT_MINUTES_MIN = 12
VISIT_MINUTES_MAX = 45

WORK_ORDER_COLUMNS = [
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
]

FIELD_FORM_COLUMNS = [
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
]

VALIDATION_COLUMNS = [
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
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fmt_float(value: Any, digits: int = 3, blank_zero: bool = False) -> str:
    number = safe_float(value, 0.0)
    if blank_zero and math.isclose(number, 0.0):
        return ""
    return f"{number:.{digits}f}"


def fmt_coord(value: Any) -> str:
    if value in (None, ""):
        return ""
    return f"{safe_float(value):.7f}"


def site_display_name(site_id: str) -> str:
    if site_id == "partner_site_1":
        return "Partner Site 1 orchard-specific example"
    if site_id == "kern_site_1":
        return "Kern Site 1 small-boundary low-priority result"
    label = site_id.replace("_", " ").title()
    return f"{label} public boundary - cautious interpretation"


def site_context_sentence(site_id: str) -> str:
    if site_id == "partner_site_1":
        return "Partner Site 1 is the clearest orchard-specific example in this packet."
    if site_id == "kern_site_1":
        return (
            "Kern Site 1 is a small-boundary low-priority result, not necessarily a failed map: "
            "19.62 eligible canopy acres and 0.00 Scout first acres."
        )
    return "This is a public boundary; interpret the work order cautiously because crop and management context are unverified."


def canonical_class(priority_class: str) -> str:
    lowered = priority_class.lower().strip()
    if lowered.startswith("stable"):
        return "Stable"
    if lowered.startswith("strong"):
        return "Strong reference"
    if lowered == "scout first":
        return "Scout first"
    if lowered == "monitor":
        return "Monitor"
    return priority_class.strip()


def map_file(site_id: str) -> str:
    return f"submission/figures/{site_id}_report_zone_map.png"


def records_to_check(site_id: str) -> str:
    if site_id == "partner_site_1":
        return "field memory; block map; recent scouting notes; irrigation set records; PCA or crop-advisor notes; management records"
    return "field memory and records if available; public-boundary context; avoid inferring crop or management history"


def field_observations_to_make() -> str:
    return (
        "visible canopy difference; irrigation distribution observation; pest or disease symptom observation; "
        "soil or water movement observation; photos if useful"
    )


def what_to_write_down() -> str:
    return (
        "actual minutes; visible difference yes/no/unclear; records checked; photos taken; "
        "finding_label; followup_owner only if field symptoms or records support follow-up"
    )


def overclaim_guardrail() -> str:
    return "Satellite imagery only prioritizes scouting; field verification determines cause. This is not a diagnosis tool."


def visit_minutes(area_acres: Any, priority_class: str) -> int:
    area = max(0.0, safe_float(area_acres))
    estimate = VISIT_BASE_MINUTES + VISIT_MINUTES_PER_ACRE * area
    if canonical_class(priority_class) in {"Stable", "Strong reference"}:
        estimate = min(estimate, 18)
    return int(round(max(VISIT_MINUTES_MIN, min(VISIT_MINUTES_MAX, estimate))))


def comparison_instruction(priority_class: str, site_id: str) -> str:
    cls = canonical_class(priority_class)
    if cls == "Scout first":
        return "Compare this starting coordinate with a nearby Strong reference area or stable canopy before deciding follow-up."
    if cls == "Monitor":
        if site_id == "kern_site_1":
            return "Low-priority check; compare to Strong reference or stable canopy only if already nearby or time allows."
        return "Check after Scout first zones if time allows; compare to Strong reference or stable canopy before escalating."
    if cls == "Strong reference":
        return "Use this area as the green comparison area for Scout first or Monitor zones."
    if cls == "Stable":
        return "Use this area as a conservative stable-canopy comparison or missed-signal check."
    return "Compare against nearby Strong reference or stable canopy before deciding follow-up."


def suggested_first_action(priority_class: str, site_id: str) -> str:
    cls = canonical_class(priority_class)
    if cls == "Scout first":
        return "Send a scout to the starting coordinate and walk the visible canopy around it first."
    if cls == "Monitor":
        if site_id == "kern_site_1":
            return "Low-priority check if nearby; confirm there is no obvious visible concern before spending more time."
        return "Check after Scout first zones if access and field time allow."
    if cls == "Strong reference":
        return "Use as a comparison area before assigning any follow-up."
    if cls == "Stable":
        return "Use as a stable-canopy check; no action unless field observation suggests otherwise."
    return "Use as a field navigation prompt, not a diagnosis."


def class_rank(priority_class: str) -> int:
    return {
        "Scout first": 0,
        "Monitor": 1,
        "Strong reference": 2,
        "Stable": 3,
    }.get(canonical_class(priority_class), 9)


def sort_zone_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            class_rank(row.get("priority_class", "")),
            -safe_float(row.get("persistence_score")),
            -safe_float(row.get("approx_area_acres")),
            -safe_float(row.get("mean_relative_underperformance")),
            row.get("zone_id", ""),
        ),
    )


def polygon_ring_centroid(ring: list[list[float]]) -> tuple[float, float, float] | None:
    if len(ring) < 3:
        return None
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for idx in range(len(ring) - 1):
        x0, y0 = ring[idx][:2]
        x1, y1 = ring[idx + 1][:2]
        cross = x0 * y1 - x1 * y0
        signed_area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    signed_area *= 0.5
    if math.isclose(signed_area, 0.0):
        return None
    cx /= 6.0 * signed_area
    cy /= 6.0 * signed_area
    return cx, cy, abs(signed_area)


def geometry_centroid(geometry: dict[str, Any]) -> tuple[str, str]:
    geom_type = geometry.get("type", "")
    coordinates = geometry.get("coordinates", [])
    rings: list[list[list[float]]] = []
    if geom_type == "Polygon":
        if coordinates:
            rings.append(coordinates[0])
    elif geom_type == "MultiPolygon":
        for polygon in coordinates:
            if polygon:
                rings.append(polygon[0])

    weighted_lon = 0.0
    weighted_lat = 0.0
    total_area = 0.0
    fallback_points: list[list[float]] = []
    for ring in rings:
        fallback_points.extend(point for point in ring if len(point) >= 2)
        centroid = polygon_ring_centroid(ring)
        if centroid is None:
            continue
        lon, lat, area = centroid
        weighted_lon += lon * area
        weighted_lat += lat * area
        total_area += area

    if total_area > 0:
        return fmt_coord(weighted_lat / total_area), fmt_coord(weighted_lon / total_area)

    if fallback_points:
        lon = sum(point[0] for point in fallback_points) / len(fallback_points)
        lat = sum(point[1] for point in fallback_points) / len(fallback_points)
        return fmt_coord(lat), fmt_coord(lon)

    return "", ""


def geojson_zone_id(site_id: str, priority_class: str, patch_id: Any) -> str:
    slug = canonical_class(priority_class).lower().replace(" ", "_")
    patch = safe_int(patch_id)
    if patch:
        return f"{site_id}_{slug}_{patch:03d}"
    return f"{site_id}_{slug}"


def reference_candidate(site_id: str, feature: dict[str, Any]) -> dict[str, str]:
    props = feature.get("properties", {})
    priority_class = canonical_class(str(props.get("zone_class", "")))
    lat, lon = geometry_centroid(feature.get("geometry", {}))
    return {
        "site_id": site_id,
        "zone_id": geojson_zone_id(site_id, priority_class, props.get("patch_id")),
        "priority_class": priority_class,
        "approx_area_acres": fmt_float(props.get("acres_est")),
        "persistence_score": fmt_float(props.get("mean_persistence")),
        "indices_triggered": "",
        "valid_observation_count": "",
        "mean_relative_underperformance": "",
        "centroid_lat": lat,
        "centroid_lon": lon,
        "map_file": map_file(site_id),
    }


def load_reference_zones(geodata_dir: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    by_site: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for path in sorted(geodata_dir.glob("*_zones.geojson")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            site_id = str(props.get("site") or path.name.removesuffix("_zones.geojson"))
            cls = canonical_class(str(props.get("zone_class", "")))
            if cls not in {"Stable", "Strong reference"}:
                continue
            by_site[site_id][cls].append(reference_candidate(site_id, feature))

    for site_refs in by_site.values():
        for cls, rows in site_refs.items():
            rows.sort(
                key=lambda row: (
                    -safe_float(row.get("approx_area_acres")),
                    -safe_float(row.get("persistence_score")),
                    row.get("zone_id", ""),
                )
            )
    return by_site


def scouting_candidate(row: dict[str, str]) -> dict[str, str]:
    site_id = row.get("site_id", "")
    return {
        "site_id": site_id,
        "zone_id": row.get("zone_id", ""),
        "priority_class": canonical_class(row.get("priority_class", "")),
        "approx_area_acres": fmt_float(row.get("approx_area_acres")),
        "persistence_score": fmt_float(row.get("persistence_score")),
        "indices_triggered": row.get("indices_triggered", ""),
        "valid_observation_count": fmt_float(row.get("valid_observation_count"), digits=1),
        "mean_relative_underperformance": fmt_float(row.get("mean_relative_underperformance"), digits=4),
        "centroid_lat": fmt_coord(row.get("centroid_lat")),
        "centroid_lon": fmt_coord(row.get("centroid_lon")),
        "map_file": map_file(site_id),
    }


def add_execution_fields(row: dict[str, str], rank: int) -> dict[str, str]:
    site_id = row["site_id"]
    priority_class = row["priority_class"]
    enriched = {
        **row,
        "site_display_name": site_display_name(site_id),
        "work_order_rank": str(rank),
        "comparison_instruction": comparison_instruction(priority_class, site_id),
        "suggested_first_action": suggested_first_action(priority_class, site_id),
        "estimated_visit_minutes": str(visit_minutes(row.get("approx_area_acres"), priority_class)),
        "records_to_check": records_to_check(site_id),
        "field_observations_to_make": field_observations_to_make(),
        "what_to_write_down": what_to_write_down(),
        "overclaim_guardrail": overclaim_guardrail(),
    }
    return {column: enriched.get(column, "") for column in WORK_ORDER_COLUMNS}


def ordered_sites(summary_rows: list[dict[str, str]], scouting_by_site: dict[str, list[dict[str, str]]]) -> list[str]:
    site_ids = {row.get("site", "") for row in summary_rows}
    site_ids.update(scouting_by_site.keys())
    ordered = [site for site in SITE_ORDER if site in site_ids]
    ordered.extend(sorted(site for site in site_ids if site and site not in SITE_ORDER))
    return ordered


def build_work_orders(
    summary_rows: list[dict[str, str]],
    scouting_by_site: dict[str, list[dict[str, str]]],
    references_by_site: dict[str, dict[str, list[dict[str, str]]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for site_id in ordered_sites(summary_rows, scouting_by_site):
        site_rows = sort_zone_rows(scouting_by_site.get(site_id, []))
        has_scout_first = any(row.get("priority_class") == "Scout first" for row in site_rows)
        selected: list[dict[str, str]]
        if has_scout_first:
            selected = site_rows[:5]
        else:
            monitor_rows = [row for row in site_rows if row.get("priority_class") == "Monitor"]
            selected = monitor_rows[:1]
            selected.extend(references_by_site.get(site_id, {}).get("Strong reference", [])[:1])
            selected.extend(references_by_site.get(site_id, {}).get("Stable", [])[:1])
            selected = selected[:5]

        for rank, row in enumerate(selected, start=1):
            rows.append(add_execution_fields(row, rank))
    return rows


def validation_row(row: dict[str, str], sample_rank: int, sample_type: str, reason: str) -> dict[str, str]:
    site_id = row.get("site_id", "")
    priority_class = row.get("priority_class", "")
    start_lat = row.get("centroid_lat", "")
    start_lon = row.get("centroid_lon", "")
    if not start_lat or not start_lon:
        reason = "use map to select nearby green/stable comparison area"
    output = {
        "site_id": site_id,
        "site_display_name": site_display_name(site_id),
        "sample_rank": str(sample_rank),
        "sample_type": sample_type,
        "zone_id": row.get("zone_id", ""),
        "priority_class": priority_class,
        "approx_area_acres": row.get("approx_area_acres", ""),
        "persistence_score": row.get("persistence_score", ""),
        "indices_triggered": row.get("indices_triggered", ""),
        "valid_observation_count": row.get("valid_observation_count", ""),
        "mean_relative_underperformance": row.get("mean_relative_underperformance", ""),
        "start_lat": start_lat,
        "start_lon": start_lon,
        "map_file": row.get("map_file", map_file(site_id)),
        "selection_reason": reason,
        "comparison_instruction": comparison_instruction(priority_class, site_id),
        "field_observations_to_make": field_observations_to_make(),
        "overclaim_guardrail": overclaim_guardrail(),
    }
    return {column: output.get(column, "") for column in VALIDATION_COLUMNS}


def build_validation_plan(
    summary_rows: list[dict[str, str]],
    scouting_by_site: dict[str, list[dict[str, str]]],
    references_by_site: dict[str, dict[str, list[dict[str, str]]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for site_id in ordered_sites(summary_rows, scouting_by_site):
        site_rows = sort_zone_rows(scouting_by_site.get(site_id, []))
        scout_rows = [row for row in site_rows if row.get("priority_class") == "Scout first"]
        monitor_rows = [row for row in site_rows if row.get("priority_class") == "Monitor"]
        selected: list[tuple[dict[str, str], str, str]] = []
        if scout_rows:
            selected.extend((row, "Scout first field feedback", "top Scout first zone by deterministic priority ranking") for row in scout_rows[:3])
            selected.extend((row, "Monitor contrast sample", "top Monitor zone by deterministic priority ranking") for row in monitor_rows[:2])
        else:
            selected.extend((row, "Monitor low-priority check", "no Scout first zones; top Monitor zone if available") for row in monitor_rows[:1])

        strong = references_by_site.get(site_id, {}).get("Strong reference", [])
        stable = references_by_site.get(site_id, {}).get("Stable", [])
        if strong:
            selected.append((strong[0], "Strong reference agreement sample", "largest available Strong reference zone from GeoJSON"))
        else:
            selected.append(
                (
                    {
                        "site_id": site_id,
                        "zone_id": "",
                        "priority_class": "Strong reference",
                        "map_file": map_file(site_id),
                    },
                    "Strong reference agreement sample",
                    "use map to select nearby green/stable comparison area",
                )
            )
        if stable:
            selected.append((stable[0], "Stable missed-signal check", "largest available Stable zone from GeoJSON"))
        else:
            selected.append(
                (
                    {
                        "site_id": site_id,
                        "zone_id": "",
                        "priority_class": "Stable",
                        "map_file": map_file(site_id),
                    },
                    "Stable missed-signal check",
                    "use map to select nearby green/stable comparison area",
                )
            )

        for sample_rank, (row, sample_type, reason) in enumerate(selected, start=1):
            rows.append(validation_row(row, sample_rank, sample_type, reason))
    return rows


def summary_by_site(summary_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("site", ""): row for row in summary_rows}


def first_reference_text(references_by_site: dict[str, dict[str, list[dict[str, str]]]], site_id: str) -> str:
    strong = references_by_site.get(site_id, {}).get("Strong reference", [])
    stable = references_by_site.get(site_id, {}).get("Stable", [])
    if strong:
        row = strong[0]
        return f"Strong reference starting coordinate: {row.get('centroid_lat')}, {row.get('centroid_lon')}."
    if stable:
        row = stable[0]
        return f"Stable canopy starting coordinate: {row.get('centroid_lat')}, {row.get('centroid_lon')}."
    return "If no reference centroid is available, use the map to select a nearby green or stable comparison area."


def table_row_markdown(row: dict[str, str]) -> str:
    coord = f"{row.get('centroid_lat', '')}, {row.get('centroid_lon', '')}".strip(", ")
    return (
        f"| {row.get('work_order_rank', '')} | `{row.get('zone_id', '')}` | {row.get('priority_class', '')} | "
        f"{safe_float(row.get('approx_area_acres')):.2f} | {safe_float(row.get('persistence_score')):.2f} | "
        f"{coord} | {row.get('estimated_visit_minutes', '')} |"
    )


def site_summary_text(site_id: str, summary: dict[str, str]) -> str:
    return (
        f"Eligible canopy: {safe_float(summary.get('eligible_canopy_acres_est') or summary.get('total_acres_est')):.2f} acres; "
        f"images used: {summary.get('images_used', '')}; "
        f"Scout first: {safe_float(summary.get('investigate_acres_est')):.2f} acres "
        f"({safe_float(summary.get('investigate_pct')):.2f}%); "
        f"Monitor: {safe_float(summary.get('monitor_acres_est')):.2f} acres; "
        f"Stable: {safe_float(summary.get('stable_acres_est')):.2f} acres; "
        f"Strong reference: {safe_float(summary.get('strong_acres_est')):.2f} acres. "
        f"{site_context_sentence(site_id)}"
    )


def build_markdown(
    summary_rows: list[dict[str, str]],
    work_order_rows: list[dict[str, str]],
    references_by_site: dict[str, dict[str, list[dict[str, str]]]],
) -> str:
    summary_lookup = summary_by_site(summary_rows)
    rows_by_site: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in work_order_rows:
        rows_by_site[row["site_id"]].append(row)

    lines: list[str] = [
        "# Grower Work Orders",
        "",
        "This is a scouting-priority field worklist, not a diagnosis tool. It turns the submitted maps and scouting-priority zones into starting coordinates, comparison prompts, records checks, and a simple field-feedback loop.",
        "",
        "Use these coordinates as field navigation prompts, not routes. The repo does not include rows, gates, roads, irrigation sets, or access lanes.",
        "",
        "Planning estimate formula: estimated_visit_minutes = 12 base minutes + 4 minutes per acre, bounded from 12 to 45 minutes for a first-pass scouting stop. These are planning estimates, not true labor costs.",
        "",
        "## Decision Rules",
        "",
        "- Send scout: Scout first zone, especially high persistence and multi-index agreement.",
        "- Compare: always compare Scout first and Monitor zones to nearby Strong reference areas or stable canopy.",
        "- Inspect: note visible canopy difference, irrigation distribution signs, pest or disease symptoms, and soil or water movement signs.",
        "- Call PCA/crop advisor/irrigation tech: only if field symptoms or records support follow-up.",
        "- Monitor/no action: use when a Monitor zone has no visible difference, known benign context, or insufficient access/time.",
        "",
        "## Operational Feedback Metrics",
        "",
        "- confirmed_useful_rate = visited Scout first/Monitor zones labeled confirmed_useful or known_context divided by visited Scout first/Monitor zones.",
        "- false_alert_rate = visited Scout first/Monitor zones labeled no_action divided by visited Scout first/Monitor zones.",
        "- reference_agreement_rate = visited Strong reference zones that looked normal/strong relative to Scout first zones divided by visited Strong reference zones.",
        "- missed_signal_check = Stable/Strong reference samples where a visible concern was found; use these to review thresholds or canopy mask behavior next season.",
        "",
        "This is a low-burden operational feedback loop, not a full statistical accuracy assessment.",
        "",
        "## Site Work Orders",
        "",
    ]

    for site_id in ordered_sites(summary_rows, {site: rows for site, rows in rows_by_site.items()}):
        site_rows = rows_by_site.get(site_id, [])
        summary = summary_lookup.get(site_id, {})
        lines.extend(
            [
                f"### {site_id} - {site_display_name(site_id)}",
                "",
                site_summary_text(site_id, summary),
                "",
                f"Map file to open: `submission/figures/{site_id}_report_zone_map.png`.",
                "",
            ]
        )
        if site_id == "kern_site_1":
            lines.extend(
                [
                    "No Scout first zones were found for Kern Site 1. Treat this as a conservative low-priority check, not a failed result.",
                    "",
                ]
            )

        if site_rows:
            lines.extend(
                [
                    "Top zones to walk first:",
                    "",
                    "| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |",
                    "|---:|---|---|---:|---:|---|---:|",
                ]
            )
            lines.extend(table_row_markdown(row) for row in site_rows)
            lines.append("")
        else:
            lines.extend(["No actionable zone rows were available for this site.", ""])

        lines.extend(
            [
                f"What to compare against: {first_reference_text(references_by_site, site_id)} Compare the zone against Strong reference or stable canopy before deciding follow-up.",
                "",
                f"Records to check: {records_to_check(site_id)}.",
                "",
                f"Field observations to make: {field_observations_to_make()}.",
                "",
                f"What to write down after scouting: {what_to_write_down()}.",
                "",
                "This work order does not assign cause from satellite imagery.",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def build_outputs(tables_dir: Path, geodata_dir: Path, report_dir: Path) -> None:
    scouting_path = tables_dir / "scouting_priority_table.csv"
    summary_path = tables_dir / "spatial_zone_summary.csv"
    if not scouting_path.exists():
        raise FileNotFoundError(f"Missing scouting table: {scouting_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing spatial summary table: {summary_path}")

    scouting_rows = [scouting_candidate(row) for row in read_csv(scouting_path)]
    summary_rows = read_csv(summary_path)
    scouting_by_site: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in scouting_rows:
        scouting_by_site[row["site_id"]].append(row)

    references_by_site = load_reference_zones(geodata_dir)
    work_orders = build_work_orders(summary_rows, scouting_by_site, references_by_site)
    validation_plan = build_validation_plan(summary_rows, scouting_by_site, references_by_site)

    write_csv(tables_dir / "grower_work_orders.csv", WORK_ORDER_COLUMNS, work_orders)
    write_csv(tables_dir / "field_verification_form_template.csv", FIELD_FORM_COLUMNS, [])
    write_csv(tables_dir / "validation_sampling_plan.csv", VALIDATION_COLUMNS, validation_plan)

    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "grower_work_orders.md").write_text(
        build_markdown(summary_rows, work_orders, references_by_site),
        encoding="utf-8",
    )

    print("Built grower work-order artifacts with deterministic ordering.")
    print("No random sampling used.")
    print(f"- {tables_dir / 'grower_work_orders.csv'}")
    print(f"- {tables_dir / 'field_verification_form_template.csv'}")
    print(f"- {tables_dir / 'validation_sampling_plan.csv'}")
    print(f"- {report_dir / 'grower_work_orders.md'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES_DIR)
    parser.add_argument("--geodata-dir", type=Path, default=DEFAULT_GEODATA_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_outputs(args.tables_dir, args.geodata_dir, args.report_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
