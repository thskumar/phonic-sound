"""Shared utilities: logging, paths, packaging."""

from __future__ import annotations

import logging
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure root logger for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    return logging.getLogger("pptx-to-html")


def ensure_dir(path: Path) -> Path:
    """Create directory if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_output_dir(path: Path) -> None:
    """Remove existing output directory before regeneration."""
    if path.exists():
        shutil.rmtree(path)


def copy_tree(src: Path, dst: Path) -> None:
    """Copy directory contents into destination."""
    if not src.is_dir():
        return
    ensure_dir(dst)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def create_zip(source_dir: Path, zip_path: Path) -> Path:
    """Package output folder as a distributable ZIP."""
    ensure_dir(zip_path.parent)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(source_dir.parent)
                zf.write(file, arcname)
    return zip_path


def slide_filename(index: int, ext: str = "png") -> str:
    """Zero-based index to slideN.ext (1-based naming)."""
    return f"slide{index + 1}.{ext}"


def iter_slide_indices(count: int) -> Iterable[int]:
    return range(count)
