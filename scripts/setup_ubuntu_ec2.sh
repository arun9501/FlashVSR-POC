#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# setup_ubuntu_ec2.sh
# Install system dependencies on Ubuntu EC2 for FlashVSR app: python, ffmpeg, git-lfs.
# Run with: bash scripts/setup_ubuntu_ec2.sh
# -----------------------------------------------------------------------------
set -euo pipefail

echo "[1/5] Updating apt..."
sudo apt-get update -qq

echo "[2/5] Installing Python 3, venv, and build tools..."
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  git \
  wget \
  curl

echo "[3/5] Installing FFmpeg..."
sudo apt-get install -y ffmpeg
command -v ffmpeg >/dev/null 2>&1 || { echo "FFmpeg install failed"; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ffprobe not found"; exit 1; }

echo "[4/5] Installing Git LFS (for downloading model weights)..."
sudo apt-get install -y git-lfs
git lfs version || true

echo "[5/5] Checking for NVIDIA driver (optional but required for FlashVSR inference)..."
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || true
else
  echo "  nvidia-smi not found. Install NVIDIA driver and CUDA for GPU inference."
  echo "  See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
fi

echo ""
echo "Next steps:"
echo "  1. Clone FlashVSR and set up env: bash scripts/install_flashvsr.sh"
echo "  2. Download weights: bash scripts/download_weights.sh"
echo "  3. Set FLASHVSR_REPO_PATH in .env to the FlashVSR repo root"
echo "  4. Run demo: bash scripts/run_demo.sh"
