"""Create the one-file local review folder for final F3 report reading."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "Final Submission Review"

REVIEW_FILES = {
    "F3_Orchard_Stress_Final_Report.pdf": ROOT / "submission" / "report" / "final_technical_report.pdf",
}


def prepare_review_folder(target: Path) -> list[Path]:
    resolved_root = ROOT.resolve()
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Review folder must stay inside the repo: {resolved_target}") from exc

    if resolved_target.name != "Final Submission Review":
        raise ValueError("Review folder name must be 'Final Submission Review'")

    resolved_target.mkdir(parents=True, exist_ok=True)
    expected_names = set(REVIEW_FILES)
    for child in resolved_target.iterdir():
        if child.is_file() and child.name not in expected_names:
            child.unlink()
        elif child.is_dir():
            raise ValueError(f"Unexpected directory in review folder: {child}")

    copied: list[Path] = []
    for filename, source in REVIEW_FILES.items():
        if not source.exists():
            raise FileNotFoundError(f"Missing source file: {source}")
        destination = resolved_target / filename
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    return parser.parse_args()


def main() -> int:
    copied = prepare_review_folder(parse_args().target)
    print("Prepared final review folder:")
    for path in copied:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
