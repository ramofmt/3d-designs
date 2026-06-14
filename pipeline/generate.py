"""Local image-to-3D generation on the Mac's GPU -- no paid services.

Wraps a locally-installed Apple-Silicon image-to-3D model and returns a mesh
file.  Default backend is TRELLIS-mac (https://github.com/shivampkumar/trellis-mac),
which runs entirely on the Mac Mini's GPU via Metal/MPS -- nothing leaves the
machine.

One-time setup (see SETUP.md): clone & install TRELLIS-mac, then:
    export TRELLIS_DIR="$HOME/trellis-mac"
    export PYTORCH_ENABLE_MPS_FALLBACK=1
(TRELLIS_DIR/.venv/bin/python is used automatically if present.)

Any other local model works too -- set GEN3D_CMD to its command, using the
{image} and {output} placeholders, e.g.
    export GEN3D_CMD='python ~/my-model/infer.py {image} {output}'

Usage:
    python -m pipeline.generate photo.jpg --out designs/thing-hand
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys


def _load_dotenv():
    """Load repo-root .env (written by scripts/setup.sh) so TRELLIS_DIR etc. are
    available without manual exports. Real env vars take precedence."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


def _python_for(trellis_dir):
    venv_py = os.path.join(trellis_dir, ".venv", "bin", "python")
    return venv_py if os.path.exists(venv_py) else sys.executable


def _stage(path, out_dir):
    """Move the produced mesh into out_dir if it isn't already there."""
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(out_dir):
        dst = os.path.join(out_dir, os.path.basename(path))
        shutil.copy(path, dst)
        return dst
    return path


def _collect(out_base, out_dir, extra_dirs=()):
    exact = [out_base + ".glb", out_base + ".obj"]
    for d in (out_dir, *extra_dirs):
        exact.append(os.path.join(d, "output_3d.glb"))
    for c in exact:
        if os.path.exists(c):
            return _stage(c, out_dir)
    hits = []
    for d in (out_dir, *extra_dirs):
        hits += glob.glob(os.path.join(d, "*.glb")) + glob.glob(os.path.join(d, "*.obj"))
    if hits:
        return _stage(max(hits, key=os.path.getmtime), out_dir)
    raise RuntimeError(f"generator finished but produced no mesh near {out_dir}")


def image_to_mesh(image_path, out_dir, texture=False, pipeline="512", seed=42,
                  trellis_dir=None, cmd_template=None, timeout=2400):
    """Run local image->3D on the Mac GPU. Returns the path to the produced mesh.

    Backends, in priority order:
      1. cmd_template / $GEN3D_CMD -- shell template with {image} {output}.
      2. TRELLIS-mac at trellis_dir / $TRELLIS_DIR (default).
    """
    os.makedirs(out_dir, exist_ok=True)
    image_path = os.path.abspath(image_path)
    out_base = os.path.join(os.path.abspath(out_dir), "generated")
    env = dict(os.environ, PYTORCH_ENABLE_MPS_FALLBACK="1")

    tmpl = cmd_template or os.environ.get("GEN3D_CMD")
    if tmpl:
        subprocess.run(tmpl.format(image=image_path, output=out_base),
                       shell=True, check=True, env=env, timeout=timeout)
        return _collect(out_base, out_dir)

    trellis_dir = trellis_dir or os.environ.get("TRELLIS_DIR")
    if not trellis_dir or not os.path.isdir(trellis_dir):
        raise RuntimeError(
            "No local generator configured. Install TRELLIS-mac "
            "(https://github.com/shivampkumar/trellis-mac) and set TRELLIS_DIR, "
            "or set GEN3D_CMD to your model's command (with {image} {output}). "
            "See SETUP.md.")

    cmd = [_python_for(trellis_dir), os.path.join(trellis_dir, "generate.py"),
           image_path, "--output", out_base,
           "--pipeline-type", str(pipeline), "--seed", str(seed)]
    if not texture:
        cmd.append("--no-texture")          # geometry-only: faster + clean for FDM
    subprocess.run(cmd, check=True, env=env, cwd=trellis_dir, timeout=timeout)
    return _collect(out_base, out_dir, extra_dirs=(trellis_dir,))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Local image->3D on the Mac GPU (no paid services)")
    ap.add_argument("image")
    ap.add_argument("--out", required=True, help="design folder, e.g. designs/<slug>")
    ap.add_argument("--texture", action="store_true", help="bake textures (default: geometry-only)")
    ap.add_argument("--pipeline", default="512", choices=["512", "1024", "1024_cascade"])
    a = ap.parse_args()
    mesh = image_to_mesh(a.image, a.out, texture=a.texture, pipeline=a.pipeline)
    print("mesh:", mesh)
