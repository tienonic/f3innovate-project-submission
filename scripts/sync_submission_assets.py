"""Sync final F3 submission assets into the local Obsidian project folder.

The committed submission packet is the source of truth. This script updates the
local vault copies used by the visual report and final deliverables so a
regenerated map does not leave stale images in Obsidian.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = Path.home() / "Documents" / "vault" / "Projects" / "F3 Data Challenge"

GENERATED_FIGURE_PATTERNS = [
    "*_report_zone_map.png",
    "*_canopy_priority_overlay.png",
    "*_canopy_mask_diagnostic.png",
    "*_zone_timeseries.png",
    "*_stress_zones.png",
    "spatial_zone_maps.png",
    "pipeline_diagram.png",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_known_generated_figures(figures_dir: Path) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    targets: set[Path] = set()
    for pattern in GENERATED_FIGURE_PATTERNS:
        targets.update(path for path in figures_dir.glob(pattern) if path.is_file())
    removed: list[Path] = []
    for path in sorted(targets):
        path.unlink()
        removed.append(path)
    return removed


def verify_png_sync(src_dir: Path, dst_dir: Path) -> int:
    verified = 0
    for src in sorted(src_dir.glob("*.png")):
        if not src.is_file():
            continue
        dst = dst_dir / src.name
        if not dst.exists():
            raise FileNotFoundError(f"Missing synced PNG: {dst}")
        if sha256_file(src) != sha256_file(dst):
            raise ValueError(f"Synced PNG hash mismatch: {src.name}")
        verified += 1
    return verified


def copy_file(src: Path, dst: Path) -> Path:
    if not src.exists():
        raise FileNotFoundError(f"Missing source asset: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        shutil.copy2(src, tmp)
        if tmp.stat().st_size != src.stat().st_size:
            raise IOError(f"Incomplete temporary copy for {dst}")
        tmp.replace(dst)
        if dst.stat().st_size != src.stat().st_size or sha256_file(src) != sha256_file(dst):
            raise IOError(f"Synced file hash mismatch after copy: {dst}")
    finally:
        if tmp.exists():
            tmp.unlink()
    return dst


def copy_tree_files(src_dir: Path, dst_dir: Path, pattern: str) -> list[Path]:
    if not src_dir.exists():
        raise FileNotFoundError(f"Missing source directory: {src_dir}")
    copied: list[Path] = []
    for src in sorted(src_dir.glob(pattern)):
        if src.is_file():
            copied.append(copy_file(src, dst_dir / src.name))
    return copied


def sync_assets(vault_dir: Path) -> list[Path]:
    submission_dir = ROOT / "submission"
    figures_dir = submission_dir / "figures"
    report_dir = submission_dir / "report"
    tables_dir = submission_dir / "tables"

    copied: list[Path] = []
    vault_figures_dir = vault_dir / "figures"
    clean_known_generated_figures(vault_figures_dir)
    copied.extend(copy_tree_files(figures_dir, vault_figures_dir, "*.png"))
    verify_png_sync(figures_dir, vault_figures_dir)
    copied.append(
        copy_file(
            report_dir / "final_technical_report.pdf",
            vault_dir / "03 Deliverables" / "final_technical_report.pdf",
        )
    )
    copied.append(
        copy_file(
            report_dir / "grower_work_orders.md",
            vault_dir / "03 Deliverables" / "grower_work_orders.md",
        )
    )
    copied.append(
        copy_file(
            report_dir / "judge_review_guide.md",
            vault_dir / "03 Deliverables" / "judge_review_guide.md",
        )
    )
    copied.append(
        copy_file(
            submission_dir / "grower_quickstart.html",
            vault_dir / "03 Deliverables" / "grower_quickstart.html",
        )
    )
    for table_name in [
        "spatial_zone_summary.csv",
        "scouting_priority_table.csv",
        "grower_work_orders.csv",
        "field_verification_form_template.csv",
        "validation_sampling_plan.csv",
    ]:
        copied.append(copy_file(tables_dir / table_name, vault_dir / "03 Deliverables" / table_name))
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=DEFAULT_VAULT_DIR,
        help="Obsidian F3 project folder to update.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    copied = sync_assets(args.vault_dir)
    print(f"Synced {len(copied)} assets into {args.vault_dir}")
    for path in copied:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
