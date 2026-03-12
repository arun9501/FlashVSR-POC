#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# install_flashvsr.sh
# Clone official FlashVSR repo, create venv, install deps and Block-Sparse-Attention.
# Run from project root. Set FLASHVSR_REPO_PATH or use default third_party/FlashVSR.
# -----------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${FLASHVSR_REPO_PATH:-$(pwd)/third_party/FlashVSR}"
BLOCK_SPARSE_DIR="${BLOCK_SPARSE_DIR:-$(pwd)/third_party/Block-Sparse-Attention}"

echo "FlashVSR repo will be at: $REPO_DIR"
echo "Block-Sparse-Attention will be at: $BLOCK_SPARSE_DIR"

mkdir -p "$(dirname "$REPO_DIR")"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "[1/5] Cloning FlashVSR..."
  git clone https://github.com/OpenImagingLab/FlashVSR "$REPO_DIR"
else
  echo "[1/5] FlashVSR already cloned at $REPO_DIR"
fi

cd "$REPO_DIR"
# Optional: pin to a specific commit for reproducibility
# git checkout <commit>

echo "[2/5] Creating Python 3 venv in FlashVSR repo..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# Ensure setuptools (provides pkg_resources) is available for editable installs
pip install --upgrade setuptools

echo "[3/5] Installing FlashVSR requirements (PyTorch/CUDA - may take a while)..."
# Official repo uses torch+cu124 etc. from requirements.txt; adjust if your CUDA differs.
pip install -e .
pip install -r requirements.txt

echo "[4/5] Installing Block-Sparse-Attention (required; build can be memory-intensive)..."
mkdir -p "$(dirname "$BLOCK_SPARSE_DIR")"
if [[ ! -d "$BLOCK_SPARSE_DIR/.git" ]]; then
  git clone https://github.com/mit-han-lab/Block-Sparse-Attention "$BLOCK_SPARSE_DIR"
fi
cd "$BLOCK_SPARSE_DIR"
pip install packaging ninja
python setup.py install
# If you hit OOM during build, try: MAX_JOBS=1 python setup.py install
cd "$REPO_DIR"

echo "[5/5] Verifying FlashVSR imports..."
python -c "
from diffsynth import ModelManager
print('diffsynth OK')
" || { echo "Import check failed. Ensure Block-Sparse-Attention and FlashVSR deps are installed."; exit 1; }

echo ""
echo "Install done. To use this env when running the app:"
echo "  export FLASHVSR_REPO_PATH=$REPO_DIR"
echo "  export FLASHVSR_PYTHON=$REPO_DIR/.venv/bin/python"
echo "  python -m app.cli --input /path/to/video.mp4 --output-dir /path/to/out --python \$FLASHVSR_PYTHON"
