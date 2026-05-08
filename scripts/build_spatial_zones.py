"""
Build grower-facing persistent underperformance zones from Sentinel-2 L2A.

This script intentionally avoids Earth Engine auth. It uses the public
Microsoft Planetary Computer STAC API, signs Sentinel-2 asset URLs, clips
COGs to each site boundary, and computes field-normalized scouting-priority zones.

Outputs:
  output/spatial/*.tif              GeoTIFF scores and zone classes
  output/spatial/*_summary.csv      Per-site zone statistics
  output/spatial/*_zone_timeseries.csv
  output/figures/*_stress_zones.png
  output/figures/*_report_zone_map.png
  output/figures/*_canopy_priority_overlay.png
  output/figures/*_zone_timeseries.png
  output/figures/spatial_zone_maps.png
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import requests
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, shapes
from rasterio.mask import mask
from rasterio.transform import array_bounds
from rasterio.warp import reproject
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform


PC_STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
EARTH_SEARCH_STAC = "https://earth-search.aws.element84.com/v1/search"

ALL_SITE_IDS = (
    "fresno_site_1",
    "kern_site_1",
    "kings_site_1",
    "partner_site_1",
    "stanislaus_site_1",
    "tulare_site_1",
)
PARTNER_SITE_ID = "partner_site_1"
UNDERPERFORMANCE_ZONE_VALUES = {1, 2}
INDICES = ("NDVI", "NDMI", "NDRE", "EVI2")
ASSET_ALIASES = {
    "B08": ("B08", "nir"),
    "B04": ("B04", "red"),
    "B05": ("B05", "rededge1"),
    "B11": ("B11", "swir16"),
    "SCL": ("SCL", "scl"),
}
CLOUD_SCL_CLASSES = {0, 1, 3, 6, 7, 8, 9, 10, 11}
CANOPY_MASK_CONFIG = {
    "min_valid_obs": 4,
    "ndvi_p75_min": 0.35,
    "ndvi_median_min": 0.20,
    "evi2_p75_min": 0.22,
    "min_component_pixels": 3,
}
ZONE_LABELS = {1: "Scout first", 2: "Monitor", 3: "Stable context", 4: "Strong reference"}
ZONE_COLORS = {
    1: "#A33A35",
    2: "#D89A2B",
    3: "#AAB7A0",
    4: "#2E6F5E",
}
EXCLUDED_COLOR = "#F4F6F0"
BOUNDARY_COLOR = "#17211F"
PAPER_COLOR = "#FAF9F4"
GRID_COLOR = "#D8DDD4"
OVERVIEW_SITE_ORDER = (
    "partner_site_1",
    "fresno_site_1",
    "kern_site_1",
    "kings_site_1",
    "stanislaus_site_1",
    "tulare_site_1",
)
ZONE_RECOMMENDATIONS = {
    1: "Scout this zone in the field; compare canopy condition, irrigation distribution, pest signs, soil variability, and management records.",
    2: "Scout after first-priority zones or monitor during field rounds; compare canopy condition and management records before assigning a cause.",
    3: "Use as baseline context; no immediate scouting priority from the satellite signal alone.",
    4: "Use as a strong within-site reference zone for comparison during field follow-up.",
}


def scouting_zone_cmap(include_stable: bool = True) -> ListedColormap:
    colors = [(0, 0, 0, 0), ZONE_COLORS[1], ZONE_COLORS[2]]
    if include_stable:
        colors.extend([ZONE_COLORS[3], ZONE_COLORS[4]])
    return ListedColormap(colors)


def zone_legend_handles(include_canopy: bool = False, include_stable: bool = True) -> list[Patch]:
    handles: list[Patch] = []
    if include_canopy:
        handles.append(Patch(facecolor="#C7DBC6", edgecolor="none", label="Eligible canopy"))
    handles.extend(
        [
            Patch(facecolor=ZONE_COLORS[1], edgecolor="none", label="Scout first"),
            Patch(facecolor=ZONE_COLORS[2], edgecolor="none", label="Monitor"),
        ]
    )
    if include_stable:
        handles.extend(
            [
                Patch(facecolor=ZONE_COLORS[3], edgecolor="none", label="Stable context"),
                Patch(facecolor=ZONE_COLORS[4], edgecolor="none", label="Strong reference"),
            ]
        )
    handles.extend(
        [
            Patch(facecolor=EXCLUDED_COLOR, edgecolor="#9CA3AF", label="Non-canopy / excluded"),
            Patch(facecolor="none", edgecolor=BOUNDARY_COLOR, label="Site boundary"),
        ]
    )
    return handles


def draw_figure_legend(fig, handles: list[Patch], y: float = 0.095, ncol: int = 4) -> None:
    legend_ax = fig.add_axes([0.08, y - 0.024, 0.84, 0.052])
    legend_ax.axis("off")
    legend_ax.legend(
        handles=handles,
        loc="center",
        ncol=ncol,
        frameon=False,
        fontsize=8.0,
        handlelength=1.65,
        columnspacing=1.15,
    )


def legend_y_below_axis(fig, ax, min_y: float = 0.105, gap: float = 0.080) -> float:
    fig.canvas.draw()
    axis_bottom = ax.get_position().y0
    return max(min_y, axis_bottom - gap)


def style_map_axes(ax, xbins: int = 5, ybins: int = 4) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(nbins=xbins, min_n_ticks=3))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=ybins, min_n_ticks=3))
    ax.tick_params(axis="both", labelsize=8.5)


def padded_display_bounds(
    bounds: tuple[float, float, float, float],
    profile: dict[str, Any],
    pad_fraction: float,
    min_span_pixels: int = 0,
    force_square: bool = False,
) -> tuple[float, float, float, float]:
    west, east, south, north = bounds
    pixel = max(abs(profile["transform"].a), abs(profile["transform"].e))
    min_span = pixel * min_span_pixels
    width = max(east - west, min_span)
    height = max(north - south, min_span)
    cx = (west + east) / 2
    cy = (south + north) / 2
    if force_square:
        span = max(width, height, min_span)
        pad = max(span * pad_fraction, pixel * 3)
        half = span / 2 + pad
        return cx - half, cx + half, cy - half, cy + half

    span = max(width, height)
    pad = max(span * pad_fraction, pixel * 3)
    return cx - width / 2 - pad, cx + width / 2 + pad, cy - height / 2 - pad, cy + height / 2 + pad


def map_display_bounds(result: SiteResult, pad_fraction: float = 0.025) -> tuple[tuple[float, float, float, float], bool]:
    if result.site == "kern_site_1":
        kern_focus = np.isin(result.zones, [2, 4])
        kern_bounds = mask_bounds(kern_focus, result.profile)
        if kern_bounds is not None:
            return padded_display_bounds(kern_bounds, result.profile, pad_fraction=0.12, min_span_pixels=20, force_square=False), True
        zone_bounds = mask_bounds(result.zones > 0, result.profile)
        if zone_bounds is not None:
            return padded_display_bounds(zone_bounds, result.profile, pad_fraction=0.12, min_span_pixels=20, force_square=False), True

    bounds = mask_bounds(result.canopy_mask, result.profile)
    if bounds is None:
        bounds = raster_extent(result.profile)
    return padded_display_bounds(bounds, result.profile, pad_fraction=pad_fraction, min_span_pixels=0, force_square=False), False


def apply_display_bounds(ax, bounds: tuple[float, float, float, float]) -> None:
    west, east, south, north = bounds
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)


def map_figure_canvas(display_bounds: tuple[float, float, float, float], title: str, note: str) -> tuple[plt.Figure, Any]:
    west, east, south, north = display_bounds
    map_aspect = max((east - west) / max(north - south, 1e-9), 0.15)
    fig_w = 12.5
    map_w_frac = 0.84
    map_w_in = fig_w * map_w_frac
    map_h_in = min(6.1, max(2.15, map_w_in / map_aspect))
    top_in = 1.12
    bottom_in = 1.28
    fig_h = min(8.5, max(4.55, top_in + map_h_in + bottom_in))
    map_h_frac = map_h_in / fig_h
    map_bottom = bottom_in / fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=PAPER_COLOR)
    fig.text(0.075, 1 - 0.34 / fig_h, title, fontsize=15, weight="bold", color=BOUNDARY_COLOR)
    fig.text(
        0.075,
        1 - 0.77 / fig_h,
        note,
        ha="left",
        va="top",
        fontsize=9,
        color="#33423E",
        bbox={"boxstyle": "square,pad=0.35", "facecolor": "white", "edgecolor": GRID_COLOR, "alpha": 0.96},
    )
    ax = fig.add_axes([0.090, map_bottom, map_w_frac, map_h_frac])
    ax.set_facecolor(EXCLUDED_COLOR)
    return fig, ax


def site_display_name(site: str) -> str:
    if site == "kern_site_1":
        return "Kern 1"
    return site.replace("_", " ").title()


@dataclass
class ImageResult:
    item_id: str
    date: str
    cloud_cover: float
    arrays: dict[str, np.ndarray]
    profile: dict[str, Any]


@dataclass
class SiteResult:
    site: str
    years: list[int]
    yearly: dict[int, dict[str, np.ndarray]]
    profile: dict[str, Any]
    canopy_mask: np.ndarray
    valid_observation_count: np.ndarray
    zones: np.ndarray
    score: np.ndarray
    persistence: np.ndarray
    confidence: np.ndarray
    mean_ndvi: np.ndarray
    underperformance_mask: np.ndarray
    index_trigger_frequency: dict[str, np.ndarray]
    summary: dict[str, Any]
    timeseries_rows: list[dict[str, Any]]


class PcClient:
    def __init__(self, timeout: int = 90, retries: int = 4) -> None:
        self.session = requests.Session()
        self.timeout = timeout
        self.retries = retries
        self.signed_cache: dict[str, str] = {}

    def post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.post(url, json=body, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001 - retry network/API failures
                last_err = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"POST failed after {self.retries} attempts: {url}") from last_err

    def get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"GET failed after {self.retries} attempts: {url}") from last_err

    def sign(self, href: str) -> str:
        cached = self.signed_cache.get(href)
        if cached:
            return cached
        if "blob.core.windows.net" not in href:
            self.signed_cache[href] = href
            return href
        try:
            signed = self.get_json(PC_SIGN, {"href": href})["href"]
        except RuntimeError:
            # Some public COG URLs can still be read without a SAS token. If
            # signing is temporarily unavailable, try the original asset URL
            # and let rasterio decide whether it is readable.
            signed = href
        self.signed_cache[href] = signed
        return signed


def force_2d(geom):
    """Drop optional KML/GeoJSON Z values before raster masking."""

    def _drop_z(x, y, z=None):
        return (x, y)

    return shapely_transform(_drop_z, geom)


def load_site(site_path: Path) -> tuple[str, gpd.GeoDataFrame]:
    gdf = gpd.read_file(site_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    gdf["geometry"] = gdf.geometry.map(force_2d)
    site = site_path.stem
    if "site_name" in gdf.columns and gdf["site_name"].notna().any():
        site = str(gdf["site_name"].dropna().iloc[0])
    return site, gdf


def asset_href(assets: dict[str, Any], logical_name: str) -> str:
    for alias in ASSET_ALIASES[logical_name]:
        asset = assets.get(alias)
        if asset and asset.get("href"):
            return str(asset["href"])
    raise KeyError(f"missing required asset {logical_name}")


def has_required_assets(item: dict[str, Any]) -> bool:
    assets = item.get("assets", {})
    return all(any(alias in assets for alias in aliases) for aliases in ASSET_ALIASES.values())


def stac_endpoints(source: str) -> list[tuple[str, str]]:
    if source == "planetary-computer":
        return [("planetary-computer", PC_STAC_SEARCH)]
    if source == "earth-search":
        return [("earth-search", EARTH_SEARCH_STAC)]
    return [("earth-search", EARTH_SEARCH_STAC), ("planetary-computer", PC_STAC_SEARCH)]


def search_items(
    client: PcClient,
    bbox: tuple[float, float, float, float],
    year: int,
    season: tuple[str, str],
    cloud_lt: float,
    stac_source: str,
    limit: int = 80,
) -> list[dict[str, Any]]:
    start, end = season
    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{year}-{start}T00:00:00Z/{year}-{end}T23:59:59Z",
        "limit": limit,
        "query": {"eo:cloud_cover": {"lt": cloud_lt}},
    }
    items: list[dict[str, Any]] = []
    for source_name, endpoint in stac_endpoints(stac_source):
        try:
            data = client.post_json(endpoint, body)
            items = data.get("features", [])
        except RuntimeError:
            items = []
            for window_start, window_end in season_windows(season):
                month_body = body.copy()
                month_body["datetime"] = f"{year}-{window_start}T00:00:00Z/{year}-{window_end}T23:59:59Z"
                month_body["limit"] = min(limit, 40)
                try:
                    month_data = client.post_json(endpoint, month_body)
                except RuntimeError:
                    continue
                items.extend(month_data.get("features", []))
        if items:
            for item in items:
                item["_stac_source"] = source_name
            break
    if not items:
        return []

    items = [item for item in items if has_required_assets(item)]
    return sorted(
        items,
        key=lambda item: (
            float(item.get("properties", {}).get("eo:cloud_cover", 999.0)),
            item.get("properties", {}).get("datetime", ""),
        ),
    )


def choose_tile(items_by_year: dict[int, list[dict[str, Any]]]) -> str | None:
    counts: dict[str, int] = {}
    for items in items_by_year.values():
        for item in items:
            tile = (
                item.get("properties", {}).get("s2:mgrs_tile")
                or item.get("properties", {}).get("sentinel:utm_zone")
                or ""
            )
            if tile:
                counts[tile] = counts.get(tile, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def item_tile(item: dict[str, Any]) -> str:
    props = item.get("properties", {})
    grid_code = str(props.get("grid:code", "")).replace("MGRS-", "")
    mgrs_parts = (
        str(props.get("mgrs:utm_zone", "")),
        str(props.get("mgrs:latitude_band", "")),
        str(props.get("mgrs:grid_square", "")),
    )
    mgrs_tile = "".join(mgrs_parts) if all(mgrs_parts) else ""
    return str(
        item.get("properties", {}).get("s2:mgrs_tile")
        or grid_code
        or mgrs_tile
        or props.get("sentinel:utm_zone")
        or ""
    )


def season_windows(season: tuple[str, str]) -> list[tuple[str, str]]:
    start, end = season
    start_month, start_day = (int(part) for part in start.split("-"))
    end_month, end_day = (int(part) for part in end.split("-"))
    if start_month > end_month:
        return [season]
    windows: list[tuple[str, str]] = []
    for month in range(start_month, end_month + 1):
        first_day = start_day if month == start_month else 1
        last_day = end_day if month == end_month else calendar.monthrange(2001, month)[1]
        windows.append((f"{month:02d}-{first_day:02d}", f"{month:02d}-{last_day:02d}"))
    return windows


def dedupe_by_date(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        date = item.get("properties", {}).get("datetime", "")[:10]
        cloud = float(item.get("properties", {}).get("eo:cloud_cover", 999.0))
        if date not in best:
            best[date] = item
            continue
        old_cloud = float(best[date].get("properties", {}).get("eo:cloud_cover", 999.0))
        if cloud < old_cloud:
            best[date] = item
    return sorted(
        best.values(),
        key=lambda item: float(item.get("properties", {}).get("eo:cloud_cover", 999.0)),
    )


def item_month(item: dict[str, Any]) -> int:
    date = item.get("properties", {}).get("datetime", "")
    try:
        return int(date[5:7])
    except ValueError:
        return 0


def select_month_balanced_items(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Pick clear scenes across the season instead of clustering on one low-cloud date."""
    candidates = dedupe_by_date(items)
    if count <= 0 or len(candidates) <= count:
        return candidates

    # June/July/August are the default season. For other seasons, this still
    # spreads picks across early, middle, and late months.
    months = sorted({item_month(item) for item in candidates if item_month(item)})
    if not months:
        return candidates[:count]
    if len(months) >= count:
        positions = np.linspace(0, len(months) - 1, count).round().astype(int)
        target_months = [months[int(pos)] for pos in positions]
    else:
        target_months = months

    picks: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for month in target_months:
        month_items = [item for item in candidates if item_month(item) == month and item.get("id", "") not in used_ids]
        if not month_items:
            continue
        pick = min(month_items, key=lambda item: float(item.get("properties", {}).get("eo:cloud_cover", 999.0)))
        picks.append(pick)
        used_ids.add(pick.get("id", ""))

    for item in candidates:
        if len(picks) >= count:
            break
        item_id = item.get("id", "")
        if item_id not in used_ids:
            picks.append(item)
            used_ids.add(item_id)

    return sorted(picks, key=lambda item: item.get("properties", {}).get("datetime", ""))


def project_geometry(gdf_wgs84: gpd.GeoDataFrame, dst_crs) -> list[dict[str, Any]]:
    projected = gdf_wgs84.to_crs(dst_crs)
    geom = projected.geometry.union_all()
    return [mapping(geom)]


def read_asset_masked(
    client: PcClient,
    href: str,
    gdf_wgs84: gpd.GeoDataFrame,
) -> tuple[np.ndarray, dict[str, Any]]:
    signed = client.sign(href)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(signed) as src:
            geoms = project_geometry(gdf_wgs84, src.crs)
            arr, transform = mask(src, geoms, crop=True, filled=False)
            data = arr[0].astype("float32")
            if hasattr(data, "filled"):
                data = data.filled(np.nan).astype("float32")
            profile = src.profile.copy()
            profile.update(
                height=data.shape[0],
                width=data.shape[1],
                transform=transform,
                count=1,
                dtype="float32",
                nodata=np.nan,
            )
            return data, profile


def read_asset_to_ref(
    client: PcClient,
    href: str,
    gdf_wgs84: gpd.GeoDataFrame,
    ref_profile: dict[str, Any],
    resampling: Resampling,
) -> np.ndarray:
    data, src_profile = read_asset_masked(client, href, gdf_wgs84)
    if (
        data.shape == (ref_profile["height"], ref_profile["width"])
        and src_profile["transform"] == ref_profile["transform"]
        and src_profile["crs"] == ref_profile["crs"]
    ):
        return data

    dst = np.full((ref_profile["height"], ref_profile["width"]), np.nan, dtype="float32")
    reproject(
        data,
        dst,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        src_nodata=np.nan,
        dst_transform=ref_profile["transform"],
        dst_crs=ref_profile["crs"],
        dst_nodata=np.nan,
        resampling=resampling,
    )
    return dst


def safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    out = np.full(numerator.shape, np.nan, dtype="float32")
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (np.abs(denominator) > 1e-6)
    out[valid] = numerator[valid] / denominator[valid]
    return np.clip(out, -1.5, 1.5)


def to_reflectance(arr: np.ndarray) -> np.ndarray:
    valid = np.isfinite(arr) & (arr > 0)
    if valid.any() and float(np.nanmedian(arr[valid])) > 2.0:
        return arr / 10000.0
    return arr


def compute_item_indices(client: PcClient, item: dict[str, Any], gdf_wgs84: gpd.GeoDataFrame) -> ImageResult:
    assets = item["assets"]
    b08, ref = read_asset_masked(client, asset_href(assets, "B08"), gdf_wgs84)
    b04 = read_asset_to_ref(client, asset_href(assets, "B04"), gdf_wgs84, ref, Resampling.bilinear)
    b05 = read_asset_to_ref(client, asset_href(assets, "B05"), gdf_wgs84, ref, Resampling.bilinear)
    b11 = read_asset_to_ref(client, asset_href(assets, "B11"), gdf_wgs84, ref, Resampling.bilinear)
    scl = read_asset_to_ref(client, asset_href(assets, "SCL"), gdf_wgs84, ref, Resampling.nearest)

    scl_valid = np.isfinite(scl)
    scl_classes = np.full(scl.shape, -1, dtype="int16")
    scl_classes[scl_valid] = np.rint(scl[scl_valid]).astype("int16")
    cloud_mask = ~scl_valid | np.isin(scl_classes, list(CLOUD_SCL_CLASSES))
    reflectance_mask = (b08 <= 0) | (b04 <= 0) | (b05 <= 0) | (b11 <= 0)
    valid = np.isfinite(b08) & np.isfinite(b04) & np.isfinite(b05) & np.isfinite(b11)
    valid &= ~cloud_mask & ~reflectance_mask

    # NDVI/NDMI/NDRE are scale-invariant ratios. EVI2 includes an additive
    # constant, so convert Sentinel-2 digital reflectance values to 0-1 first.
    b08_ref = to_reflectance(b08)
    b04_ref = to_reflectance(b04)

    arrays = {
        "NDVI": safe_ratio(b08 - b04, b08 + b04),
        "NDMI": safe_ratio(b08 - b11, b08 + b11),
        "NDRE": safe_ratio(b08 - b05, b08 + b05),
        "EVI2": safe_ratio(2.5 * (b08_ref - b04_ref), b08_ref + 2.4 * b04_ref + 1.0),
    }
    for key in arrays:
        arrays[key] = np.where(valid, arrays[key], np.nan).astype("float32")

    props = item.get("properties", {})
    return ImageResult(
        item_id=item.get("id", ""),
        date=str(props.get("datetime", ""))[:10],
        cloud_cover=float(props.get("eo:cloud_cover", math.nan)),
        arrays=arrays,
        profile=ref,
    )


def align_array(
    arr: np.ndarray,
    src_profile: dict[str, Any],
    dst_profile: dict[str, Any],
    resampling: Resampling = Resampling.bilinear,
) -> np.ndarray:
    if (
        arr.shape == (dst_profile["height"], dst_profile["width"])
        and src_profile["transform"] == dst_profile["transform"]
        and src_profile["crs"] == dst_profile["crs"]
    ):
        return arr
    dst = np.full((dst_profile["height"], dst_profile["width"]), np.nan, dtype="float32")
    reproject(
        arr,
        dst,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        src_nodata=np.nan,
        dst_transform=dst_profile["transform"],
        dst_crs=dst_profile["crs"],
        dst_nodata=np.nan,
        resampling=resampling,
    )
    return dst


def robust_z(arr: np.ndarray) -> np.ndarray:
    valid = np.isfinite(arr)
    out = np.full(arr.shape, np.nan, dtype="float32")
    if valid.sum() < 20:
        return out
    median = float(np.nanmedian(arr))
    mad = float(np.nanmedian(np.abs(arr[valid] - median)))
    scale = 1.4826 * mad
    if scale < 1e-5:
        scale = float(np.nanstd(arr[valid]))
    if scale < 1e-5:
        return out
    out[valid] = (arr[valid] - median) / scale
    return np.clip(out, -5, 5)


def valid_geometry_mask(gdf_wgs84: gpd.GeoDataFrame, profile: dict[str, Any]) -> np.ndarray:
    geom = gdf_wgs84.to_crs(profile["crs"]).geometry.union_all()
    return geometry_mask(
        [mapping(geom)],
        out_shape=(profile["height"], profile["width"]),
        transform=profile["transform"],
        invert=True,
        all_touched=False,
    )


def filter_small_boolean_components(mask_arr: np.ndarray, min_pixels: int) -> np.ndarray:
    """Remove tiny isolated eligible-canopy speckles without filling gaps."""
    if min_pixels <= 1:
        return mask_arr
    filtered = mask_arr.copy()
    height, width = filtered.shape
    visited = np.zeros(filtered.shape, dtype=bool)
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    rows, cols = np.where(filtered)
    for start_r, start_c in zip(rows, cols):
        if visited[start_r, start_c] or not filtered[start_r, start_c]:
            continue
        stack = [(int(start_r), int(start_c))]
        visited[start_r, start_c] = True
        component: list[tuple[int, int]] = []
        while stack:
            r, c = stack.pop()
            component.append((r, c))
            for dr, dc in neighbors:
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= height or nc < 0 or nc >= width:
                    continue
                if visited[nr, nc] or not filtered[nr, nc]:
                    continue
                visited[nr, nc] = True
                stack.append((nr, nc))
        if len(component) < min_pixels:
            rr, cc = zip(*component)
            filtered[rr, cc] = False
    return filtered


def build_canopy_mask(
    images_used: list[ImageResult],
    profile: dict[str, Any],
    gdf_wgs84: gpd.GeoDataFrame,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Build a conservative persistent-vegetation mask from clear multi-date observations."""
    in_site = valid_geometry_mask(gdf_wgs84, profile)
    if not images_used:
        empty = np.zeros((profile["height"], profile["width"]), dtype=bool)
        return empty, empty.astype("uint16"), {}

    ndvi_stack = np.stack([image.arrays["NDVI"] for image in images_used])
    evi2_stack = np.stack([image.arrays["EVI2"] for image in images_used])
    valid_observation_count = np.isfinite(ndvi_stack).sum(axis=0).astype("uint16")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        ndvi_median = np.nanmedian(ndvi_stack, axis=0).astype("float32")
        ndvi_p75 = np.nanpercentile(ndvi_stack, 75, axis=0).astype("float32")
        evi2_p75 = np.nanpercentile(evi2_stack, 75, axis=0).astype("float32")

    cfg = CANOPY_MASK_CONFIG
    vegetation_signal = (ndvi_p75 >= cfg["ndvi_p75_min"]) | (evi2_p75 >= cfg["evi2_p75_min"])
    canopy_mask = (
        in_site
        & (valid_observation_count >= int(cfg["min_valid_obs"]))
        & (ndvi_median >= cfg["ndvi_median_min"])
        & vegetation_signal
    )
    canopy_mask = filter_small_boolean_components(canopy_mask, int(cfg["min_component_pixels"]))
    canopy_mask &= in_site

    area = pixel_area_acres(profile)
    diagnostics = {
        "canopy_pixels": int(canopy_mask.sum()),
        "canopy_acres_est": round(float(canopy_mask.sum() * area), 2),
        "min_valid_obs": int(cfg["min_valid_obs"]),
        "ndvi_p75_min": float(cfg["ndvi_p75_min"]),
        "ndvi_median_min": float(cfg["ndvi_median_min"]),
        "evi2_p75_min": float(cfg["evi2_p75_min"]),
        "median_valid_observations": round(float(np.nanmedian(valid_observation_count[canopy_mask])), 2) if canopy_mask.any() else math.nan,
    }
    return canopy_mask, valid_observation_count, diagnostics


def filter_small_zone_patches(zones: np.ndarray, min_pixels: int) -> np.ndarray:
    if min_pixels <= 1:
        return zones
    filtered = zones.copy()
    height, width = zones.shape
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for zone_value in (1, 2, 4):
        visited = np.zeros(zones.shape, dtype=bool)
        rows, cols = np.where((zones == zone_value) & ~visited)
        for start_r, start_c in zip(rows, cols):
            if visited[start_r, start_c] or zones[start_r, start_c] != zone_value:
                continue
            stack = [(int(start_r), int(start_c))]
            visited[start_r, start_c] = True
            component: list[tuple[int, int]] = []
            while stack:
                r, c = stack.pop()
                component.append((r, c))
                for dr, dc in neighbors:
                    nr, nc = r + dr, c + dc
                    if nr < 0 or nr >= height or nc < 0 or nc >= width:
                        continue
                    if visited[nr, nc] or zones[nr, nc] != zone_value:
                        continue
                    visited[nr, nc] = True
                    stack.append((nr, nc))
            if len(component) < min_pixels:
                rr, cc = zip(*component)
                filtered[rr, cc] = 3
    return filtered


def classify_zones(
    yearly: dict[int, dict[str, np.ndarray]],
    profile: dict[str, Any],
    gdf_wgs84: gpd.GeoDataFrame,
    min_zone_pixels: int,
    canopy_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    in_site = valid_geometry_mask(gdf_wgs84, profile)
    eligible = in_site & canopy_mask
    stress_layers = []
    agreement_layers = []
    ndvi_layers = []
    index_trigger_layers: dict[str, list[np.ndarray]] = {idx: [] for idx in INDICES}
    index_valid_layers: dict[str, list[np.ndarray]] = {idx: [] for idx in INDICES}

    for arrays in yearly.values():
        masked_arrays = {idx: np.where(eligible, arrays[idx], np.nan).astype("float32") for idx in INDICES}
        z = {idx: robust_z(masked_arrays[idx]) for idx in INDICES}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            stress = np.nanmean(np.stack([-z[idx] for idx in INDICES]), axis=0)
        agreement_count = np.zeros_like(stress, dtype="int8")
        for idx in INDICES:
            idx_valid = np.isfinite(z[idx])
            agreement_count += ((z[idx] < -0.5) & idx_valid).astype("int8")
            index_trigger_layers[idx].append((z[idx] < -0.5) & idx_valid)
            index_valid_layers[idx].append(idx_valid)
        agreement = agreement_count >= 2
        stress_layers.append(stress.astype("float32"))
        agreement_layers.append(agreement)
        ndvi_layers.append(masked_arrays["NDVI"])

    stress_stack = np.stack(stress_layers)
    agreement_stack = np.stack(agreement_layers)
    valid_stack = np.isfinite(stress_stack)
    valid_years = valid_stack.sum(axis=0)

    positive_deficit = np.where(stress_stack > 0, stress_stack, 0)
    score = np.divide(
        np.nansum(positive_deficit, axis=0),
        valid_years,
        out=np.full(valid_years.shape, np.nan, dtype="float32"),
        where=valid_years > 0,
    )
    persistent_hits = (stress_stack > 0.75) & agreement_stack & valid_stack
    persistence = np.divide(
        persistent_hits.sum(axis=0),
        valid_years,
        out=np.full(valid_years.shape, np.nan, dtype="float32"),
        where=valid_years > 0,
    )
    agreement_fraction = np.divide(
        (agreement_stack & valid_stack).sum(axis=0),
        valid_years,
        out=np.zeros(valid_years.shape, dtype="float32"),
        where=valid_years > 0,
    )
    confidence = (valid_years / max(1, len(yearly))) * (0.5 + 0.5 * agreement_fraction)
    mean_stress = np.divide(
        np.nansum(stress_stack, axis=0),
        valid_years,
        out=np.full(valid_years.shape, np.nan, dtype="float32"),
        where=valid_years > 0,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean_ndvi = np.nanmean(np.stack(ndvi_layers), axis=0).astype("float32")

    zones = np.zeros(score.shape, dtype="uint8")
    valid = eligible & np.isfinite(score) & (valid_years >= max(2, math.ceil(len(yearly) * 0.5)))

    investigate = valid & (score >= 0.75) & (persistence >= 0.50) & (confidence >= 0.50)
    monitor = valid & ~investigate & ((score >= 0.45) | (persistence >= 0.25))
    strong = valid & ~investigate & ~monitor & (mean_stress <= -0.75) & (confidence >= 0.50)
    stable = valid & ~investigate & ~monitor & ~strong

    zones[investigate] = 1
    zones[monitor] = 2
    zones[stable] = 3
    zones[strong] = 4
    zones = filter_small_zone_patches(zones, min_zone_pixels)
    zones[~eligible] = 0

    score = np.where(eligible, score, np.nan).astype("float32")
    persistence = np.where(eligible, persistence, np.nan).astype("float32")
    confidence = np.where(eligible, confidence, np.nan).astype("float32")
    mean_ndvi = np.where(eligible, mean_ndvi, np.nan).astype("float32")

    index_trigger_frequency: dict[str, np.ndarray] = {}
    for idx in INDICES:
        trigger_stack = np.stack(index_trigger_layers[idx])
        valid_idx_stack = np.stack(index_valid_layers[idx])
        valid_idx_years = valid_idx_stack.sum(axis=0)
        freq = np.divide(
            trigger_stack.sum(axis=0),
            valid_idx_years,
            out=np.full(valid_idx_years.shape, np.nan, dtype="float32"),
            where=valid_idx_years > 0,
        )
        index_trigger_frequency[idx] = np.where(eligible, freq, np.nan).astype("float32")

    return zones, score, persistence, confidence, mean_ndvi, index_trigger_frequency


def pixel_area_acres(profile: dict[str, Any]) -> float:
    transform = profile["transform"]
    pixel_area_m2 = abs(transform.a * transform.e)
    return pixel_area_m2 / 4046.8564224


def summarize(site: str, zones: np.ndarray, score: np.ndarray, confidence: np.ndarray, profile: dict[str, Any], images_used: list[ImageResult]) -> dict[str, Any]:
    valid = zones > 0
    area = pixel_area_acres(profile)
    total_acres = float(valid.sum() * area)
    stats: dict[str, Any] = {
        "site": site,
        "valid_pixels": int(valid.sum()),
        "total_acres_est": round(total_acres, 2),
        "images_used": len(images_used),
        "median_score": round(float(np.nanmedian(score[valid])), 3) if valid.any() else math.nan,
        "median_confidence": round(float(np.nanmedian(confidence[valid])), 3) if valid.any() else math.nan,
    }
    labels = {1: "investigate", 2: "monitor", 3: "stable", 4: "strong"}
    for value, label in labels.items():
        count = int((zones == value).sum())
        acres = count * area
        stats[f"{label}_pixels"] = count
        stats[f"{label}_acres_est"] = round(float(acres), 2)
        stats[f"{label}_pct"] = round(float(100 * count / valid.sum()), 2) if valid.any() else 0.0
    return stats


def export_zone_vectors(
    site: str,
    zones: np.ndarray,
    score: np.ndarray,
    persistence: np.ndarray,
    confidence: np.ndarray,
    profile: dict[str, Any],
    out_path: Path,
) -> int:
    records: list[dict[str, Any]] = []
    geoms = []
    area = pixel_area_acres(profile)
    patch_id = 1
    for geom, value in shapes(zones.astype("uint8"), mask=zones > 0, transform=profile["transform"]):
        zone_value = int(value)
        if zone_value not in ZONE_LABELS:
            continue
        geom_mask = geometry_mask(
            [geom],
            out_shape=zones.shape,
            transform=profile["transform"],
            invert=True,
            all_touched=False,
        )
        patch_pixels = geom_mask & (zones == zone_value)
        count = int(patch_pixels.sum())
        if count == 0:
            continue
        label = ZONE_LABELS[zone_value]
        records.append(
            {
                "site": site,
                "patch_id": patch_id,
                "zone_value": zone_value,
                "zone_class": label,
                "pixels": count,
                "acres_est": round(float(count * area), 3),
                "mean_score": round(float(np.nanmean(score[patch_pixels])), 4),
                "mean_persistence": round(float(np.nanmean(persistence[patch_pixels])), 4),
                "mean_confidence": round(float(np.nanmean(confidence[patch_pixels])), 4),
                "recommendation": ZONE_RECOMMENDATIONS[zone_value],
            }
        )
        geoms.append(shape(geom))
        patch_id += 1

    if not records:
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vector_gdf = gpd.GeoDataFrame(records, geometry=geoms, crs=profile["crs"]).to_crs(4326)
    vector_gdf.to_file(out_path, driver="GeoJSON")
    return len(records)


def triggered_indices_for_pixels(index_trigger_frequency: dict[str, np.ndarray], pixels: np.ndarray) -> str:
    triggered = [
        idx
        for idx in INDICES
        if pixels.any()
        and idx in index_trigger_frequency
        and np.isfinite(index_trigger_frequency[idx][pixels]).any()
        and float(np.nanmean(index_trigger_frequency[idx][pixels])) >= 0.25
    ]
    return ";".join(triggered) if triggered else "mixed_low_agreement"


def scouting_priority_rows(result: SiteResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    area = pixel_area_acres(result.profile)
    patch_id = 1
    priority_zones = np.where(np.isin(result.zones, list(UNDERPERFORMANCE_ZONE_VALUES)), result.zones, 0).astype("uint8")
    for geom, value in shapes(priority_zones, mask=priority_zones > 0, transform=result.profile["transform"]):
        zone_value = int(value)
        geom_mask = geometry_mask(
            [geom],
            out_shape=result.zones.shape,
            transform=result.profile["transform"],
            invert=True,
            all_touched=False,
        )
        patch_pixels = geom_mask & (priority_zones == zone_value)
        if not patch_pixels.any():
            continue
        geom_obj = shape(geom)
        centroid_wgs84 = gpd.GeoSeries([geom_obj.centroid], crs=result.profile["crs"]).to_crs(4326).iloc[0]
        rows.append(
            {
                "site_id": result.site,
                "zone_id": f"{result.site}_priority_{patch_id:03d}",
                "priority_class": ZONE_LABELS.get(zone_value, "Scouting priority"),
                "approx_area_acres": round(float(patch_pixels.sum() * area), 3),
                "persistence_score": round(float(np.nanmean(result.persistence[patch_pixels])), 4),
                "indices_triggered": triggered_indices_for_pixels(result.index_trigger_frequency, patch_pixels),
                "valid_observation_count": round(float(np.nanmean(result.valid_observation_count[patch_pixels])), 2),
                "mean_relative_underperformance": round(float(np.nanmean(result.score[patch_pixels])), 4),
                "centroid_lat": round(float(centroid_wgs84.y), 7),
                "centroid_lon": round(float(centroid_wgs84.x), 7),
                "recommended_followup": "Scout this zone in the field; compare canopy condition, irrigation distribution, pest signs, soil variability, and management records.",
            }
        )
        patch_id += 1
    return rows


def zone_timeseries(site: str, years: list[int], yearly: dict[int, dict[str, np.ndarray]], zones: np.ndarray, score: np.ndarray) -> list[dict[str, Any]]:
    stress_zone = zones == 1
    reference_zone = zones == 4

    valid_score = np.isfinite(score) & (zones > 0)
    if stress_zone.sum() < 10 and valid_score.sum() > 0:
        cutoff = float(np.nanpercentile(score[valid_score], 80))
        stress_zone = valid_score & (score >= cutoff)
    if reference_zone.sum() < 10 and valid_score.sum() > 0:
        cutoff = float(np.nanpercentile(score[valid_score], 20))
        reference_zone = valid_score & (score <= cutoff)

    rows: list[dict[str, Any]] = []
    for year in years:
        arrays = yearly.get(year)
        if not arrays:
            continue
        row: dict[str, Any] = {
            "site": site,
            "year": year,
            "stress_pixels": int(stress_zone.sum()),
            "reference_pixels": int(reference_zone.sum()),
        }
        for idx in INDICES:
            row[f"{idx}_stress_median"] = float(np.nanmedian(arrays[idx][stress_zone]))
            row[f"{idx}_reference_median"] = float(np.nanmedian(arrays[idx][reference_zone]))
            row[f"{idx}_gap_reference_minus_stress"] = row[f"{idx}_reference_median"] - row[f"{idx}_stress_median"]
        rows.append(row)
    return rows


def save_raster(path: Path, arr: np.ndarray, profile: dict[str, Any], dtype: str, nodata: float | int) -> None:
    out_profile = profile.copy()
    out_profile.update(driver="GTiff", count=1, dtype=dtype, nodata=nodata, compress="deflate")
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(arr.astype(dtype), 1)


def raster_extent(profile: dict[str, Any]) -> tuple[float, float, float, float]:
    west, south, east, north = array_bounds(profile["height"], profile["width"], profile["transform"])
    return west, east, south, north


def mask_bounds(mask_arr: np.ndarray, profile: dict[str, Any]) -> tuple[float, float, float, float] | None:
    if not mask_arr.any():
        return None
    rows, cols = np.where(mask_arr)
    transform = profile["transform"]
    left = transform.c + int(cols.min()) * transform.a
    right = transform.c + (int(cols.max()) + 1) * transform.a
    top = transform.f + int(rows.min()) * transform.e
    bottom = transform.f + (int(rows.max()) + 1) * transform.e
    west, east = sorted((left, right))
    south, north = sorted((bottom, top))
    return west, east, south, north


def apply_focus_extent(ax, result: SiteResult, pad_fraction: float = 0.04) -> None:
    bounds = mask_bounds(result.canopy_mask, result.profile)
    if bounds is None:
        bounds = raster_extent(result.profile)
    west, east, south, north = bounds
    span = max(east - west, north - south)
    pixel = max(abs(result.profile["transform"].a), abs(result.profile["transform"].e))
    pad = max(span * pad_fraction, pixel * 3)
    ax.set_xlim(west - pad, east + pad)
    ax.set_ylim(south - pad, north + pad)


def apply_mask_extent(ax, mask_arr: np.ndarray, profile: dict[str, Any], pad_fraction: float = 0.08) -> None:
    bounds = mask_bounds(mask_arr, profile)
    if bounds is None:
        bounds = raster_extent(profile)
    west, east, south, north = bounds
    span = max(east - west, north - south)
    pixel = max(abs(profile["transform"].a), abs(profile["transform"].e))
    pad = max(span * pad_fraction, pixel * 4)
    ax.set_xlim(west - pad, east + pad)
    ax.set_ylim(south - pad, north + pad)


def apply_bounds_extent(
    ax,
    bounds: tuple[float, float, float, float],
    profile: dict[str, Any],
    pad_fraction: float = 0.20,
    min_span_pixels: int = 40,
) -> None:
    west, east, south, north = bounds
    center_x = (west + east) / 2
    center_y = (south + north) / 2
    pixel = max(abs(profile["transform"].a), abs(profile["transform"].e))
    span = max(east - west, north - south, pixel * min_span_pixels)
    pad = max(span * pad_fraction, pixel * 4)
    half = span / 2 + pad
    ax.set_xlim(center_x - half, center_x + half)
    ax.set_ylim(center_y - half, center_y + half)


def apply_map_display_extent(ax, result: SiteResult, pad_fraction: float = 0.025) -> bool:
    """Apply the readable display extent. Returns True when a special priority zoom was used."""
    display_bounds, zoomed = map_display_bounds(result, pad_fraction=pad_fraction)
    apply_display_bounds(ax, display_bounds)
    return zoomed


def public_site_note(site: str) -> str:
    if site == PARTNER_SITE_ID:
        return "Partner boundary is treated as the strongest orchard-specific example."
    return "Public boundary: interpret cautiously because crop context may be mixed or unverified."


def plot_site_map(result: SiteResult, gdf_wgs84: gpd.GeoDataFrame, out_path: Path) -> None:
    cmap = ListedColormap(
        [
            (0, 0, 0, 0),
            "#B42318",
            "#F79009",
            "#A6C8A0",
            "#1A7F37",
        ]
    )
    norm = BoundaryNorm([0, 1, 2, 3, 4, 5], cmap.N)
    extent = raster_extent(result.profile)
    boundary = gdf_wgs84.to_crs(result.profile["crs"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    ax.set_facecolor("#E5E7EB")
    ndvi = np.ma.masked_where(~result.canopy_mask | ~np.isfinite(result.mean_ndvi), result.mean_ndvi)
    ax.imshow(ndvi, cmap="YlGn", extent=extent, origin="upper", vmin=0.0, vmax=0.8)
    masked_zones = np.ma.masked_where(result.zones == 0, result.zones)
    im = ax.imshow(masked_zones, cmap=cmap, norm=norm, extent=extent, origin="upper", alpha=0.78)
    boundary.boundary.plot(ax=ax, color="black", linewidth=1.2)
    apply_map_display_extent(ax, result)
    ax.set_title(f"{site_display_name(result.site)} Scouting-Priority Zones", fontweight="bold")
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")
    ax.ticklabel_format(style="plain", useOffset=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, ticks=[1.5, 2.5, 3.5, 4.5])
    cbar.ax.set_yticklabels(["Scout first", "Monitor", "Stable", "Strong ref."])

    ax2 = axes[1]
    labels = ["Scout first", "Monitor", "Stable", "Strong ref."]
    pcts = [
        result.summary.get("investigate_pct", 0),
        result.summary.get("monitor_pct", 0),
        result.summary.get("stable_pct", 0),
        result.summary.get("strong_pct", 0),
    ]
    colors = ["#B42318", "#F79009", "#A6C8A0", "#1A7F37"]
    ax2.barh(labels, pcts, color=colors)
    ax2.set_xlim(0, max(5, max(pcts) * 1.15 if pcts else 100))
    ax2.set_xlabel("Share of eligible canopy pixels (%)")
    ax2.set_title("Zone Mix")
    for i, pct in enumerate(pcts):
        ax2.text(pct + 0.4, i, f"{pct:.1f}%", va="center", fontsize=9)
    note = (
        f"Images used: {result.summary['images_used']}\n"
        f"Median confidence: {result.summary['median_confidence']}\n"
        f"Eligible canopy area: {result.summary['total_acres_est']} acres\n\n"
        "Score uses clear Sentinel-2 pixels,\n"
        "eligible canopy masking, within-site\n"
        "baselines, and multi-year persistence.\n\n"
        f"{public_site_note(result.site)}"
    )
    ax2.text(0.02, -0.42, note, transform=ax2.transAxes, va="top", fontsize=9)
    ax2.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_canopy_diagnostic(result: SiteResult, gdf_wgs84: gpd.GeoDataFrame, out_path: Path) -> None:
    extent = raster_extent(result.profile)
    boundary = gdf_wgs84.to_crs(result.profile["crs"])
    zone_cmap = ListedColormap([(0, 0, 0, 0), "#B42318", "#F79009", "#A6C8A0", "#1A7F37"])
    zone_norm = BoundaryNorm([0, 1, 2, 3, 4, 5], zone_cmap.N)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6))
    for ax in axes:
        ax.set_facecolor("#E5E7EB")
        apply_focus_extent(ax, result)
        ax.ticklabel_format(style="plain", useOffset=False)

    obs = np.ma.masked_where(~result.canopy_mask, result.valid_observation_count)
    im0 = axes[0].imshow(obs, cmap="viridis", extent=extent, origin="upper")
    axes[0].imshow(np.ma.masked_where(result.canopy_mask, np.ones_like(result.canopy_mask)), cmap=ListedColormap([(0, 0, 0, 0.12)]), extent=extent, origin="upper")
    boundary.boundary.plot(ax=axes[0], color="black", linewidth=1.0)
    axes[0].set_title("Eligible Canopy Mask and Clear Observations", fontweight="bold")
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.03, label="Clear observations")

    canopy = np.ma.masked_where(~result.canopy_mask, np.ones_like(result.canopy_mask, dtype="uint8"))
    axes[1].imshow(canopy, cmap=ListedColormap(["#7FB77E"]), extent=extent, origin="upper", alpha=0.42)
    priority = np.ma.masked_where(~result.underperformance_mask, result.zones)
    axes[1].imshow(priority, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.82)
    boundary.boundary.plot(ax=axes[1], color="black", linewidth=1.0)
    axes[1].set_title("Canopy Mask vs. Scouting-Priority Zones", fontweight="bold")
    for ax in axes:
        apply_focus_extent(ax, result)

    fig.suptitle(f"{site_display_name(result.site)} Canopy Eligibility Diagnostic", fontweight="bold")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_canopy_priority_overlay(result: SiteResult, gdf_wgs84: gpd.GeoDataFrame, out_path: Path) -> None:
    extent = raster_extent(result.profile)
    boundary = gdf_wgs84.to_crs(result.profile["crs"])
    zone_cmap = scouting_zone_cmap(include_stable=False)
    zone_norm = BoundaryNorm([0, 1, 2, 3], zone_cmap.N)

    display_bounds, zoomed = map_display_bounds(result, pad_fraction=0.025)
    fig, ax = map_figure_canvas(
        display_bounds,
        f"{site_display_name(result.site)} Canopy Mask vs. Scouting-Priority Zones",
        "Priority colors are clipped to eligible canopy only. Roads, canals, bare ground, and margins remain excluded.",
    )

    canopy = np.ma.masked_where(~result.canopy_mask, np.ones_like(result.canopy_mask, dtype="uint8"))
    ax.imshow(canopy, cmap=ListedColormap(["#C7DBC6"]), extent=extent, origin="upper", alpha=0.62)

    priority = np.where(np.isin(result.zones, list(UNDERPERFORMANCE_ZONE_VALUES)), result.zones, 0).astype("uint8")
    priority_masked = np.ma.masked_where(priority == 0, priority)
    ax.imshow(priority_masked, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.88)

    boundary.boundary.plot(ax=ax, color=BOUNDARY_COLOR, linewidth=1.25)
    apply_display_bounds(ax, display_bounds)
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")
    ax.ticklabel_format(style="plain", useOffset=False)
    style_map_axes(ax)

    canopy_bounds = mask_bounds(result.canopy_mask, result.profile)
    priority_focus = priority > 0
    focus_mask = priority_focus if priority_focus.any() else result.canopy_mask
    focus_bounds = mask_bounds(focus_mask, result.profile)
    if not zoomed and canopy_bounds and focus_bounds:
        main_span = max(canopy_bounds[1] - canopy_bounds[0], canopy_bounds[3] - canopy_bounds[2])
        focus_span = max(focus_bounds[1] - focus_bounds[0], focus_bounds[3] - focus_bounds[2])
        if main_span > 0 and focus_span < main_span * 0.25:
            inset = ax.inset_axes([0.58, 0.57, 0.38, 0.38])
            inset.set_facecolor(EXCLUDED_COLOR)
            inset.imshow(canopy, cmap=ListedColormap(["#C7DBC6"]), extent=extent, origin="upper", alpha=0.62)
            inset.imshow(priority_masked, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.88)
            boundary.boundary.plot(ax=inset, color=BOUNDARY_COLOR, linewidth=0.8)
            apply_mask_extent(inset, focus_mask, result.profile, pad_fraction=0.20)
            inset.set_title("detail", fontsize=9, weight="bold")
            inset.set_xticks([])
            inset.set_yticks([])
            for spine in inset.spines.values():
                spine.set_edgecolor(BOUNDARY_COLOR)
                spine.set_linewidth(1.0)

    draw_figure_legend(fig, zone_legend_handles(include_canopy=True, include_stable=False), y=legend_y_below_axis(fig, ax, min_y=0.055, gap=0.115), ncol=5)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def plot_report_zone_map(result: SiteResult, gdf_wgs84: gpd.GeoDataFrame, out_path: Path) -> None:
    extent = raster_extent(result.profile)
    boundary = gdf_wgs84.to_crs(result.profile["crs"])
    zone_cmap = scouting_zone_cmap(include_stable=True)
    zone_norm = BoundaryNorm([0, 1, 2, 3, 4, 5], zone_cmap.N)

    display_bounds, zoomed = map_display_bounds(result, pad_fraction=0.025)
    fig, ax = map_figure_canvas(
        display_bounds,
        f"{site_display_name(result.site)} Scouting-Priority Zone Map",
        public_site_note(result.site),
    )
    ndvi = np.ma.masked_where(~result.canopy_mask | ~np.isfinite(result.mean_ndvi), result.mean_ndvi)
    ax.imshow(ndvi, cmap="YlGn", extent=extent, origin="upper", vmin=0.0, vmax=0.8, interpolation="nearest")
    zone_layer = np.ma.masked_where(result.zones == 0, result.zones)
    ax.imshow(zone_layer, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.82, interpolation="nearest")
    boundary.boundary.plot(ax=ax, color=BOUNDARY_COLOR, linewidth=1.25)
    apply_display_bounds(ax, display_bounds)
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")
    ax.ticklabel_format(style="plain", useOffset=False)
    style_map_axes(ax)

    priority_focus = np.isin(result.zones, list(UNDERPERFORMANCE_ZONE_VALUES))
    focus_mask = priority_focus if priority_focus.any() else result.canopy_mask
    canopy_bounds = mask_bounds(result.canopy_mask, result.profile)
    focus_bounds = mask_bounds(focus_mask, result.profile)
    if not zoomed and canopy_bounds and focus_bounds:
        main_span = max(canopy_bounds[1] - canopy_bounds[0], canopy_bounds[3] - canopy_bounds[2])
        focus_span = max(focus_bounds[1] - focus_bounds[0], focus_bounds[3] - focus_bounds[2])
        if main_span > 0 and focus_span < main_span * 0.30:
            inset = ax.inset_axes([0.54, 0.54, 0.42, 0.40])
            inset.set_facecolor(EXCLUDED_COLOR)
            inset.imshow(ndvi, cmap="YlGn", extent=extent, origin="upper", vmin=0.0, vmax=0.8, interpolation="nearest")
            inset.imshow(zone_layer, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.88, interpolation="nearest")
            boundary.boundary.plot(ax=inset, color=BOUNDARY_COLOR, linewidth=0.8)
            apply_mask_extent(inset, focus_mask, result.profile, pad_fraction=0.22)
            inset.set_title("priority detail", fontsize=9, weight="bold")
            inset.set_xticks([])
            inset.set_yticks([])
            for spine in inset.spines.values():
                spine.set_edgecolor(BOUNDARY_COLOR)
                spine.set_linewidth(1.0)

    draw_figure_legend(fig, zone_legend_handles(include_canopy=False, include_stable=True), y=legend_y_below_axis(fig, ax, min_y=0.055, gap=0.115), ncol=6)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def plot_timeseries(result: SiteResult, out_path: Path) -> None:
    rows = result.timeseries_rows
    if not rows:
        return
    years = [row["year"] for row in rows]
    fig, axes = plt.subplots(1, len(INDICES), figsize=(4.8 * len(INDICES), 4.5), sharex=True)
    if len(INDICES) == 1:
        axes = [axes]
    for ax, idx in zip(axes, INDICES):
        stress = [row[f"{idx}_stress_median"] for row in rows]
        reference = [row[f"{idx}_reference_median"] for row in rows]
        ax.plot(years, reference, marker="o", color="#1A7F37", label="Strong reference zone")
        ax.plot(years, stress, marker="o", color="#B42318", label="Scouting-priority zone")
        ax.fill_between(years, stress, reference, color="#F79009", alpha=0.18)
        ax.set_title(idx)
        ax.set_xticks(years)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Seasonal median index value")
    axes[0].legend(fontsize=8, loc="best")
    fig.suptitle(f"{result.site.replace('_', ' ').title()}: Strong Reference vs Scouting Priority", fontweight="bold")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def process_site(
    client: PcClient,
    site_path: Path,
    years: list[int],
    season: tuple[str, str],
    cloud_lt: float,
    stac_source: str,
    images_per_year: int,
    min_zone_pixels: int,
    spatial_dir: Path,
    figures_dir: Path,
) -> SiteResult | None:
    site, gdf = load_site(site_path)
    bbox = tuple(float(v) for v in gdf.total_bounds)
    print(f"\n[{site}] searching Sentinel-2 items for {years}...")
    items_by_year: dict[int, list[dict[str, Any]]] = {}
    for year in years:
        items = search_items(client, bbox, year, season, cloud_lt, stac_source)
        if not items:
            items = search_items(client, bbox, year, ("03-01", "10-31"), min(60.0, cloud_lt * 2), stac_source)
        items_by_year[year] = items
        print(f"  {year}: {len(items)} candidates")

    tile = choose_tile(items_by_year)
    print(f"  selected tile: {tile or 'mixed'}")
    yearly_images: dict[int, list[ImageResult]] = {}
    master_profile: dict[str, Any] | None = None
    images_used: list[ImageResult] = []

    for year, items in items_by_year.items():
        if tile:
            tile_items = [item for item in items if item_tile(item) == tile]
            if tile_items:
                items = tile_items
        picks = select_month_balanced_items(items, images_per_year)
        yearly_images[year] = []
        for item in picks:
            props = item.get("properties", {})
            print(f"  {year}: reading {props.get('datetime', '')[:10]} cloud={props.get('eo:cloud_cover')}")
            try:
                result = compute_item_indices(client, item, gdf)
            except Exception as exc:  # noqa: BLE001
                print(f"    skipped {item.get('id', '')}: {exc}")
                continue
            if master_profile is None:
                master_profile = result.profile
            aligned = {
                idx: align_array(result.arrays[idx], result.profile, master_profile)
                for idx in INDICES
            }
            result.arrays = aligned
            result.profile = master_profile
            yearly_images[year].append(result)
            images_used.append(result)

    if master_profile is None:
        print(f"  no usable imagery for {site}")
        return None

    yearly: dict[int, dict[str, np.ndarray]] = {}
    for year, images in yearly_images.items():
        if not images:
            continue
        yearly[year] = {}
        for idx in INDICES:
            stack = np.stack([image.arrays[idx] for image in images])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                yearly[year][idx] = np.nanmedian(stack, axis=0).astype("float32")

    if len(yearly) < 2:
        print(f"  not enough years for persistence scoring: {site}")
        return None

    canopy_mask, valid_observation_count, canopy_diagnostics = build_canopy_mask(images_used, master_profile, gdf)
    if not canopy_mask.any():
        print(f"  no eligible persistent canopy/vegetation pixels for {site}")
        return None

    zones, score, persistence, confidence, mean_ndvi, index_trigger_frequency = classify_zones(
        yearly,
        master_profile,
        gdf,
        min_zone_pixels,
        canopy_mask,
    )
    underperformance_mask = np.isin(zones, list(UNDERPERFORMANCE_ZONE_VALUES))
    assert not np.any(underperformance_mask & ~canopy_mask), f"{site}: underperformance outside canopy mask"
    assert not np.any((zones > 0) & ~canopy_mask), f"{site}: zone pixels outside canopy mask"

    summary = summarize(site, zones, score, confidence, master_profile, images_used)
    summary.update(
        {
            "eligible_canopy_pixels": canopy_diagnostics["canopy_pixels"],
            "eligible_canopy_acres_est": canopy_diagnostics["canopy_acres_est"],
            "canopy_min_valid_obs": canopy_diagnostics["min_valid_obs"],
            "canopy_ndvi_p75_min": canopy_diagnostics["ndvi_p75_min"],
            "canopy_ndvi_median_min": canopy_diagnostics["ndvi_median_min"],
            "canopy_evi2_p75_min": canopy_diagnostics["evi2_p75_min"],
            "median_clear_observations_canopy": canopy_diagnostics["median_valid_observations"],
        }
    )
    ts_rows = zone_timeseries(site, sorted(yearly), yearly, zones, score)

    save_raster(spatial_dir / f"{site}_canopy_mask.tif", canopy_mask.astype("uint8"), master_profile, "uint8", 0)
    save_raster(spatial_dir / f"{site}_valid_observation_count.tif", valid_observation_count, master_profile, "uint16", 0)
    save_raster(spatial_dir / f"{site}_underperformance_mask.tif", underperformance_mask.astype("uint8"), master_profile, "uint8", 0)
    save_raster(spatial_dir / f"{site}_underperformance_score.tif", score, master_profile, "float32", np.nan)
    save_raster(spatial_dir / f"{site}_persistence.tif", persistence, master_profile, "float32", np.nan)
    save_raster(spatial_dir / f"{site}_confidence.tif", confidence, master_profile, "float32", np.nan)
    save_raster(spatial_dir / f"{site}_mean_ndvi.tif", mean_ndvi, master_profile, "float32", np.nan)
    save_raster(spatial_dir / f"{site}_zones.tif", zones, master_profile, "uint8", 0)
    vector_patches = export_zone_vectors(
        site,
        zones,
        score,
        persistence,
        confidence,
        master_profile,
        spatial_dir / f"{site}_zones.geojson",
    )
    summary["zone_vector_patches"] = vector_patches
    summary["zone_vector_file"] = f"{site}_zones.geojson"

    result = SiteResult(
        site=site,
        years=sorted(yearly),
        yearly=yearly,
        profile=master_profile,
        canopy_mask=canopy_mask,
        valid_observation_count=valid_observation_count,
        zones=zones,
        score=score,
        persistence=persistence,
        confidence=confidence,
        mean_ndvi=mean_ndvi,
        underperformance_mask=underperformance_mask,
        index_trigger_frequency=index_trigger_frequency,
        summary=summary,
        timeseries_rows=ts_rows,
    )
    plot_site_map(result, gdf, figures_dir / f"{site}_stress_zones.png")
    plot_report_zone_map(result, gdf, figures_dir / f"{site}_report_zone_map.png")
    plot_canopy_diagnostic(result, gdf, figures_dir / f"{site}_canopy_mask_diagnostic.png")
    plot_canopy_priority_overlay(result, gdf, figures_dir / f"{site}_canopy_priority_overlay.png")
    plot_timeseries(result, figures_dir / f"{site}_zone_timeseries.png")

    with (spatial_dir / f"{site}_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with (spatial_dir / f"{site}_zone_timeseries.csv").open("w", encoding="utf-8") as f:
        if ts_rows:
            cols = list(ts_rows[0].keys())
            f.write(",".join(cols) + "\n")
            for row in ts_rows:
                f.write(",".join(str(row[col]) for col in cols) + "\n")

    print(f"  wrote outputs for {site}: {summary}")
    return result


def overview_order(results: list[SiteResult]) -> list[SiteResult]:
    by_site = {result.site: result for result in results}
    ordered = [by_site[site] for site in OVERVIEW_SITE_ORDER if site in by_site]
    ordered.extend(result for result in results if result.site not in OVERVIEW_SITE_ORDER)
    return ordered


def plot_overview_panel(ax, result: SiteResult) -> None:
    extent = raster_extent(result.profile)
    zone_cmap = scouting_zone_cmap(include_stable=True)
    zone_norm = BoundaryNorm([0, 1, 2, 3, 4, 5], zone_cmap.N)
    ndvi = np.ma.masked_where(~result.canopy_mask | ~np.isfinite(result.mean_ndvi), result.mean_ndvi)
    zone_layer = np.ma.masked_where(result.zones == 0, result.zones)
    ax.set_facecolor(EXCLUDED_COLOR)
    ax.imshow(ndvi, cmap="YlGn", extent=extent, origin="upper", vmin=0.0, vmax=0.8, interpolation="nearest")
    ax.imshow(zone_layer, cmap=zone_cmap, norm=zone_norm, extent=extent, origin="upper", alpha=0.84, interpolation="nearest")
    apply_map_display_extent(ax, result, pad_fraction=0.035)
    ax.set_axis_off()
    title = site_display_name(result.site)
    if result.site == PARTNER_SITE_ID:
        title = f"{title} | orchard-specific"
    ax.set_title(title, fontsize=11, weight="bold", color=BOUNDARY_COLOR, pad=6)
    scout_acres = result.summary.get("investigate_acres_est", "")
    canopy_acres = result.summary.get("eligible_canopy_acres_est", result.summary.get("total_acres_est", ""))
    subtitle = f"Scout first: {scout_acres} ac | Canopy: {canopy_acres} ac"
    ax.text(
        0.02,
        0.02,
        subtitle,
        transform=ax.transAxes,
        fontsize=7.5,
        color="#33423E",
        va="bottom",
        ha="left",
        bbox={"boxstyle": "square,pad=0.25", "facecolor": "white", "edgecolor": GRID_COLOR, "alpha": 0.88},
    )


def plot_combined_zone_map(results: list[SiteResult], figures_dir: Path) -> None:
    if not results:
        return
    ordered = overview_order(results)
    ncols = 3
    nrows = math.ceil(len(ordered) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 9.8), squeeze=False, facecolor=PAPER_COLOR)
    flat_axes = list(axes.ravel())
    for ax, result in zip(flat_axes, ordered):
        plot_overview_panel(ax, result)
    for ax in flat_axes[len(ordered) :]:
        ax.axis("off")
    fig.text(0.055, 0.965, "Six-Site Scouting-Priority Overview", fontsize=18, weight="bold", color=BOUNDARY_COLOR, va="top")
    fig.text(
        0.055,
        0.925,
        "Partner site is the primary orchard-specific proof point. Public boundaries show six-site pipeline coverage and should be interpreted cautiously.",
        fontsize=9.5,
        color="#33423E",
        va="top",
    )
    fig.subplots_adjust(left=0.055, right=0.955, top=0.86, bottom=0.16, wspace=0.12, hspace=0.22)
    draw_figure_legend(fig, zone_legend_handles(include_canopy=False, include_stable=True), y=0.065, ncol=6)
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / "spatial_zone_maps.png", dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_combined_outputs(results: list[SiteResult], spatial_dir: Path, figures_dir: Path, report_dir: Path) -> None:
    if not results:
        return
    summary_cols = list(results[0].summary.keys())
    with (spatial_dir / "spatial_zone_summary.csv").open("w", encoding="utf-8") as f:
        f.write(",".join(summary_cols) + "\n")
        for result in results:
            f.write(",".join(str(result.summary.get(col, "")) for col in summary_cols) + "\n")

    ts_rows = [row for result in results for row in result.timeseries_rows]
    if ts_rows:
        cols = list(ts_rows[0].keys())
        with (spatial_dir / "zone_timeseries_all_sites.csv").open("w", encoding="utf-8") as f:
            f.write(",".join(cols) + "\n")
            for row in ts_rows:
                f.write(",".join(str(row[col]) for col in cols) + "\n")

    priority_rows = [row for result in results for row in scouting_priority_rows(result)]
    report_dir.mkdir(parents=True, exist_ok=True)
    priority_cols = [
        "site_id",
        "zone_id",
        "priority_class",
        "approx_area_acres",
        "persistence_score",
        "indices_triggered",
        "valid_observation_count",
        "mean_relative_underperformance",
        "centroid_lat",
        "centroid_lon",
        "recommended_followup",
    ]
    with (report_dir / "scouting_priority_table.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=priority_cols)
        writer.writeheader()
        writer.writerows(priority_rows)

    plot_combined_zone_map(results, figures_dir)


def write_methodology_notes(args: argparse.Namespace, results: list[SiteResult], spatial_dir: Path) -> None:
    notes = {
        "pipeline": "Persistent Orchard Underperformance Mapper",
        "indices_used": list(INDICES),
        "scl_masked_classes": sorted(CLOUD_SCL_CLASSES),
        "canopy_mask": CANOPY_MASK_CONFIG,
        "years_requested": args.years,
        "season_start": args.season_start,
        "season_end": args.season_end,
        "cloud_lt": args.cloud_lt,
        "stac_source": args.stac_source,
        "images_per_year": args.images_per_year,
        "min_zone_pixels": args.min_zone_pixels,
        "underperformance_rule": "Mean robust within-site deficit across eligible canopy pixels; scout-first requires score >= 0.75, persistence >= 0.50, confidence >= 0.50.",
        "agreement_rule": "At least two indices below -0.5 robust z-score in a pixel-year support underperformance agreement.",
        "confidence_rule": "Valid-year fraction multiplied by an agreement-weighted confidence term.",
        "sites_completed": [result.site for result in results],
        "outputs": {
            "rasters": "*_canopy_mask.tif, *_underperformance_mask.tif, *_zones.tif, *_underperformance_score.tif, *_persistence.tif, *_confidence.tif, *_mean_ndvi.tif",
            "vectors": "*_zones.geojson",
            "tables": "spatial_zone_summary.csv, zone_timeseries_all_sites.csv, output/report/scouting_priority_table.csv",
            "figures": "*_stress_zones.png, *_report_zone_map.png, *_canopy_priority_overlay.png, *_canopy_mask_diagnostic.png, *_zone_timeseries.png, spatial_zone_maps.png",
        },
    }
    spatial_dir.mkdir(parents=True, exist_ok=True)
    with (spatial_dir / "methodology_notes.json").open("w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Sentinel-2 persistent underperformance scouting-priority zones.")
    parser.add_argument("--sites", nargs="+", default=list(ALL_SITE_IDS), help="Site IDs to process, or 'all' for the six challenge boundaries.")
    parser.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023, 2024])
    parser.add_argument("--season-start", default="06-01", help="MM-DD")
    parser.add_argument("--season-end", default="08-31", help="MM-DD")
    parser.add_argument("--cloud-lt", type=float, default=15.0)
    parser.add_argument("--stac-source", choices=["auto", "earth-search", "planetary-computer"], default="auto")
    parser.add_argument("--images-per-year", type=int, default=2)
    parser.add_argument("--min-zone-pixels", type=int, default=9, help="Minimum connected pixels for visible management patches.")
    parser.add_argument("--geojson-dir", default="data/geojsons")
    parser.add_argument("--spatial-dir", default="output/spatial")
    parser.add_argument("--figures-dir", default="output/figures")
    parser.add_argument("--report-dir", default="output/report")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def normalize_sites(raw_sites: list[str]) -> list[str]:
    if any(site.lower() == "all" for site in raw_sites):
        return list(ALL_SITE_IDS)
    ordered: list[str] = []
    seen: set[str] = set()
    for site in raw_sites:
        if site not in seen:
            ordered.append(site)
            seen.add(site)
    return ordered


def main() -> None:
    args = parse_args()
    args.sites = normalize_sites(args.sites)
    geojson_dir = Path(args.geojson_dir)
    spatial_dir = Path(args.spatial_dir)
    figures_dir = Path(args.figures_dir)
    report_dir = Path(args.report_dir)
    client = PcClient(timeout=args.timeout)
    results: list[SiteResult] = []

    for site in args.sites:
        path = geojson_dir / f"{site}.geojson"
        if not path.exists():
            print(f"missing site boundary: {path}")
            continue
        result = process_site(
            client,
            path,
            args.years,
            (args.season_start, args.season_end),
            args.cloud_lt,
            args.stac_source,
            args.images_per_year,
            args.min_zone_pixels,
            spatial_dir,
            figures_dir,
        )
        if result:
            results.append(result)

    write_combined_outputs(results, spatial_dir, figures_dir, report_dir)
    write_methodology_notes(args, results, spatial_dir)
    print(f"\nCompleted {len(results)} site(s). Summary: {spatial_dir / 'spatial_zone_summary.csv'}")


if __name__ == "__main__":
    main()
