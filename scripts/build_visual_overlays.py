"""Build readable canopy-vs-priority overlays from existing spatial rasters.

This is a fast visual refresh helper. It does not query Sentinel-2 or change
scoring; it only rebuilds the large single-panel figures used in the report
and Obsidian notes.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import rasterio

from build_spatial_zones import (
    ALL_SITE_IDS,
    INDICES,
    SiteResult,
    load_site,
    plot_combined_zone_map,
    plot_canopy_priority_overlay,
    plot_report_zone_map,
)


def read_raster(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        return src.read(1), src.profile.copy()


def read_summary_rows(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as f:
        return {row.get("site", ""): row for row in csv.DictReader(f)}


def build_overlay(site: str, geojson_dir: Path, spatial_dir: Path, figures_dir: Path) -> SiteResult:
    site_path = geojson_dir / f"{site}.geojson"
    canopy_path = spatial_dir / f"{site}_canopy_mask.tif"
    zones_path = spatial_dir / f"{site}_zones.tif"
    mean_ndvi_path = spatial_dir / f"{site}_mean_ndvi.tif"
    if not site_path.exists():
        raise FileNotFoundError(f"Missing boundary: {site_path}")
    if not canopy_path.exists():
        raise FileNotFoundError(f"Missing canopy mask: {canopy_path}")
    if not zones_path.exists():
        raise FileNotFoundError(f"Missing zones raster: {zones_path}")
    if not mean_ndvi_path.exists():
        raise FileNotFoundError(f"Missing mean NDVI raster: {mean_ndvi_path}")

    _, gdf = load_site(site_path)
    canopy_raw, profile = read_raster(canopy_path)
    zones, _ = read_raster(zones_path)
    mean_ndvi, _ = read_raster(mean_ndvi_path)
    canopy = canopy_raw > 0
    underperformance = np.isin(zones, [1, 2])
    if bool((underperformance & ~canopy).any()):
        raise AssertionError(f"{site}: priority pixels occur outside canopy mask")

    placeholder = np.full(zones.shape, np.nan, dtype="float32")
    summary_rows = read_summary_rows(spatial_dir / "spatial_zone_summary.csv")
    result = SiteResult(
        site=site,
        years=[],
        yearly={},
        profile=profile,
        canopy_mask=canopy,
        valid_observation_count=np.zeros(zones.shape, dtype="uint16"),
        zones=zones.astype("uint8"),
        score=placeholder,
        persistence=placeholder,
        confidence=placeholder,
        mean_ndvi=mean_ndvi.astype("float32"),
        underperformance_mask=underperformance,
        index_trigger_frequency={idx: placeholder for idx in INDICES},
        summary=summary_rows.get(site, {}),
        timeseries_rows=[],
    )
    plot_canopy_priority_overlay(result, gdf, figures_dir / f"{site}_canopy_priority_overlay.png")
    plot_report_zone_map(result, gdf, figures_dir / f"{site}_report_zone_map.png")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build readable canopy priority overlay figures.")
    parser.add_argument("--sites", nargs="+", default=list(ALL_SITE_IDS), help="Site IDs to process, or 'all'.")
    parser.add_argument("--geojson-dir", default="data/geojsons")
    parser.add_argument("--spatial-dir", default="output/spatial")
    parser.add_argument("--figures-dir", default="output/figures")
    return parser.parse_args()


def normalize_sites(raw_sites: list[str]) -> list[str]:
    if any(site.lower() == "all" for site in raw_sites):
        return list(ALL_SITE_IDS)
    return raw_sites


def main() -> None:
    args = parse_args()
    results = []
    for site in normalize_sites(args.sites):
        result = build_overlay(site, Path(args.geojson_dir), Path(args.spatial_dir), Path(args.figures_dir))
        results.append(result)
        print(f"wrote {site}_canopy_priority_overlay.png and {site}_report_zone_map.png")
    plot_combined_zone_map(results, Path(args.figures_dir))
    print("wrote spatial_zone_maps.png")


if __name__ == "__main__":
    main()
