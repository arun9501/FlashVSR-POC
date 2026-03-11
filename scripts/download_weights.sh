#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# download_weights.sh
# Download FlashVSR / FlashVSR-v1.1 weights from Hugging Face into WanVSR dir.
# Requires git-lfs. Run from project root. Set FLASHVSR_REPO_PATH or pass path.
# -----------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="${FLASHVSR_REPO_PATH:-$(pwd)/third_party/FlashVSR}"
WANVSR="$REPO_DIR/examples/WanVSR"
VERSION="${1:-v1.1}"

if [[ ! -d "$WANVSR" ]]; then
  echo "WanVSR not found at $WANVSR. Run install_flashvsr.sh first."
  exit 1
fi

git lfs install || true
cd "$WANVSR"

if [[ "$VERSION" == "v1.1" ]]; then
  DEST="FlashVSR-v1.1"
  HF_URL="https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1"
else
  DEST="FlashVSR"
  HF_URL="https://huggingface.co/JunhaoZhuang/FlashVSR"
fi

if [[ -d "$DEST" && -f "$DEST/diffusion_pytorch_model_streaming_dmd.safetensors" ]]; then
  echo "Weights already present at $WANVSR/$DEST"
  exit 0
fi

echo "Cloning weights ($VERSION) from Hugging Face into $WANVSR/$DEST ..."
git lfs clone "$HF_URL" "$DEST"
echo "Done. Weights at: $WANVSR/$DEST"
