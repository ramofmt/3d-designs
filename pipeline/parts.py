"""Break a design into individual printable parts -- tuned for Prusa MK4S.

Takes the parts of a design (build123d solids exported to STL, or trimesh
meshes) and produces, per design:
  - parts/<name>.stl            one printable file per piece
  - parts.json + PARTS.md       a parts list (qty, size, fits-bed?, farm split)
  - parts_preview.html          interactive 3D view of all the pieces laid out

Bed-fit and the farm split are sized for the Prusa MK4S (250 x 210 x 220 mm).
Oversize parts are flagged here; cutting them down is `split_to_bed` (todo).

CLI:
    python -m pipeline.parts designs/<slug>/parts/*.stl --name "Desk organizer" --printers 3
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import trimesh

# Prusa MK4S build volume (X, Y, Z), mm. Bed is NOT square -- Y is the tight axis.
PRUSA_MK4S = (250.0, 210.0, 220.0)
BED_MARGIN = 3.0  # keep a few mm off the edges (brim / skirt / nozzle clearance)


def _as_mesh(obj):
    if isinstance(obj, trimesh.Trimesh):
        return obj
    if isinstance(obj, str):
        return trimesh.load(obj, force="mesh")
    # build123d / OCP objects expose .export_stl or work via trimesh; caller should
    # pass a mesh or an STL path to keep this module free of the build123d/OCP import.
    raise TypeError(f"pass a trimesh.Trimesh or an STL path, not {type(obj)}")


def fits_bed(extents, bed=PRUSA_MK4S, margin=BED_MARGIN):
    """True if the part fits the bed in SOME axis-aligned orientation."""
    part = sorted(float(e) for e in extents)
    room = sorted(b - margin for b in bed)
    return all(p <= r for p, r in zip(part, room))


def _aligned_cylinder(center, axis, radius, length, sections=24):
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    T = trimesh.geometry.align_vectors([0, 0, 1], np.asarray(axis, float))
    T[:3, 3] = center
    cyl.apply_transform(T)
    return cyl


def _interior_points(mesh, origin, normal, n=2):
    """A couple of points lying inside the solid's cross-section at the cut plane,
    spread out so the pins also resist rotation."""
    try:
        from shapely.geometry import Point
        planar, to3d = mesh.section(plane_origin=origin, plane_normal=normal).to_planar()
        polys = list(planar.polygons_full)
        if not polys:
            return []
        poly = max(polys, key=lambda p: p.area)
        minx, miny, maxx, maxy = poly.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        fracs = [0.5] if n == 1 else [0.28, 0.72]
        major_x = (maxx - minx) >= (maxy - miny)
        pts = []
        for f in fracs:
            q = Point(minx + f * (maxx - minx), cy) if major_x else Point(cx, miny + f * (maxy - miny))
            if not poly.contains(q):
                q = poly.representative_point()
            pts.append([q.x, q.y, 0.0])
        return trimesh.transform_points(np.array(pts), to3d)
    except Exception:
        return []


def _cut(mesh, pin_r, pin_len, clearance):
    """Split a mesh in two across its longest axis, with registration pins."""
    ext = mesh.extents
    axis = int(np.argmax(ext))
    normal = np.zeros(3); normal[axis] = 1.0
    origin = mesh.bounds.mean(axis=0)
    a = mesh.slice_plane(origin, normal, cap=True)
    b = mesh.slice_plane(origin, -normal, cap=True)
    if a is None or b is None or len(a.faces) == 0 or len(b.faces) == 0:
        return None, None
    try:
        bosses, holes = [], []
        for p in _interior_points(mesh, origin, normal, n=2):
            bosses.append(_aligned_cylinder(p, normal, pin_r, 2 * pin_len))
            holes.append(_aligned_cylinder(p - (pin_len / 2.0) * normal, normal,
                                           pin_r + clearance, pin_len + 1.0))
        if bosses:
            a = a.union(bosses, engine="manifold")
            b = b.difference(holes, engine="manifold")
    except Exception:
        pass  # fall back to plain flat-faced halves (glue them)
    return a, b


def split_to_bed(mesh, bed=PRUSA_MK4S, margin=BED_MARGIN,
                 pin_r=3.0, pin_len=5.0, clearance=0.2, max_pieces=16):
    """Cut an oversize mesh into pieces that each fit the bed, with pins to align
    them on reassembly. Returns a list of watertight pieces."""
    out, queue = [], [mesh.copy()]
    while queue and len(out) + len(queue) <= max_pieces:
        m = queue.pop(0)
        if fits_bed(m.extents, bed, margin):
            out.append(m); continue
        a, b = _cut(m, pin_r, pin_len, clearance)
        if a is None:
            out.append(m); continue
        queue.extend([a, b])
    out.extend(queue)
    return out


def _distribute(stats, printers):
    """Greedy longest-processing-time split across N printers, balanced by volume
    (a rough proxy for print time until PrusaSlicer gives real numbers)."""
    if printers <= 1:
        return None
    load = [0.0] * printers
    plan = [[] for _ in range(printers)]
    for s in sorted(stats, key=lambda x: x["volume_cm3"], reverse=True):
        i = int(np.argmin(load))
        plan[i].append(s["name"])
        load[i] += s["volume_cm3"]
    return [{"printer": i + 1, "parts": plan[i], "load_cm3": round(load[i], 1)}
            for i in range(printers) if plan[i]]


def _layout(meshes, gap=8.0):
    """Lay all parts in a row on the bed plane for a 'here are the pieces' view."""
    placed, x = [], 0.0
    for m in meshes:
        c = m.copy()
        c.apply_translation([x - c.bounds[0][0], -(c.bounds[0][1] + c.bounds[1][1]) / 2,
                             -c.bounds[0][2]])
        placed.append(c)
        x += c.extents[0] + gap
    return trimesh.util.concatenate(placed)


def package_parts(parts, out_dir, design_name="Design", bed=PRUSA_MK4S,
                  printers=1, assembly_notes="", make_preview=True, split=True):
    """Export each part + a parts list + a preview. `parts` is {name: mesh|stl_path}
    (or a list of those). Oversize parts are auto-cut to fit the bed when
    split=True. Returns the manifest dict."""
    if not isinstance(parts, dict):
        parts = {f"part{i+1}": p for i, p in enumerate(parts)}

    # Expand any part too big for the bed into bed-fitting, pinned sub-pieces.
    expanded, split_map = {}, {}
    for name, obj in parts.items():
        mesh = _as_mesh(obj)
        if not split or fits_bed(mesh.extents, bed):
            expanded[name] = mesh
            continue
        chunks = split_to_bed(mesh, bed)
        if len(chunks) == 1:
            expanded[name] = chunks[0]
        else:
            split_map[name] = len(chunks)
            for i, c in enumerate(chunks, 1):
                expanded[f"{name}_p{i}"] = c
    parts = expanded
    pdir = os.path.join(out_dir, "parts")
    os.makedirs(pdir, exist_ok=True)

    stats, meshes = [], []
    for name, obj in parts.items():
        mesh = _as_mesh(obj)
        stl = os.path.join(pdir, f"{name}.stl")
        mesh.export(stl)
        ext = mesh.extents
        stats.append({
            "name": name,
            "stl": os.path.relpath(stl, out_dir),
            "size_mm": [round(float(e), 1) for e in ext],
            "volume_cm3": round(float(mesh.volume) / 1000.0, 1),
            "watertight": bool(mesh.is_watertight),
            "fits_mk4s": fits_bed(ext, bed),
        })
        meshes.append(mesh)

    manifest = {
        "design": design_name,
        "printer": "Prusa MK4S",
        "bed_mm": list(bed),
        "part_count": len(stats),
        "parts": stats,
        "oversize": [s["name"] for s in stats if not s["fits_mk4s"]],
        "split_from": split_map,
        "farm_plan": _distribute(stats, printers),
        "assembly_notes": assembly_notes,
    }
    with open(os.path.join(out_dir, "parts.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    with open(os.path.join(out_dir, "PARTS.md"), "w") as fh:
        fh.write(_manifest_md(manifest))

    if make_preview:
        try:
            from .viewer import make_viewer
            preview = os.path.join(out_dir, "parts_preview.html")
            make_viewer(_layout(meshes), preview, title=f"{design_name} — {len(stats)} parts",
                        caption=f"{len(stats)} pieces · Prusa MK4S")
            manifest["preview"] = preview
        except Exception as exc:  # noqa: BLE001
            manifest["preview_error"] = str(exc)
    return manifest


def _manifest_md(m):
    lines = [f"# Parts to print — {m['design']}",
             f"Printer: **{m['printer']}** (bed {m['bed_mm'][0]:.0f} × {m['bed_mm'][1]:.0f} × {m['bed_mm'][2]:.0f} mm)",
             "", f"**{m['part_count']} piece(s).**", "",
             "| Part | Size (mm) | Volume | Fits MK4S? |",
             "|------|-----------|--------|------------|"]
    for s in m["parts"]:
        sz = " × ".join(f"{v:.0f}" for v in s["size_mm"])
        fit = "yes" if s["fits_mk4s"] else "**NO — too big, must be split**"
        lines.append(f"| {s['name']} | {sz} | {s['volume_cm3']} cm³ | {fit} |")
    if m.get("split_from"):
        lines += ["", "## Cut to fit the bed"]
        for name, k in m["split_from"].items():
            lines.append(f"- **{name}** was too big — cut into {k} pieces (`{name}_p1`…`{name}_p{k}`) that pin together on assembly.")
    if m["oversize"]:
        lines += ["", f"> Still too big for the bed: {', '.join(m['oversize'])} — could not be auto-cut; split manually in PrusaSlicer."]
    if m["farm_plan"]:
        lines += ["", "## Split across your printers"]
        for p in m["farm_plan"]:
            lines.append(f"- Printer {p['printer']}: {', '.join(p['parts'])}  ({p['load_cm3']} cm³)")
    if m["assembly_notes"]:
        lines += ["", "## How it goes together", m["assembly_notes"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Package a design into printable parts (Prusa MK4S)")
    ap.add_argument("stls", nargs="+", help="one STL per part")
    ap.add_argument("--out", default=None, help="output dir (default: parent of first STL's parent)")
    ap.add_argument("--name", default="Design")
    ap.add_argument("--printers", type=int, default=1)
    a = ap.parse_args()
    out = a.out or os.path.dirname(os.path.dirname(os.path.abspath(a.stls[0])))
    parts = {os.path.splitext(os.path.basename(p))[0]: p for p in a.stls}
    man = package_parts(parts, out, design_name=a.name, printers=a.printers)
    print(json.dumps({k: man[k] for k in ("part_count", "oversize", "farm_plan")}, indent=2))
