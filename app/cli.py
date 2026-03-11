"""
CLI for flashvsr_app: input video -> FlashVSR upscale (optional normalize to target resolution).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.logger import setup_logging
from app.utils.env_check import run_all_checks
from app.services.pipeline_service import run_pipeline

# Default log dir relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Upscale video with FlashVSR. By default preserves input aspect ratio; optionally normalize to a target resolution.",
    )
    p.add_argument("--input", "-i", type=Path, required=True, help="Input video file path")
    p.add_argument("--output-dir", "-o", type=Path, required=True, help="Output directory")
    p.add_argument(
        "--no-normalize",
        action="store_true",
        help="Do not normalize resolution; output is raw FlashVSR upscale (same aspect ratio as input)",
    )
    p.add_argument("--target-width", type=int, default=1920, help="Target width when normalizing (default: 1920)")
    p.add_argument("--target-height", type=int, default=1080, help="Target height when normalizing (default: 1080)")
    p.add_argument(
        "--model-version",
        choices=["v1", "v1.1"],
        default="v1.1",
        help="FlashVSR model version (default: v1.1)",
    )
    p.add_argument(
        "--mode",
        choices=["full", "tiny", "tiny_long_video"],
        default="tiny_long_video",
        help="Inference mode (default: tiny_long_video)",
    )
    p.add_argument(
        "--fit-mode",
        choices=["pad", "crop", "stretch"],
        default="pad",
        help="How to fit to target resolution: pad=letterbox, crop=center crop, stretch (default: pad)",
    )
    p.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep raw FlashVSR output in addition to final normalized file",
    )
    p.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Log directory for file logging",
    )
    p.add_argument(
        "--python",
        type=str,
        default=None,
        help="Python interpreter for FlashVSR (e.g. venv/bin/python)",
    )
    p.add_argument(
        "--env-check-only",
        action="store_true",
        help="Only run environment checks and exit",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print final result as JSON to stdout",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    setup_logging(log_dir=args.log_dir)
    from app.logger import get_logger
    logger = get_logger(__name__)

    if args.env_check_only:
        checks = run_all_checks(
            require_gpu=True,
            require_weights_version=args.model_version,
        )
        for name, passed, msg in checks:
            status = "OK" if passed else "FAIL"
            print(f"  [{status}] {name}: {msg}")
        failed = [n for n, p, _ in checks if not p]
        return 0 if not failed else 1

    logger.info(
        "Config: model=%s mode=%s normalize=%s %s",
        args.model_version,
        args.mode,
        "no" if args.no_normalize else "yes",
        f"target={args.target_width}x{args.target_height} fit={args.fit_mode}" if not args.no_normalize else "(same aspect ratio)",
    )
    try:
        from app.utils.video_probe import get_video_metadata
        meta = get_video_metadata(args.input)
        logger.info("Input resolution: %dx%d", meta["width"], meta["height"])
    except Exception as e:
        logger.warning("Could not probe input: %s", e)

    result = run_pipeline(
        input_video=args.input,
        output_dir=args.output_dir,
        target_width=args.target_width,
        target_height=args.target_height,
        model_version=args.model_version,
        mode=args.mode,
        fit_mode=args.fit_mode,
        keep_intermediate=args.keep_intermediate,
        python_bin=args.python,
        no_normalize=args.no_normalize,
    )

    if result.success:
        logger.info("Final output: %s", result.final_output_path)
        if args.json:
            out = {
                "success": True,
                "input_path": result.input_path,
                "raw_output_path": result.raw_output_path,
                "final_output_path": result.final_output_path,
                "input_resolution": [result.input_width, result.input_height],
                "raw_output_resolution": [result.raw_output_width, result.raw_output_height],
                "final_output_resolution": [result.final_output_width, result.final_output_height],
                "runtime_seconds": result.runtime_seconds,
            }
            print(json.dumps(out, indent=2))
        return 0
    else:
        logger.error("Pipeline failed: %s", result.error)
        if args.json:
            print(json.dumps({
                "success": False,
                "error": result.error,
                "stderr": result.stderr,
                "stdout": result.stdout,
                "runtime_seconds": result.runtime_seconds,
            }, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
