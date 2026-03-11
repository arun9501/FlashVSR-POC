"""
Application settings loaded from environment and .env.

Uses pathlib for paths. All optional paths default to None and are resolved
at runtime (e.g. WORK_DIR, TEMP_DIR) or from FLASHVSR_REPO_PATH.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Try to load .env if python-dotenv is available (optional for minimal deps in CI)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


def _path_env(key: str, default: Optional[str] = None) -> Optional[Path]:
    v = _env(key, default)
    return Path(v).resolve() if v else None


# -----------------------------------------------------------------------------
# FlashVSR
# -----------------------------------------------------------------------------
FLASHVSR_REPO_PATH: Optional[Path] = _path_env("FLASHVSR_REPO_PATH")
"""Root of the official FlashVSR repo (e.g. /opt/flashvsr/FlashVSR or third_party/FlashVSR)."""

FLASHVSR_MODEL_ROOT: Optional[Path] = _path_env("FLASHVSR_MODEL_ROOT")
"""
Root directory containing model weight folders.
If set, overrides repo-relative paths. Expected structure:
  {FLASHVSR_MODEL_ROOT}/FlashVSR/   (v1)
  {FLASHVSR_MODEL_ROOT}/FlashVSR-v1.1/   (v1.1)
If unset, weights are expected at {FLASHVSR_REPO_PATH}/examples/WanVSR/FlashVSR(-v1.1).
"""

FLASHVSR_DEFAULT_MODEL_VERSION: str = _env("FLASHVSR_DEFAULT_MODEL_VERSION", "v1.1") or "v1.1"
FLASHVSR_DEFAULT_MODE: str = _env("FLASHVSR_DEFAULT_MODE", "tiny_long_video") or "tiny_long_video"

# -----------------------------------------------------------------------------
# FFmpeg
# -----------------------------------------------------------------------------
FFMPEG_BIN: str = _env("FFMPEG_BIN", "ffmpeg") or "ffmpeg"
FFPROBE_BIN: str = _env("FFPROBE_BIN", "ffprobe") or "ffprobe"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL: str = _env("LOG_LEVEL", "INFO") or "INFO"

# -----------------------------------------------------------------------------
# Directories (optional)
# -----------------------------------------------------------------------------
WORK_DIR: Optional[Path] = _path_env("WORK_DIR")
TEMP_DIR: Optional[Path] = _path_env("TEMP_DIR")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def get_wanvsr_dir() -> Optional[Path]:
    """Return examples/WanVSR inside the FlashVSR repo, or None if repo path not set."""
    if not FLASHVSR_REPO_PATH:
        return None
    return FLASHVSR_REPO_PATH / "examples" / "WanVSR"


def get_model_dir(version: str) -> Optional[Path]:
    """
    Return path to model weights for the given version ('v1' or 'v1.1').
    Prefers FLASHVSR_MODEL_ROOT if set; otherwise repo-relative.
    """
    folder = "FlashVSR-v1.1" if version == "v1.1" else "FlashVSR"
    if FLASHVSR_MODEL_ROOT:
        return FLASHVSR_MODEL_ROOT / folder
    wan = get_wanvsr_dir()
    return (wan / folder) if wan else None
