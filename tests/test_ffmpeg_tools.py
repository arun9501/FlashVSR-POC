"""Tests for ffmpeg_tools module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.ffmpeg_tools import FitMode, normalize_to_resolution


def test_normalize_invalid_dimensions(tmp_path: Path) -> None:
    inp = tmp_path / "in.mp4"
    inp.touch()
    out = tmp_path / "out.mp4"
    with pytest.raises(ValueError, match="must be positive"):
        normalize_to_resolution(inp, out, 0, 1080, fit_mode="pad")
    with pytest.raises(ValueError, match="must be positive"):
        normalize_to_resolution(inp, out, 1920, 0, fit_mode="pad")


def test_normalize_input_not_found(tmp_path: Path) -> None:
    out = tmp_path / "out.mp4"
    with pytest.raises(FileNotFoundError):
        normalize_to_resolution(tmp_path / "nonexistent.mp4", out, 1920, 1080)


def test_normalize_invalid_fit_mode(tmp_path: Path) -> None:
    inp = tmp_path / "in.mp4"
    inp.touch()
    out = tmp_path / "out.mp4"
    with pytest.raises(ValueError, match="Invalid fit_mode"):
        normalize_to_resolution(inp, out, 1920, 1080, fit_mode="invalid")  # type: ignore[arg-type]


def test_normalize_calls_ffmpeg_with_pad(tmp_path: Path) -> None:
    inp = tmp_path / "in.mp4"
    inp.touch()
    out = tmp_path / "out.mp4"
    with patch("app.utils.ffmpeg_tools.subprocess.run") as m:
        m.return_value.returncode = 0
        m.return_value.stderr = ""
        normalize_to_resolution(inp, out, 1920, 1080, fit_mode="pad")
    m.assert_called_once()
    call_args = m.call_args[0][0]
    # First arg is FFMPEG_BIN (typically "ffmpeg")
    assert "ffmpeg" in call_args[0].lower() or call_args[0] == "ffmpeg"
    assert "-vf" in call_args
    vf_idx = call_args.index("-vf")
    vf = call_args[vf_idx + 1]
    assert "pad=1920:1080" in vf
    assert "force_original_aspect_ratio=decrease" in vf


def test_normalize_crop_filter(tmp_path: Path) -> None:
    inp = tmp_path / "in.mp4"
    inp.touch()
    out = tmp_path / "out.mp4"
    with patch("app.utils.ffmpeg_tools.subprocess.run") as m:
        m.return_value.returncode = 0
        m.return_value.stderr = ""
        normalize_to_resolution(inp, out, 1920, 1080, fit_mode="crop")
    vf = m.call_args[0][0][m.call_args[0][0].index("-vf") + 1]
    assert "crop=1920:1080" in vf
    assert "force_original_aspect_ratio=increase" in vf


def test_normalize_stretch_filter(tmp_path: Path) -> None:
    inp = tmp_path / "in.mp4"
    inp.touch()
    out = tmp_path / "out.mp4"
    with patch("app.utils.ffmpeg_tools.subprocess.run") as m:
        m.return_value.returncode = 0
        m.return_value.stderr = ""
        normalize_to_resolution(inp, out, 1920, 1080, fit_mode="stretch")
    vf = m.call_args[0][0][m.call_args[0][0].index("-vf") + 1]
    assert vf == "scale=1920:1080"
