"""Utility script to copy the local `zipvoice` package into `zipvoice_streaming/vendor`.

Run this once whenever you need a fresh vendored copy.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    project_root = root.parent
    src = project_root / "zipvoice"
    if not src.is_dir():
        raise SystemExit(f"Expected source package at {src}")

    vendor_root = root / "vendor"
    dest = vendor_root / "zipvoice"

    if dest.exists():
        shutil.rmtree(dest)

    vendor_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.so", "*.dll"),
    )
    print(f"Vendored zipvoice package copied to {dest}")


if __name__ == "__main__":
    main()
