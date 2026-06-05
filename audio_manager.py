"""Narration: copy pre-recorded soundX_Y.mp3 files (TTS helpers kept for reference)."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from utils import ensure_dir, slide_filename

logger = logging.getLogger(__name__)

# Matches soundX_1.mp3 / soundX_2.mp3 (ignores duplicates like sound22_1(1).mp3)
SOUND_PATTERN = re.compile(r"^sound(\d+)_([12])\.mp3$", re.IGNORECASE)

# Default Edge TTS voice (clear, child-friendly)
DEFAULT_VOICE = "en-US-AnaNeural"
FALLBACK_VOICE = "en-US-JennyNeural"


@dataclass
class AudioResult:
    """Paths to per-slide narration files."""

    audio_paths: List[Path]
    method: str  # "external" | "edge-tts" | "gtts"


def copy_recorded_sounds(
    sound_dir: Path,
    audio_dir: Path,
    slide_count: int,
) -> List[Dict[str, Optional[str]]]:
    """
    Copy recorded narration into the output ``audio`` folder.

    Convention: ``soundX_Y.mp3`` where X is the 1-based slide number and
    Y is 1 (plays automatically when the slide opens) or 2 (plays when the
    Speak Out button is pressed).

    Returns a list of length ``slide_count``; each entry is a dict with web
    paths for the slide, e.g. ``{"first": "audio/sound1_1.mp3", "second": None}``.
    """
    sound_dir = Path(sound_dir)
    audio_dir = ensure_dir(audio_dir)

    sound_map: List[Dict[str, Optional[str]]] = [
        {"first": None, "second": None} for _ in range(slide_count)
    ]

    # Remove stale audio so the folder always matches the source
    for stale in list(audio_dir.glob("sound*.mp3")) + list(audio_dir.glob("slide*.mp3")):
        stale.unlink(missing_ok=True)

    if not sound_dir.is_dir():
        logger.warning("Sound folder not found: %s", sound_dir)
        return sound_map

    copied = 0
    for src in sorted(sound_dir.iterdir()):
        if not src.is_file():
            continue
        match = SOUND_PATTERN.match(src.name)
        if not match:
            continue  # skip duplicates / descriptive names / non-mp3 assets

        slide_no = int(match.group(1))
        which = match.group(2)
        index = slide_no - 1
        if index < 0 or index >= slide_count:
            logger.warning(
                "Sound '%s' targets slide %s which is out of range (1-%s)",
                src.name,
                slide_no,
                slide_count,
            )
            continue

        dst_name = f"sound{slide_no}_{which}.mp3"
        shutil.copy2(src, audio_dir / dst_name)
        key = "first" if which == "1" else "second"
        sound_map[index][key] = f"audio/{dst_name}"
        copied += 1

    with_audio = sum(1 for s in sound_map if s["first"] or s["second"])
    logger.info(
        "Copied %s recorded sound files (%s/%s slides have audio)",
        copied,
        with_audio,
        slide_count,
    )
    return sound_map


def _tts_safe_text(text: str, slide_index: int) -> str:
    """Ensure text is safe for TTS engines."""
    cleaned = text.strip()
    if not cleaned:
        return f"Slide {slide_index + 1}"
    # Edge TTS limit; very long strings can fail
    if len(cleaned) > 500:
        cleaned = cleaned[:500]
    return cleaned


async def _edge_tts_save(text: str, output: Path, voice: str, slide_index: int = 0) -> bool:
    try:
        import edge_tts
    except ImportError:
        return False

    content = _tts_safe_text(text, slide_index)
    try:
        communicate = edge_tts.Communicate(content, voice)
        await communicate.save(str(output))
        return output.is_file()
    except Exception as exc:
        logger.warning("edge-tts failed for slide %s: %s", slide_index + 1, exc)
        return False


def _gtts_save(text: str, output: Path, lang: str = "en") -> bool:
    try:
        from gtts import gTTS
    except ImportError:
        return False

    content = text.strip() or " "
    tts = gTTS(text=content, lang=lang)
    tts.save(str(output))
    return output.is_file()


def generate_narration_sync(
    texts: List[str],
    audio_dir: Path,
    voice: str = DEFAULT_VOICE,
    lang: str = "en",
) -> AudioResult:
    """Generate MP3 files for each slide (blocking wrapper)."""
    return asyncio.run(generate_narration(texts, audio_dir, voice=voice, lang=lang))


async def generate_narration(
    texts: List[str],
    audio_dir: Path,
    voice: str = DEFAULT_VOICE,
    lang: str = "en",
) -> AudioResult:
    """
    Create slideN.mp3 using edge-tts, falling back to gTTS.
    """
    audio_dir = ensure_dir(audio_dir)
    paths: List[Path] = []
    method = "edge-tts"

    for i, text in enumerate(texts):
        out = audio_dir / slide_filename(i, "mp3")
        ok = await _edge_tts_save(text, out, voice, slide_index=i)
        if not ok:
            logger.warning("edge-tts failed for slide %s; trying gTTS", i + 1)
            ok = _gtts_save(_tts_safe_text(text, i), out, lang=lang)
            method = "gtts"
        if not ok:
            raise RuntimeError(
                "TTS failed. Install edge-tts or gTTS: pip install edge-tts gTTS"
            )
        paths.append(out)
        logger.info("Generated narration: %s", out.name)

    return AudioResult(audio_paths=paths, method=method)


def copy_external_audio(
    source_dir: Path,
    audio_dir: Path,
    slide_count: int,
) -> AudioResult:
    """
    Copy slide1.mp3 … slideN.mp3 from external folder.
    Missing files are logged but do not stop the build.
    """
    source_dir = Path(source_dir)
    audio_dir = ensure_dir(audio_dir)
    paths: List[Path] = []

    for i in range(slide_count):
        name = slide_filename(i, "mp3")
        src = source_dir / name
        dst = audio_dir / name
        if src.is_file():
            shutil.copy2(src, dst)
            paths.append(dst)
            logger.info("Copied audio: %s", name)
        else:
            logger.warning("Missing external audio: %s", src)
            paths.append(dst)  # placeholder path; may be missing

    return AudioResult(audio_paths=paths, method="external")


def resolve_audio(
    texts: List[str],
    audio_dir: Path,
    external_audio_dir: Optional[Path] = None,
    use_tts: bool = True,
    voice: str = DEFAULT_VOICE,
    lang: str = "en",
) -> AudioResult:
    """
    Use external MP3 folder when provided and complete enough;
    otherwise auto-generate narration from slide text.
    """
    slide_count = len(texts)

    if external_audio_dir and Path(external_audio_dir).is_dir():
        result = copy_external_audio(external_audio_dir, audio_dir, slide_count)
        missing = [p for p in result.audio_paths if not p.is_file()]
        if not missing:
            logger.info("Using external narration from %s", external_audio_dir)
            return result
        if use_tts:
            logger.info(
                "External audio incomplete (%s missing); generating TTS for all slides",
                len(missing),
            )
        else:
            return result

    if not use_tts:
        raise ValueError(
            "No complete external audio folder and TTS disabled. "
            "Provide audio/ with slide1.mp3 … or enable --tts."
        )

    logger.info("Auto-generating narration with TTS")
    return generate_narration_sync(texts, audio_dir, voice=voice, lang=lang)
