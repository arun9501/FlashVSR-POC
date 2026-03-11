"""
Post-process upscaled video to exact target resolution (e.g. 1080p).
Uses FFmpeg with configurable fit mode: pad, crop, or stretch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.utils.ffmpeg_tools import FitMode, normalize_to_resolution
from app.utils.video_probe import get_resolution, probe

from app.logger import get_logger

logger = get_logger(__name__)


def normalize_to_1080p(
    raw_output_path: Path,
    final_output_path: Path,
    target_width: int = 1920,
    target_height: int = 1080,
    fit_mode: FitMode = "pad",
) -> tuple[int, int]:
    """
    Normalize the raw model output to exact target resolution (default 1920x1080).

    - pad: letterbox/pillarbox to exact size (default; preserves aspect, no crop).
    - crop: center-crop to exact size.
    - stretch: force exact size (may distort).

    Returns (final_width, final_height) which will equal (target_width, target_height).
    """
    raw_output_path = Path(raw_output_path)
    final_output_path = Path(final_output_path)
    if not raw_output_path.is_file():
        raise FileNotFoundError(f"Raw output not found: {raw_output_path}")

    try:
        data = probe(raw_output_path)
        w, h = get_resolution(data)
        logger.info("Raw output resolution: %dx%d -> normalizing to %dx%d (%s)", w, h, target_width, target_height, fit_mode)
    except Exception as e:
        logger.warning("Could not probe raw output: %s; proceeding with normalization", e)

    normalize_to_resolution(
        raw_output_path,
        final_output_path,
        target_width=target_width,
        target_height=target_height,
        fit_mode=fit_mode,
        overwrite=True,
    )
    return target_width, target_height
