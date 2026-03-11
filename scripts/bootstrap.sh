#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# bootstrap.sh
# One-shot setup for FlashVSR app on EC2 GPU (e.g. with Deep Learning AMI).
# Runs: system deps → clone/install FlashVSR + Block-Sparse-Attention → download
# weights → create/update .env with FLASHVSR_REPO_PATH and FLASHVSR_PYTHON.
# Run from project root: bash scripts/bootstrap.sh
# Optional: export FLASHVSR_REPO_PATH=/custom/path before running.
# -----------------------------------------------------------------------------
set -euo pipefail

# Resolve project root (directory containing .env.example and scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f ".env.example" ]] || [[ ! -d "scripts" ]]; then
  echo "Error: Run from project root (directory containing .env.example and scripts/)."
  exit 1
fi

# Default repo path (absolute); override with FLASHVSR_REPO_PATH
export FLASHVSR_REPO_PATH="${FLASHVSR_REPO_PATH:-$PROJECT_ROOT/third_party/FlashVSR}"
REPO_PATH="$FLASHVSR_REPO_PATH"
PYTHON_PATH="${REPO_PATH}/.venv/bin/python"

echo "=============================================="
echo "FlashVSR app bootstrap"
echo "=============================================="
echo "Project root:    $PROJECT_ROOT"
echo "FlashVSR repo:   $REPO_PATH"
echo "=============================================="

echo ""
echo "[1/4] System dependencies (Ubuntu: python3.11, ffmpeg, git-lfs)..."
bash scripts/setup_ubuntu_ec2.sh

echo ""
echo "[2/4] Clone FlashVSR and install (venv + Block-Sparse-Attention)..."
bash scripts/install_flashvsr.sh

echo ""
echo "[3/4] Download model weights (v1.1)..."
bash scripts/download_weights.sh

echo ""
echo "[4/4] Configure .env ..."
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "  Created .env from .env.example"
fi
# Escape path for sed replacement (only \ and & are special in replacement)
safe_repo=$(printf '%s\n' "$REPO_PATH" | sed 's/[&\\]/\\&/g')
safe_python=$(printf '%s\n' "$PYTHON_PATH" | sed 's/[&\\]/\\&/g')
sed -i.bak "s|^FLASHVSR_REPO_PATH=.*|FLASHVSR_REPO_PATH=$safe_repo|" .env
sed -i.bak "s|^# FLASHVSR_PYTHON=.*|FLASHVSR_PYTHON=$safe_python|" .env
rm -f .env.bak
echo "  Set FLASHVSR_REPO_PATH=$REPO_PATH"
echo "  Set FLASHVSR_PYTHON=$PYTHON_PATH"

echo ""
echo "=============================================="
echo "Bootstrap complete."
echo "  Run: python -m app.cli --env-check-only --model-version v1.1"
echo "  Then: python -m app.cli --input /path/to/video.mp4 --output-dir /path/to/out"
echo "=============================================="
