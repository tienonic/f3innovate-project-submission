"""Refresh final figures, PDF, vault copies, and grower-facing assets."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = Path.home() / "Documents" / "vault" / "Projects" / "F3 Data Challenge"


def run_step(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==", flush=True)
    print(" ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def sync_workbench_report_copy() -> None:
    src = ROOT / "submission" / "report" / "final_technical_report.pdf"
    dst = ROOT / "output" / "report" / "final_technical_report.pdf"
    if not src.exists():
        raise FileNotFoundError(f"Missing final report: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Synced current final report to {dst}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=DEFAULT_VAULT_DIR,
        help="Obsidian F3 project folder to sync.",
    )
    parser.add_argument(
        "--skip-overlays",
        action="store_true",
        help="Skip rebuilding PNG overlays from existing spatial outputs.",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip rebuilding the final technical report PDF.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip submission verification.",
    )
    parser.add_argument(
        "--include-handout",
        action="store_true",
        help="Also rebuild the temporary one-page class handout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    py = sys.executable

    if not args.skip_overlays:
        run_step(
            "Rebuild submission figures from current spatial outputs",
            [
                py,
                "scripts/build_visual_overlays.py",
                "--sites",
                "all",
                "--geojson-dir",
                "data/geojsons",
                "--spatial-dir",
                "output/spatial",
                "--figures-dir",
                "submission/figures",
            ],
        )

    if not args.skip_pdf:
        run_step(
            "Rebuild final technical report PDF",
            [
                py,
                "scripts/build_final_report_pdf.py",
                "--figures-dir",
                "submission/figures",
                "--spatial-dir",
                "submission/tables",
                "--output",
                "submission/report/final_technical_report.pdf",
            ],
        )
        sync_workbench_report_copy()

    run_step(
        "Build grower work orders and field feedback templates",
        [py, "scripts/build_grower_work_orders.py"],
    )

    run_step(
        "Build standalone grower quickstart webpage",
        [py, "scripts/build_grower_quickstart_page.py"],
    )

    run_step(
        "Prepare one-file final submission review folder",
        [py, "scripts/prepare_final_review_folder.py"],
    )

    run_step(
        "Sync submission assets into Obsidian",
        [py, "scripts/sync_submission_assets.py", "--vault-dir", str(args.vault_dir)],
    )

    if args.include_handout:
        run_step(
            "Build temporary one-page class handout",
            [
                py,
                "scripts/build_class_handout_pdf.py",
                "--figures-dir",
                "submission/figures",
                "--vault-dir",
                str(args.vault_dir),
            ],
        )

    if not args.skip_verify:
        run_step(
            "Verify submission packet and synced vault assets",
            [py, "scripts/verify_submission_outputs.py", "--vault-dir", str(args.vault_dir)],
        )

    print("\nVisual asset refresh complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
