"""
Probe video metadata using ffprobe (JSON output).
Returns width, height, fps, duration, codec, etc.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import FFPROBE_BIN

from app.logger import get_logger

logger = get_logger(__name__)

# Supported input extensions for video (align with FlashVSR scripts)
SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")


def probe(path: Path) -> Dict[str, Any]:
    """
    Run ffprobe on the given file and return parsed JSON (streams + format).
    Raises FileNotFoundError if file does not exist, ValueError for invalid video.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")

    cmd = [
        FFPROBE_BIN,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"ffprobe failed: {e.stderr or e.stdout or e}") from e
    except FileNotFoundError:
        raise ValueError(f"{FFPROBE_BIN} not found in PATH") from None

    data = json.loads(out.stdout)
    return data


def get_video_stream(probe_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the first video stream from ffprobe JSON, or None."""
    streams = probe_data.get("streams") or []
    for s in streams:
        if s.get("codec_type") == "video":
            return s
    return None


def get_resolution(probe_data: Dict[str, Any]) -> tuple[int, int]:
    """
    Return (width, height) from the first video stream.
    Raises ValueError if no video stream or missing width/height.
    """
    stream = get_video_stream(probe_data)
    if not stream:
        raise ValueError("No video stream in file")
    w = stream.get("width")
    h = stream.get("height")
    if w is None or h is None:
        raise ValueError("Video stream missing width or height")
    return int(w), int(h)


def get_fps(probe_data: Dict[str, Any]) -> Optional[float]:
    """Return frames per second from the first video stream if available."""
    stream = get_video_stream(probe_data)
    if not stream:
        return None
    r = stream.get("r_frame_rate")
    if not r or "/" not in str(r):
        return None
    num, den = r.split("/", 1)
    try:
        n, d = float(num), float(den)
        return n / d if d else None
    except ValueError:
        return None


def get_duration_seconds(probe_data: Dict[str, Any]) -> Optional[float]:
    """Return duration in seconds from format section."""
    fmt = probe_data.get("format") or {}
    d = fmt.get("duration")
    if d is None:
        return None
    try:
        return float(d)
    except (TypeError, ValueError):
        return None


def get_video_metadata(path: Path) -> Dict[str, Any]:
    """
    Convenience: probe file and return a small dict with width, height, fps, duration_sec.
    """
    data = probe(path)
    width, height = get_resolution(data)
    return {
        "width": width,
        "height": height,
        "fps": get_fps(data),
        "duration_sec": get_duration_seconds(data),
        "path": str(path),
    }


def is_supported_video_file(path: Path) -> bool:
    """Return True if path has a supported video extension and exists."""
    p = Path(path)
    return p.is_file() and p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
