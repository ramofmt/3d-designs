"""Interactive 3D preview -- the review artifact (replaces photo renders).

Exports the model to GLB and wraps it in an HTML page that renders an
interactive, spinnable 3D view in any browser (model-viewer).  The GLB is
base64-embedded and the model-viewer library is vendored in the repo
(../../vendor), so the published page pulls from NO external service -- it just
works when served from GitHub Pages and is fully self-hosted.

Served at: https://ramofmt.github.io/3d-designs/designs/<slug>/review.html

CLI:
    python -m pipeline.viewer designs/<slug>/model.stl --title "Watch charger"
"""
from __future__ import annotations

import argparse
import base64
import os

import trimesh

HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>{title}</title>
<script type="module" src="{mv_src}"></script>
<style>
  html,body{{margin:0;height:100%;background:#15171c;color:#cfd3da;
    font:14px/1.4 -apple-system,Segoe UI,Roboto,sans-serif}}
  model-viewer{{width:100vw;height:100vh;--poster-color:#15171c}}
  .cap{{position:fixed;left:14px;bottom:12px;padding:8px 12px;border-radius:8px;
    background:rgba(0,0,0,.45);backdrop-filter:blur(6px);white-space:pre-line}}
  .t{{color:#fff;font-weight:600}}
</style></head><body>
<model-viewer src="data:model/gltf-binary;base64,{b64}"
  camera-controls auto-rotate touch-action="pan-y" shadow-intensity="1"
  exposure="1.0" environment-image="neutral" interaction-prompt="none"
  camera-orbit="-35deg 70deg auto"></model-viewer>
<div class="cap"><span class="t">{title}</span>
{caption}</div>
</body></html>"""


def _maybe_decimate(mesh, max_faces):
    if len(mesh.faces) <= max_faces:
        return mesh
    try:
        return mesh.simplify_quadric_decimation(face_count=max_faces)
    except Exception:
        return mesh


def export_glb(model, out_glb, max_faces=200_000):
    mesh = model if isinstance(model, trimesh.Trimesh) else trimesh.load(model, force="mesh")
    mesh = _maybe_decimate(mesh, max_faces)
    trimesh.Scene(mesh).export(out_glb)
    return out_glb, mesh


def make_viewer(model, out_html, title="Model", caption="", max_faces=200_000,
                mv_src="../../vendor/model-viewer.min.js"):
    """Write the interactive 3D preview HTML. Returns its path.

    mv_src is the path to the vendored model-viewer library, relative to the
    HTML file (default assumes designs/<slug>/review.html -> ../../vendor/).
    """
    glb_tmp = out_html.rsplit(".", 1)[0] + ".glb"
    _, mesh = export_glb(model, glb_tmp, max_faces=max_faces)
    if not caption:
        size = mesh.bounds[1] - mesh.bounds[0]
        caption = (f"{size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm   "
                   f"vol {mesh.volume / 1000:.1f} cm3   {len(mesh.faces):,} tris")
    b64 = base64.b64encode(open(glb_tmp, "rb").read()).decode()
    with open(out_html, "w") as fh:
        fh.write(HTML.format(title=title, b64=b64, caption=caption, mv_src=mv_src))
    os.remove(glb_tmp)  # fully embedded; no loose file needed
    return out_html


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Interactive 3D preview (GLB + vendored model-viewer)")
    ap.add_argument("model")
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default="Model")
    ap.add_argument("--max-faces", type=int, default=200_000)
    ap.add_argument("--mv-src", default="../../vendor/model-viewer.min.js")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.model)), "review.html")
    p = make_viewer(a.model, out, title=a.title, max_faces=a.max_faces, mv_src=a.mv_src)
    print("viewer:", p, f"({os.path.getsize(p)/1e6:.1f} MB)")
