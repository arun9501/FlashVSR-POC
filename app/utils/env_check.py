"""
Environment validation: GPU, ffmpeg/ffprobe, git-lfs, FlashVSR repo, model weights.
Fails gracefully with clear messages when nvidia-smi or other deps are missing.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from config.settings import (
    FFMPEG_BIN,
    FFPROBE_BIN,
    FLASHVSR_REPO_PATH,
    get_model_dir,
    get_wanvsr_dir,
)


class EnvCheckError(Exception):
    """Raised when an environment check fails."""

    pass


def check_nvidia_gpu() -> Tuple[bool, str]:
    """
    Check if NVIDIA GPU is available via nvidia-smi.
    Returns (success, message). If nvidia-smi is missing, returns (False, message).
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return False, f"nvidia-smi failed: {out.stderr or out.stdout or 'unknown'}"
        lines = (out.stdout or "").strip().splitlines()
        if not lines:
            return False, "nvidia-smi reported no GPUs"
        return True, (lines[0].strip() or "NVIDIA GPU detected")
    except FileNotFoundError:
        return False, "nvidia-smi not found; NVIDIA driver or GPU may be missing"
    except subprocess.TimeoutExpired:
        return False, "nvidia-smi timed out"
    except Exception as e:
        return False, str(e)


def check_ffmpeg() -> Tuple[bool, str]:
    """Check that ffmpeg and ffprobe are available."""
    ffmpeg = shutil.which(FFMPEG_BIN)
    ffprobe = shutil.which(FFPROBE_BIN)
    if not ffmpeg:
        return False, f"{FFMPEG_BIN} not found in PATH"
    if not ffprobe:
        return False, f"{FFPROBE_BIN} not found in PATH"
    return True, f"{FFMPEG_BIN}={ffmpeg}, {FFPROBE_BIN}={ffprobe}"


def check_git_lfs() -> Tuple[bool, str]:
    """Check that git-lfs is installed (needed for downloading weights)."""
    which = shutil.which("git-lfs")
    if not which:
        return False, "git-lfs not found in PATH (required for weight download)"
    try:
        subprocess.run(
            ["git-lfs", "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return True, f"git-lfs found: {which}"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False, "git-lfs not working or not found"


def check_flashvsr_repo() -> Tuple[bool, str]:
    """Check that FlashVSR repo path exists and contains examples/WanVSR."""
    if not FLASHVSR_REPO_PATH:
        return False, "FLASHVSR_REPO_PATH is not set"
    if not FLASHVSR_REPO_PATH.is_dir():
        return False, f"FLASHVSR_REPO_PATH is not a directory: {FLASHVSR_REPO_PATH}"
    wan = get_wanvsr_dir()
    if not wan or not wan.is_dir():
        return False, f"WanVSR directory not found: {wan or 'N/A'}"
    return True, str(wan)


def check_model_weights(version: str) -> Tuple[bool, str]:
    """
    Check that required checkpoint files exist for the given model version (v1 or v1.1).
    Official repo expects: LQ_proj_in.ckpt, TCDecoder.ckpt, diffusion_pytorch_model_streaming_dmd.safetensors,
    and for full pipeline Wan2.1_VAE.pth.
    """
    model_dir = get_model_dir(version)
    if not model_dir:
        return False, f"Model root not resolved for version={version}"
    if not model_dir.is_dir():
        return False, f"Model directory does not exist: {model_dir}"

    required = [
        "LQ_proj_in.ckpt",
        "TCDecoder.ckpt",
        "diffusion_pytorch_model_streaming_dmd.safetensors",
    ]
    missing = [f for f in required if not (model_dir / f).is_file()]
    if missing:
        return False, f"Missing weights in {model_dir}: {missing}"
    return True, str(model_dir)


def run_all_checks(
    require_gpu: bool = True,
    require_git_lfs: bool = False,
    require_weights_version: Optional[str] = None,
) -> List[Tuple[str, bool, str]]:
    """
    Run standard environment checks. Returns list of (check_name, passed, message).
    require_weights_version: if set (e.g. 'v1.1'), validates that model weights exist.
    """
    results: List[Tuple[str, bool, str]] = []

    ok, msg = check_ffmpeg()
    results.append(("ffmpeg", ok, msg))

    ok, msg = check_nvidia_gpu()
    results.append(("nvidia_gpu", ok, msg))
    if require_gpu and not ok:
        # Do not continue with FlashVSR repo/weights if GPU is required and missing
        results.append(("flashvsr_repo", False, "Skipped (GPU missing)"))
        if require_weights_version:
            results.append(("model_weights", False, "Skipped (GPU missing)"))
        return results

    ok, msg = check_flashvsr_repo()
    results.append(("flashvsr_repo", ok, msg))

    if require_weights_version:
        ok, msg = check_model_weights(require_weights_version)
        results.append(("model_weights", ok, msg))

    if require_git_lfs:
        ok, msg = check_git_lfs()
        results.append(("git_lfs", ok, msg))

    return results


def validate_env_for_inference(
    model_version: str,
    require_gpu: bool = True,
) -> None:
    """
    Validate environment for running inference. Raises EnvCheckError on first failure.
    """
    checks = run_all_checks(
        require_gpu=require_gpu,
        require_weights_version=model_version,
    )
    for name, passed, msg in checks:
        if not passed:
            raise EnvCheckError(f"[{name}] {msg}")
