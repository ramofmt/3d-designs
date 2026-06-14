#!/usr/bin/env bash
# One-shot local setup for the Mac Mini. Idempotent -- safe to re-run.
# Installs the Python stack + the local image-to-3D model, writes .env, and
# turns on the 3D-preview website. Everything stays on this machine.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
echo "==> repo: $ROOT"

# 1. Python stack (isolated venv)
PY="${PYTHON:-python3}"
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt && echo "==> python stack installed"

# 2. Local image->3D model on the Mac GPU (TRELLIS-mac)
TRELLIS_DIR="${TRELLIS_DIR:-$HOME/trellis-mac}"
[ -d "$TRELLIS_DIR" ] || git clone --depth 1 https://github.com/shivampkumar/trellis-mac "$TRELLIS_DIR"
if [ ! -d "$TRELLIS_DIR/.venv" ]; then
  echo "==> building TRELLIS-mac (one-time, compiles Metal kernels)"
  ( cd "$TRELLIS_DIR" && bash setup.sh )
fi
echo "==> TRELLIS-mac at $TRELLIS_DIR"

# 3. .env -- the pipeline auto-loads this; no shell-profile edits needed
cat > .env <<ENV
TRELLIS_DIR=$TRELLIS_DIR
PYTORCH_ENABLE_MPS_FALLBACK=1
ENV
echo "==> wrote .env"

# 4. Hugging Face auth (model weights download, free + one-time) -- check only
if [ -s "$HOME/.cache/huggingface/token" ] || [ -s "$HOME/.huggingface/token" ]; then
  echo "==> Hugging Face: signed in"
else
  echo "==> Hugging Face: NOT signed in -- run 'hf auth login' once (free) to download model weights"
fi

# 5. GitHub Pages (the 3D-preview site)
if command -v gh >/dev/null 2>&1; then
  if gh api --method POST repos/ramofmt/3d-designs/pages -f build_type=workflow >/dev/null 2>&1; then
    echo "==> GitHub Pages enabled (GitHub Actions source)"
  else
    echo "==> GitHub Pages already on, or enable manually: Settings > Pages > Source: GitHub Actions"
  fi
else
  echo "==> gh not found -- enable Pages manually: Settings > Pages > Source: GitHub Actions"
fi

echo "==> setup complete"
