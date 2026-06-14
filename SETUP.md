# Setup (Mac Mini)

Everything runs locally on the Mac's GPU. **No paid services, no cloud generation.**

## 1. Pipeline dependencies
Python 3.11+. From the repo root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Installs the CAD + mesh + viewer stack (build123d, trimesh, manifold3d, numpy,
Pillow). On Apple Silicon these have current wheels — no version pinning needed
(unlike the no-GPU Oracle box, which is locked to old OCP/build123d).

## 2. Local image-to-3D model (the GPU generator)
Turns a photo into a 3D shape, on the Mac's GPU. Default: **TRELLIS-mac**.

```bash
git clone https://github.com/shivampkumar/trellis-mac ~/trellis-mac
cd ~/trellis-mac && bash setup.sh     # builds its own venv + Metal kernels
hf auth login                         # one-time, to download the model weights
```

Then point the pipeline at it (add to your shell profile / Codex env):

```bash
export TRELLIS_DIR="$HOME/trellis-mac"
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

First image → mesh takes ~3–5 min on an M4 Pro (24 GB+). Geometry-only by
default (`--no-texture`) — exactly what FDM printing needs.

**Any other local model** works instead — set `GEN3D_CMD` with `{image}` and
`{output}` placeholders:
```bash
export GEN3D_CMD='python ~/my-model/infer.py {image} {output}'
```

## 3. Interactive 3D preview site (GitHub Pages)
`review.html` files are served as a tappable 3D site. Enable once:

```bash
gh api -X POST repos/ramofmt/3d-designs/pages -f build_type=workflow
```

(or repo **Settings → Pages → Source: GitHub Actions**). The included workflow
`.github/workflows/pages.yml` then publishes every design at:

```
https://ramofmt.github.io/3d-designs/designs/<slug>/review.html
```

## 4. Codex environment
Make sure Codex's setup step runs `pip install -r requirements.txt` so the
sandbox has the stack, and that `TRELLIS_DIR` + the TRELLIS-mac install are
present on the Mac where Codex runs.
