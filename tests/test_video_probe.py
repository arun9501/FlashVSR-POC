"""Tests for video_probe module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.video_probe import (
    SUPPORTED_VIDEO_EXTENSIONS,
    get_resolution,
    get_video_stream,
    is_supported_video_file,
    probe,
)


def test_is_supported_video_file_nonexistent(tmp_path: Path) -> None:
    assert is_supported_video_file(tmp_path / "x.mp4") is False


def test_is_supported_video_file_extensions(tmp_path: Path) -> None:
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        f = tmp_path / f"f{ext}"
        f.touch()
        assert is_supported_video_file(f) is True
    (tmp_path / "f.txt").touch()
    assert is_supported_video_file(tmp_path / "f.txt") is False


def test_probe_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        probe(Path("/nonexistent/video.mp4"))


def test_get_video_stream_no_video() -> None:
    data = {"streams": [{"codec_type": "audio"}]}
    assert get_video_stream(data) is None


def test_get_video_stream_has_video() -> None:
    data = {"streams": [{"codec_type": "audio"}, {"codec_type": "video", "width": 1920, "height": 1080}]}
    stream = get_video_stream(data)
    assert stream is not None
    assert stream["width"] == 1920
    assert stream["height"] == 1080


def test_get_resolution_success() -> None:
    data = {"streams": [{"codec_type": "video", "width": 640, "height": 360}]}
    assert get_resolution(data) == (640, 360)


def test_get_resolution_no_video_stream() -> None:
    data = {"streams": []}
    with pytest.raises(ValueError, match="No video stream"):
        get_resolution(data)


def test_get_resolution_missing_dimensions() -> None:
    data = {"streams": [{"codec_type": "video"}]}
    with pytest.raises(ValueError, match="missing width or height"):
        get_resolution(data)


def test_probe_ffprobe_fails(tmp_path: Path) -> None:
    import subprocess
    fake_video = tmp_path / "fake.mp4"
    fake_video.touch()
    with patch("app.utils.video_probe.subprocess.run") as m:
        m.side_effect = subprocess.CalledProcessError(1, "ffprobe", stderr="Invalid data")
    with pytest.raises(ValueError):
        probe(fake_video)
