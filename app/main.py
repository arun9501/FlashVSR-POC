"""
Application entry point. Runs the upscale pipeline with config from CLI or API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.logger import setup_logging
from app.services.pipeline_service import PipelineResult, run_pipeline


def run_upscale(
    input_path: Path,
    output_dir: Path,
    target_width: int = 1920,
    target_height: int = 1080,
    model_version: str = "v1.1",
    mode: str = "tiny_long_video",
    fit_mode: str = "pad",
    keep_intermediate: bool = True,
    python_bin: Optional[str] = None,
    log_dir: Optional[Path] = None,
    no_normalize: bool = False,
) -> PipelineResult:
    """
    Run the upscale pipeline. Optionally pass log_dir to enable file logging.
    Set no_normalize=True to output only the FlashVSR upscale (same aspect ratio as input).
    """
    if log_dir:
        setup_logging(log_dir=Path(log_dir))
    return run_pipeline(
        input_video=Path(input_path),
        output_dir=Path(output_dir),
        target_width=target_width,
        target_height=target_height,
        model_version=model_version,
        mode=mode,
        fit_mode=fit_mode,
        keep_intermediate=keep_intermediate,
        python_bin=python_bin,
        no_normalize=no_normalize,
    )
