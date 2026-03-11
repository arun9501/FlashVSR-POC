"""
Wrapper around the official FlashVSR inference scripts.

Integration strategy:
- The official scripts have hardcoded input paths (e.g. ./inputs/example4.mp4 for
  tiny_long_video, ./inputs/example0.mp4 for full/tiny) and write to ./results/.
- We copy the user's input to the expected input path, run the script with cwd
  set to examples/WanVSR, then locate the generated output in results/.
- Script and output naming are derived from model version and inference mode.
- We do not modify the official repo; we only copy input and run the script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

from config.settings import get_wanvsr_dir

from app.logger import get_logger

logger = get_logger(__name__)

ModelVersion = Literal["v1", "v1.1"]
InferenceMode = Literal["full", "tiny", "tiny_long_video"]

# Official scripts use a single input file per run. We map mode -> input basename they expect.
# tiny_long_video uses example4.mp4; full and tiny use example0.mp4 (first in list).
INPUT_BASENAME_BY_MODE: dict[InferenceMode, str] = {
    "tiny_long_video": "example4.mp4",
    "full": "example0.mp4",
    "tiny": "example0.mp4",
}
# Output filename pattern: FlashVSR_v1.1_Tiny_Long_{stem}_seed0.mp4 (seed is 0 in scripts)
OUTPUT_STEM_BY_MODE: dict[InferenceMode, str] = {
    "tiny_long_video": "example4",
    "full": "example0",
    "tiny": "example0",
}


def _script_name(version: ModelVersion, mode: InferenceMode) -> str:
    if version == "v1.1":
        return f"infer_flashvsr_v1.1_{mode}.py"
    return f"infer_flashvsr_{mode}.py"


# Official scripts use these tags in output filenames (e.g. FlashVSR_v1.1_Tiny_Long_example4_seed0.mp4)
_MODE_TAG: dict[InferenceMode, str] = {
    "full": "Full",
    "tiny": "Tiny",
    "tiny_long_video": "Tiny_Long",
}


def _output_basename(version: ModelVersion, mode: InferenceMode) -> str:
    stem = OUTPUT_STEM_BY_MODE[mode]
    tag = _MODE_TAG[mode]
    if version == "v1.1":
        return f"FlashVSR_v1.1_{tag}_{stem}_seed0.mp4"
    return f"FlashVSR_{tag}_{stem}_seed0.mp4"


def run_flashvsr(
    input_video: Path,
    output_dir: Path,
    model_version: ModelVersion = "v1.1",
    mode: InferenceMode = "tiny_long_video",
    python_bin: Optional[str] = None,
    wanvsr_dir: Optional[Path] = None,
) -> Path:
    """
    Run official FlashVSR inference: copy input to repo inputs/, run script, return path to raw output.

    - input_video: path to the input video file.
    - output_dir: directory where we will copy the raw output (from repo results/).
    - model_version: v1 or v1.1.
    - mode: full, tiny, or tiny_long_video.
    - python_bin: Python interpreter to use (e.g. venv or conda). If None, uses FLASHVSR_PYTHON from env or sys.executable.
    - wanvsr_dir: examples/WanVSR directory. If None, uses get_wanvsr_dir().

    Returns path to the raw upscaled video (copied into output_dir).
    Raises FileNotFoundError, ValueError, EnvCheckError, and subprocess.CalledProcessError.
    """
    wanvsr_dir = wanvsr_dir or get_wanvsr_dir()
    if not wanvsr_dir or not wanvsr_dir.is_dir():
        raise FileNotFoundError(
            "WanVSR directory not found. Set FLASHVSR_REPO_PATH and ensure examples/WanVSR exists."
        )

    input_video = Path(input_video).resolve()
    if not input_video.is_file():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs_dir = wanvsr_dir / "inputs"
    results_dir = wanvsr_dir / "results"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    input_basename = INPUT_BASENAME_BY_MODE[mode]
    dest_input = inputs_dir / input_basename
    logger.info("Copying input to %s", dest_input)
    shutil.copy2(input_video, dest_input)

    script = _script_name(model_version, mode)
    script_path = wanvsr_dir / script
    if not script_path.is_file():
        raise FileNotFoundError(f"Inference script not found: {script_path}")

    python_bin = python_bin or os.environ.get("FLASHVSR_PYTHON") or sys.executable
    cmd = [python_bin, str(script_path)]
    logger.info("Running FlashVSR: cwd=%s cmd=%s", wanvsr_dir, cmd)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(wanvsr_dir),
            capture_output=True,
            text=True,
            timeout=86400,
        )
    except subprocess.TimeoutExpired:
        logger.error("FlashVSR subprocess timed out")
        raise
    except Exception as e:
        logger.exception("FlashVSR subprocess failed")
        raise

    if result.stdout:
        logger.info("FlashVSR stdout: %s", result.stdout[-4000:])
    if result.returncode != 0:
        logger.error("FlashVSR stderr: %s", result.stderr)
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr,
        )

    out_basename = _output_basename(model_version, mode)
    raw_in_results = results_dir / out_basename
    if not raw_in_results.is_file():
        # Fallback: newest mp4 in results
        mp4s = list(results_dir.glob("*.mp4"))
        if not mp4s:
            raise FileNotFoundError(
                f"FlashVSR did not produce output in {results_dir}. stderr: {result.stderr}"
            )
        raw_in_results = max(mp4s, key=lambda p: p.stat().st_mtime)
        logger.warning("Using most recent result file: %s", raw_in_results)

    # Copy to user's output_dir so we have a stable path for postprocess
    raw_output_dest = output_dir / raw_in_results.name
    shutil.copy2(raw_in_results, raw_output_dest)
    logger.info("Raw FlashVSR output: %s", raw_output_dest)
    return raw_output_dest
