# FlashVSR App

Production-friendly Python application around the **official** [FlashVSR](https://github.com/OpenImagingLab/FlashVSR) repository. It accepts an input video and runs FlashVSR inference. By default you can **preserve the input aspect ratio** (upscale only, same aspect ratio) or optionally normalize to a target resolution (e.g. 1080p) with pad/crop/stretch.

## Project overview

- **Goal:** Run official FlashVSR on Ubuntu EC2 with NVIDIA GPU, output exact 1080p when requested.
- **Pipeline:** Input video → FlashVSR (4× super-resolution) → FFmpeg normalization to target resolution (default 1920×1080).
- **Design:** Modular, type-hinted, CLI-first; optional FastAPI stub for future API deployment.
- **Aspect ratio:** Preserved by default via letterboxing (pad); crop and stretch are configurable.

## Architecture

```
input video
    → env check (GPU, ffmpeg, repo, weights)
    → probe (ffprobe)
    → FlashVSR inference (official scripts in subprocess)
    → raw upscaled video
    → FFmpeg normalize to 1920×1080 (pad/crop/stretch)
    → final output + metadata
```

- **Config:** `config/settings.py` (env + `.env`).
- **CLI:** `app/cli.py` — main interface.
- **Pipeline:** `app/services/pipeline_service.py` orchestrates probe → FlashVSR → postprocess.
- **FlashVSR integration:** `app/services/flashvsr_runner.py` copies input into the repo’s expected path, runs the official inference script from `examples/WanVSR`, then locates the output in `results/`.

### Official FlashVSR integration

The upstream scripts do **not** accept CLI arguments; they use hardcoded paths:

- **Input:** `./inputs/example4.mp4` (tiny_long_video) or `./inputs/example0.mp4` (full/tiny).
- **Output:** `./results/FlashVSR_v1.1_Tiny_Long_example4_seed0.mp4` (pattern varies by version/mode).

Our wrapper:

1. Copies your input file into the repo’s `examples/WanVSR/inputs/` under the expected name (`example4.mp4` or `example0.mp4` depending on mode).
2. Runs the corresponding script with `cwd=examples/WanVSR` and the repo’s Python (or the one you pass).
3. Finds the generated file in `results/` (by known filename pattern or newest `.mp4`).
4. Copies that file into your output directory and passes it to the normalization step.

No modifications to the official repo are required.

### 1080p normalization

FlashVSR is 4× super-resolution; output size depends on input. To get **exact** 1920×1080:

- **pad (default):** Scale to fit inside 1920×1080 preserving aspect ratio, then add black bars (letterbox/pillarbox). No cropping.
- **crop:** Scale to cover 1920×1080 preserving aspect ratio, then center-crop to 1920×1080.
- **stretch:** Force 1920×1080; may distort aspect ratio.

Implemented in `app/utils/ffmpeg_tools.py` and used by `app/services/postprocess_service.py`.

## Prerequisites

- **OS:** Ubuntu (e.g. EC2).
- **Python:** 3.11 (for both this app and the official FlashVSR repo).
- **NVIDIA GPU** and driver (e.g. `nvidia-smi`).
- **FFmpeg** (and ffprobe) in PATH.
- **Git LFS** (for downloading model weights).
- **Official FlashVSR repo** cloned and installed (see below).
- **Block-Sparse-Attention** installed in the same environment as FlashVSR.

## One-shot bootstrap (EC2 GPU)

On an EC2 instance with a **Deep Learning AMI** (NVIDIA driver pre-installed), you can run a single script from the project root to install system deps, FlashVSR, weights, and generate `.env`:

```bash
bash scripts/bootstrap.sh
```

Optional: set a custom repo path before running:

```bash
export FLASHVSR_REPO_PATH=/opt/flashvsr/FlashVSR
bash scripts/bootstrap.sh
```

This runs `setup_ubuntu_ec2.sh`, `install_flashvsr.sh`, `download_weights.sh`, then creates/updates `.env` with `FLASHVSR_REPO_PATH` and `FLASHVSR_PYTHON`. No manual config steps required.

## EC2 Ubuntu setup (manual)

If you prefer to run each step yourself:

1. **System deps and FFmpeg / Git LFS:**

   ```bash
   bash scripts/setup_ubuntu_ec2.sh
   ```

2. **Clone FlashVSR and install (venv + Block-Sparse-Attention):**

   ```bash
   export FLASHVSR_REPO_PATH=/opt/flashvsr/FlashVSR   # or third_party/FlashVSR
   bash scripts/install_flashvsr.sh
   ```

   - Uses Python 3.11 venv inside the repo; installs PyTorch/CUDA from the official `requirements.txt`.
   - Block-Sparse-Attention build can be memory-heavy; reduce parallelism if needed (e.g. `MAX_JOBS=1`).

3. **Download weights (Hugging Face, Git LFS):**

   ```bash
   bash scripts/download_weights.sh        # v1.1
   # or
   bash scripts/download_weights.sh v1     # v1
   ```

   Weights land in `examples/WanVSR/FlashVSR-v1.1/` or `FlashVSR/`.

4. **Configure this app:**

   ```bash
   cp .env.example .env
   # Set FLASHVSR_REPO_PATH (and optionally FLASHVSR_PYTHON to repo venv)
   ```

## NVIDIA / CUDA notes

- Official FlashVSR uses PyTorch with CUDA (e.g. cu124). Match your driver and CUDA version.
- Block-Sparse-Attention is tested on A100/A800; other GPUs may work but are less documented.
- If `nvidia-smi` is missing, the app fails gracefully with a clear error.

## Install FlashVSR (official repo)

- Clone: `git clone https://github.com/OpenImagingLab/FlashVSR`
- From repo root: `pip install -e . && pip install -r requirements.txt`
- Install Block-Sparse-Attention in a **separate** clone, then `pip install` from that clone (see official README and `scripts/install_flashvsr.sh`).

## Install Block-Sparse-Attention

```bash
git clone https://github.com/mit-han-lab/Block-Sparse-Attention
cd Block-Sparse-Attention
pip install packaging ninja
python setup.py install
```

Build can be memory-intensive; use a single job if needed.

## Download weights

- From `examples/WanVSR`:  
  `git lfs install` then  
  `git lfs clone https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1` (or `FlashVSR` for v1).
- Or use `scripts/download_weights.sh` after setting `FLASHVSR_REPO_PATH`.

## Environment variables

See `.env.example`. Main ones:

| Variable | Description |
|----------|-------------|
| `FLASHVSR_REPO_PATH` | Path to official FlashVSR repo root. |
| `FLASHVSR_MODEL_ROOT` | Optional; root dir containing `FlashVSR/` and `FlashVSR-v1.1/`. |
| `FLASHVSR_DEFAULT_MODEL_VERSION` | `v1.1` or `v1`. |
| `FLASHVSR_DEFAULT_MODE` | `full`, `tiny`, or `tiny_long_video`. |
| `FFMPEG_BIN` / `FFPROBE_BIN` | Default `ffmpeg` / `ffprobe`. |
| `LOG_LEVEL` | e.g. `INFO`. |
| `FLASHVSR_PYTHON` | Optional; Python used to run FlashVSR (e.g. repo venv). |

## Run the CLI

**Upscale and keep the same aspect ratio** (no resize/normalize):

```bash
python -m app.cli --input /data/input/sample.mp4 --output-dir /data/output --no-normalize
```

Output is written as `{input_stem}_upscaled.mp4` with the same aspect ratio as the input (FlashVSR 4× super-resolution).

**Upscale and then normalize to a target resolution** (e.g. 1080p):

```bash
python -m app.cli \
  --input /data/input/sample.mp4 \
  --output-dir /data/output \
  --target-width 1920 \
  --target-height 1080 \
  --model-version v1.1 \
  --mode tiny_long_video \
  --fit-mode pad \
  --keep-intermediate
```

- **Environment check only:** `python -m app.cli --env-check-only --model-version v1.1`
- **JSON result:** add `--json`

The CLI prints environment summary, model/mode, input resolution, stage progress, and final output path.

## Example: same aspect ratio only

```bash
export FLASHVSR_REPO_PATH=/opt/flashvsr/FlashVSR
export FLASHVSR_PYTHON=/opt/flashvsr/FlashVSR/.venv/bin/python

python -m app.cli --input ./my_video.mp4 --output-dir ./out --no-normalize
```

Output: `./out/my_video_upscaled.mp4` — upscaled with the same aspect ratio as the input.

To also normalize to 1080p (pad/crop/stretch), omit `--no-normalize` and use `--target-width 1920 --target-height 1080 --fit-mode pad`. Result: `./out/my_video_1080p.mp4`.

## Running tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Optional API stub

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

- `GET /health` — readiness.
- `POST /upscale` — placeholder (returns a message directing use of the CLI); can be wired to the pipeline later.

## Troubleshooting

| Issue | Suggestion |
|-------|------------|
| `nvidia-smi not found` | Install NVIDIA driver; run on a GPU instance. |
| `FLASHVSR_REPO_PATH is not set` | Set in `.env` or export before running. |
| `Missing weights` | Run `scripts/download_weights.sh`; ensure Git LFS pulled files. |
| `Inference script not found` | Ensure repo has `examples/WanVSR/infer_flashvsr_*.py`. |
| FlashVSR subprocess fails | Run the same script manually from `examples/WanVSR` with the repo Python; check CUDA and Block-Sparse-Attention. |
| FFmpeg errors | Install ffmpeg/ffprobe; check input is a valid video. |
| Block-Sparse-Attention OOM during build | Use `MAX_JOBS=1` or build on a machine with more RAM. |

## Known limitations

- FlashVSR is designed for **4×** super-resolution; exact 1080p is achieved by a post-resize step (FFmpeg) when the model output is not already 1920×1080.
- Performance depends on GPU and CUDA/PyTorch stack; official repo recommends 4× setting for best quality.
- Official inference scripts use hardcoded input/output names; we work around this by copying input and discovering output; see “Official FlashVSR integration” above.

## License

Respect the official FlashVSR and Block-Sparse-Attention licenses. This app is provided as a wrapper only.
