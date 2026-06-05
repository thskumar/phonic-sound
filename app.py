#!/usr/bin/env python3
"""
PPTX → Interactive HTML5 Learning App

Converts PowerPoint lessons into offline-friendly, touch-enabled HTML5 apps.
Narration uses your pre-recorded sounds in a ``sound/`` folder:

  soundX_1.mp3  → plays automatically when slide X opens
  soundX_2.mp3  → plays when the Speak Out button is pressed

Usage:
  python app.py lesson.pptx
  python app.py lesson.pptx --sound ./sound
  python app.py lesson.pptx --output ./interactive_lesson --zip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from audio_manager import copy_recorded_sounds
from html_generator import generate_app
from ppt_processor import process_pptx
from utils import clean_output_dir, create_zip, ensure_dir, setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PPTX to an interactive HTML5 learning app.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py lesson.pptx
  python app.py lesson.pptx --sound ./sound --output ./interactive_lesson
  python app.py lesson.pptx --zip --title "My Lesson"
  python app.py lesson.pptx --audio-only        # re-copy sounds + rebuild HTML

Sound naming convention (place files in the --sound folder):
  soundX_1.mp3  plays automatically when slide X opens
  soundX_2.mp3  plays when the Speak Out button is pressed
        """,
    )
    parser.add_argument(
        "pptx",
        type=Path,
        help="Path to input PowerPoint file (e.g. lesson.pptx)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("interactive_lesson"),
        help="Output folder (default: interactive_lesson)",
    )
    parser.add_argument(
        "-s",
        "--sound",
        type=Path,
        default=Path("sound"),
        help="Folder with recorded soundX_1.mp3 / soundX_2.mp3 (default: ./sound)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Lesson title for HTML and PWA manifest",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also create a ZIP package next to the output folder",
    )
    parser.add_argument(
        "--force-fallback",
        action="store_true",
        help="Skip PowerPoint COM export; use Pillow fallback slides",
    )
    parser.add_argument(
        "--no-pwa",
        action="store_true",
        help="Disable PWA manifest and service worker",
    )
    parser.add_argument(
        "--autoplay",
        action="store_true",
        help="Auto-advance to the next slide after the first sound finishes",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete output folder before building",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Reuse existing slide images; only re-copy sounds and rebuild HTML",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log = setup_logging(args.verbose)

    pptx_path = args.pptx.resolve()
    if not pptx_path.is_file():
        log.error("Input file not found: %s", pptx_path)
        return 1

    output_dir = args.output.resolve()
    if args.clean and output_dir.exists():
        log.info("Cleaning output directory: %s", output_dir)
        clean_output_dir(output_dir)

    slides_dir = ensure_dir(output_dir / "slides")
    audio_dir = ensure_dir(output_dir / "audio")
    ensure_dir(output_dir / "assets")

    title = args.title or pptx_path.stem.replace("_", " ").replace("-", " ").title()

    try:
        if args.audio_only:
            existing = sorted(slides_dir.glob("slide*.png"))
            if not existing:
                log.error(
                    "No slides found in %s. Run a full build first (without --audio-only).",
                    slides_dir,
                )
                return 1
            slide_count = len(existing)
            log.info("Audio-only mode: reusing %s existing slide image(s)", slide_count)
        else:
            log.info("Processing PPTX: %s", pptx_path)
            result = process_pptx(
                pptx_path,
                slides_dir,
                force_fallback=args.force_fallback,
                use_ocr=False,
            )
            slide_count = len(result.slides)
            log.info(
                "Slide export method: %s (%s slides)", result.method, slide_count
            )

        # Embed recorded narration (soundX_1 auto-plays, soundX_2 on Speak Out)
        sound_map = copy_recorded_sounds(args.sound, audio_dir, slide_count)
        missing = [
            i + 1
            for i, s in enumerate(sound_map)
            if not s["first"] and not s["second"]
        ]
        if missing:
            log.warning(
                "No sound for slide(s): %s",
                ", ".join(map(str, missing)),
            )

        generate_app(
            output_dir,
            slide_count=slide_count,
            title=title,
            sound_map=sound_map,
            enable_pwa=not args.no_pwa,
            enable_autoplay=args.autoplay,
        )

        if args.zip:
            zip_path = output_dir.parent / f"{output_dir.name}.zip"
            create_zip(output_dir, zip_path)
            log.info("Created ZIP: %s", zip_path)

        log.info("Done! Open: %s", output_dir / "index.html")
        log.info(
            "Parents can open index.html on phone/tablet/desktop — no Python required."
        )
        return 0

    except Exception as exc:
        log.exception("Build failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
