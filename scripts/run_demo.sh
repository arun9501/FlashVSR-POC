#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# run_demo.sh
# Run a sample upscale (replace INPUT and OUTPUT with real paths).
# Usage: FLASHVSR_REPO_PATH=/path/to/FlashVSR bash scripts/run_demo.sh
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

INPUT="${INPUT_VIDEO:-$PROJECT_ROOT/sample_input.mp4}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"

if [[ ! -f "$INPUT" ]]; then
  echo "Input video not found: $INPUT"
  echo "Set INPUT_VIDEO to your video path, or place a file at $INPUT"
  exit 1
fi

export FLASHVSR_REPO_PATH="${FLASHVSR_REPO_PATH:-$PROJECT_ROOT/third_party/FlashVSR}"
EXTRA_ARGS=()
if [[ -n "${FLASHVSR_PYTHON:-}" ]]; then
  EXTRA_ARGS+=(--python "$FLASHVSR_PYTHON")
fi

echo "Input: $INPUT"
echo "Output dir: $OUTPUT_DIR"
echo "FlashVSR repo: $FLASHVSR_REPO_PATH"
python -m app.cli \
  --input "$INPUT" \
  --output-dir "$OUTPUT_DIR" \
  --target-width 1920 \
  --target-height 1080 \
  --model-version v1.1 \
  --mode tiny_long_video \
  --fit-mode pad \
  --keep-intermediate \
  "${EXTRA_ARGS[@]}"

echo "Done. Check $OUTPUT_DIR for output."
