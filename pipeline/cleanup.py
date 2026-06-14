"""Mesh / CAD cleanup helpers for the print pipeline.

- step_to_stl:  tessellate a Zoo/CAD STEP B-rep into a watertight STL (OCP only,
  no build123d, so it's unaffected by the 0.8.0 pin).
- make_printable: repair an AI-generated mesh (Tripo/fal/Hunyuan etc.) into a
  single watertight, winding-consistent, positive-volume STL for FDM.

CLI:
    python -m pipeline.cleanup model.step           # -> model.stl
    python -m pipeline.cleanup raw.glb --faces 80000 # -> raw.printable.stl
"""
from __future__ import annotations

import argparse
import os

import trimesh


def step_to_stl(step_path, stl_path=None, deflection=0.08, angular=0.4):
    """STEP -> watertight binary STL via OpenCASCADE tessellation."""
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer

    stl_path = stl_path or os.path.splitext(step_path)[0] + ".stl"
    reader = STEPControl_Reader()
    if reader.ReadFile(step_path) != IFSelect_RetDone:
        raise RuntimeError(f"could not read STEP: {step_path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, deflection, False, angular, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    writer.Write(shape, stl_path)
    return stl_path


def make_printable(mesh_or_path, out_stl=None, target_faces=None):
    """Repair an AI/scan mesh into a watertight, single-volume STL. Returns the mesh."""
    m = mesh_or_path if isinstance(mesh_or_path, trimesh.Trimesh) \
        else trimesh.load(mesh_or_path, force="mesh")
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.update_faces(m.unique_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(m)
    trimesh.repair.fix_normals(m)
    if not m.is_watertight:
        trimesh.repair.fill_holes(m)
        trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    if target_faces and len(m.faces) > target_faces:
        m = m.simplify_quadric_decimation(face_count=target_faces)
    if out_stl:
        m.export(out_stl)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cleanup: STEP->STL or repair AI mesh->STL")
    ap.add_argument("src")
    ap.add_argument("--out", default=None)
    ap.add_argument("--faces", type=int, default=None, help="decimate to N faces (mesh path)")
    a = ap.parse_args()
    if a.src.lower().endswith((".step", ".stp")):
        out = step_to_stl(a.src, a.out)
        print("STL:", out)
    else:
        out = a.out or os.path.splitext(a.src)[0] + ".printable.stl"
        m = make_printable(a.src, out, target_faces=a.faces)
        print(f"STL: {out}  watertight={m.is_watertight}  faces={len(m.faces)}  "
              f"vol={m.volume/1000:.1f}cm3")
