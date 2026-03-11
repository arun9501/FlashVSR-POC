"""
End-to-end pipeline: validate -> probe -> FlashVSR -> (optional) normalize to target resolution.
When normalize is skipped, output is raw FlashVSR upscale (same aspect ratio as input).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from config.settings import get_wanvsr_dir

from app.logger import get_logger
from app.services.flashvsr_runner import run_flashvsr
from app.services.postprocess_service import normalize_to_1080p
from app.utils.env_check import validate_env_for_inference
from app.utils.ffmpeg_tools import FitMode
from app.utils.video_probe import get_video_metadata, is_supported_video_file

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Structured result of the upscale pipeline."""

    success: bool
    input_path: str
    raw_output_path: Optional[str] = None
    final_output_path: Optional[str] = None
    input_width: Optional[int] = None
    input_height: Optional[int] = None
    raw_output_width: Optional[int] = None
    raw_output_height: Optional[int] = None
    final_output_width: Optional[int] = None
    final_output_height: Optional[int] = None
    error: Optional[str] = None
    stderr: Optional[str] = None
    stdout: Optional[str] = None
    runtime_seconds: Optional[float] = None
    metadata: dict = field(default_factory=dict)


def run_pipeline(
    input_video: Path,
    output_dir: Path,
    target_width: int = 1920,
    target_height: int = 1080,
    model_version: Literal["v1", "v1.1"] = "v1.1",
    mode: Literal["full", "tiny", "tiny_long_video"] = "tiny_long_video",
    fit_mode: FitMode = "pad",
    keep_intermediate: bool = True,
    python_bin: Optional[str] = None,
    no_normalize: bool = False,
) -> PipelineResult:
    """
    Run the pipeline: validate env -> probe input -> FlashVSR -> (optional) normalize.

    - no_normalize: if True, skip FFmpeg normalization; final output is the raw FlashVSR
      upscale (same aspect ratio as input, 4x super-resolution). Use this to preserve
      aspect ratio only.
    - keep_intermediate: if True, raw model output is kept when normalizing; ignored when no_normalize.
    """
    import time
    start = time.perf_counter()
    result = PipelineResult(
        success=False,
        input_path=str(Path(input_video).resolve()),
    )
    try:
        input_path = Path(input_video).resolve()
        output_dir = Path(output_dir).resolve()

        if not input_path.is_file():
            result.error = f"Input file not found: {input_path}"
            return result
        if not is_supported_video_file(input_path):
            from app.utils.video_probe import SUPPORTED_VIDEO_EXTENSIONS
            result.error = (
                f"Unsupported file type or path: {input_path}. "
                f"Supported extensions: {SUPPORTED_VIDEO_EXTENSIONS}"
            )
            return result
        if not no_normalize and (target_width <= 0 or target_height <= 0):
            result.error = "Invalid target resolution (use --no-normalize to skip normalization)"
            return result

        meta = get_video_metadata(input_path)
        result.input_width = meta["width"]
        result.input_height = meta["height"]
        result.metadata["input_fps"] = meta["fps"]
        result.metadata["input_duration_sec"] = meta["duration_sec"]
        logger.info("Input: %dx%d", result.input_width, result.input_height)

        validate_env_for_inference(model_version, require_gpu=True)

        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.stem

        # Stage 1: FlashVSR (upscale, same aspect ratio as input)
        logger.info("Stage 1: FlashVSR inference (version=%s, mode=%s)", model_version, mode)
        raw_output = run_flashvsr(
            input_video=input_path,
            output_dir=output_dir,
            model_version=model_version,
            mode=mode,
            python_bin=python_bin,
            wanvsr_dir=get_wanvsr_dir(),
        )
        result.raw_output_path = str(raw_output)
        try:
            raw_meta = get_video_metadata(raw_output)
            result.raw_output_width = raw_meta["width"]
            result.raw_output_height = raw_meta["height"]
        except Exception as e:
            logger.warning("Could not probe raw output: %s", e)

        if no_normalize:
            # Final output = upscaled video with same aspect ratio; save as {stem}_upscaled.mp4
            final_path = output_dir / f"{stem}_upscaled.mp4"
            if raw_output.resolve() != final_path.resolve():
                shutil.copy2(raw_output, final_path)
                if not keep_intermediate:
                    try:
                        raw_output.unlink()
                    except OSError as e:
                        logger.warning("Could not remove raw file: %s", e)
            else:
                final_path = raw_output
            result.final_output_path = str(final_path)
            result.final_output_width = result.raw_output_width
            result.final_output_height = result.raw_output_height
            logger.info("Output (same aspect ratio): %s (%dx%d)", final_path, result.final_output_width or 0, result.final_output_height or 0)
        else:
            # Stage 2: Normalize to target resolution
            final_path = output_dir / f"{stem}_1080p.mp4"
            logger.info("Stage 2: Normalize to %dx%d (fit_mode=%s)", target_width, target_height, fit_mode)
            normalize_to_1080p(
                raw_output_path=raw_output,
                final_output_path=final_path,
                target_width=target_width,
                target_height=target_height,
                fit_mode=fit_mode,
            )
            result.final_output_path = str(final_path)
            result.final_output_width = target_width
            result.final_output_height = target_height

            if not keep_intermediate and raw_output != final_path:
                try:
                    raw_output.unlink()
                    logger.info("Removed intermediate file: %s", raw_output)
                except OSError as e:
                    logger.warning("Could not remove intermediate: %s", e)

        result.success = True
    except Exception as e:
        result.error = str(e)
        if hasattr(e, "stderr"):
            result.stderr = getattr(e, "stderr")
        if hasattr(e, "stdout"):
            result.stdout = getattr(e, "stdout")
        logger.exception("Pipeline failed: %s", e)
    finally:
        result.runtime_seconds = time.perf_counter() - start
    return result
