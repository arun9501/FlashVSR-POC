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
# Pin setuptools to a version that still provides pkg_resources
pip install "setuptools<82" wheel

echo "[3/5] Installing FlashVSR requirements (PyTorch/CUDA - may take a while)..."
# CUDA 12.1 wheels are forward-compatible with CUDA 12.2.
# Change to cu124 for CUDA >=12.4, cu118 for CUDA 11.8, etc.
TORCH_INDEX="https://download.pytorch.org/whl/cu121"

# Reset requirements.txt to upstream state before rewriting (safe for re-runs).
git checkout -- requirements.txt

# Rewrite the exact upstream cu124 pins to the latest available cu121 versions.
# torch 2.5.1, torchvision 0.20.1, torchaudio 2.5.1 are the latest cu121 builds.
sed -i 's/torch==2\.6\.0+cu124/torch==2.5.1+cu121/' requirements.txt
sed -i 's/torchvision==0\.21\.0+cu124/torchvision==0.20.1+cu121/' requirements.txt
sed -i 's/torchaudio==2\.6\.0+cu124/torchaudio==2.5.1+cu121/' requirements.txt
# Catch any other +cu124 references
sed -i 's/+cu124/+cu121/g' requirements.txt

pip install -r requirements.txt --extra-index-url "$TORCH_INDEX"
pip install --no-build-isolation -e .

echo "[4/5] Installing Block-Sparse-Attention (required; build can be memory-intensive)..."
mkdir -p "$(dirname "$BLOCK_SPARSE_DIR")"
if [[ ! -d "$BLOCK_SPARSE_DIR/.git" ]]; then
  git clone https://github.com/mit-han-lab/Block-Sparse-Attention "$BLOCK_SPARSE_DIR"
fi
cd "$BLOCK_SPARSE_DIR"
pip install packaging ninja

# Limit CUDA architectures to avoid unsupported 'compute_120' on older toolkits.
# Adjust this list if you know your exact GPU arch.
export TORCH_CUDA_ARCH_LIST="8.0;9.0"
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
