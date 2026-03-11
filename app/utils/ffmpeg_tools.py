"""
FFmpeg helpers: normalize video to exact target resolution with pad/crop/stretch.
Preserves aspect ratio for pad and crop; stretch forces exact dimensions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from config.settings import FFMPEG_BIN

from app.logger import get_logger

logger = get_logger(__name__)

FitMode = Literal["pad", "crop", "stretch"]


def normalize_to_resolution(
    input_path: Path,
    output_path: Path,
    target_width: int,
    target_height: int,
    fit_mode: FitMode = "pad",
    overwrite: bool = True,
) -> None:
    """
    Produce a video with exactly target_width x target_height using FFmpeg.

    - pad (default): Scale to fit inside target size preserving aspect ratio,
      then add black letterboxing/pillarboxing so the result is exactly
      target_width x target_height. No cropping; safe for all aspect ratios.

    - crop: Scale to cover the full target size preserving aspect ratio,
      then center-crop to exactly target_width x target_height. Some content
      may be cut off.

    - stretch: Scale (and optionally pad) to force exact dimensions; may
      distort aspect ratio.

    Raises ValueError on invalid dimensions or fit_mode.
    Raises subprocess.CalledProcessError if ffmpeg fails.
    """
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target_width and target_height must be positive")
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Build filter. We use scale + pad/crop to get exact size.
    # scale: fit within or cover (width, height) with aspect preserved
    # then pad or crop to exact (target_width, target_height)
    if fit_mode == "stretch":
        # Single scale to exact size
        vf = f"scale={target_width}:{target_height}"
    elif fit_mode == "pad":
        # Scale to fit inside [target_w, target_h], then pad to exact size
        # scale: force max size while keeping aspect; then pad to target
        vf = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black"
        )
    elif fit_mode == "crop":
        # Scale so that the image covers the target, then center crop
        vf = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}"
        )
    else:
        raise ValueError(f"Invalid fit_mode: {fit_mode}. Use 'pad', 'crop', or 'stretch'.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN,
        "-y" if overwrite else "-n",
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    logger.info("Running FFmpeg: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg stderr: %s", e.stderr)
        raise
    if result.stderr:
        logger.debug("FFmpeg stderr: %s", result.stderr)
