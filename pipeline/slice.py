"""Slice parts with PrusaSlicer to get real print time + filament (Prusa MK4S).

Runs the PrusaSlicer CLI on each part STL with an exported MK4S config and reads
the time + filament estimates back out of the gcode -- so the farm split can be
balanced by actual minutes instead of by volume.  Entirely optional: if
PrusaSlicer or the config isn't present, callers fall back to the volume proxy.

Setup (once, on the Mac): in PrusaSlicer pick the Original Prusa MK4S 0.4mm
profile + your filament, then File > Export > Export Config -> save as
pipeline/profiles/mk4s.ini  (or point PRUSA_CONFIG at it).  PrusaSlicer itself is
found on PATH, at /Applications/PrusaSlicer.app, or via $PRUSA_SLICER.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "profiles", "mk4s.ini")

_SLICER_NAMES = ["prusa-slicer", "prusa-slicer-console", "prusaslicer", "PrusaSlicer"]
_MAC_APP = "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"


def find_slicer():
    env = os.environ.get("PRUSA_SLICER")
    if env and os.path.exists(env):
        return env
    for n in _SLICER_NAMES:
        p = shutil.which(n)
        if p:
            return p
    return _MAC_APP if os.path.exists(_MAC_APP) else None


def _hms_to_s(s):
    return sum(int(v) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[u]
               for v, u in re.findall(r"(\d+)\s*([dhms])", s))


def parse_gcode(text):
    """Pull estimated time (s) + filament (g) from PrusaSlicer gcode comments."""
    t = re.search(r"estimated printing time \(normal mode\)\s*=\s*([\dhdms ]+)", text)
    grams = re.findall(r"filament used \[g\]\s*=\s*([\d.]+)", text)
    return {
        "time_s": _hms_to_s(t.group(1)) if t else None,
        "filament_g": round(sum(float(g) for g in grams), 1) if grams else None,
    }


def slice_part(stl, config=None, slicer=None, out_gcode=None, timeout=900):
    """Slice one STL -> {time_s, filament_g, gcode}, or None if it can't slice."""
    slicer = slicer or find_slicer()
    config = config or os.environ.get("PRUSA_CONFIG") or DEFAULT_CONFIG
    if not slicer or not os.path.exists(config):
        return None
    out_gcode = out_gcode or tempfile.NamedTemporaryFile(suffix=".gcode", delete=False).name
    try:
        subprocess.run([slicer, "--export-gcode", "--load", config,
                        "--output", out_gcode, stl],
                       check=True, capture_output=True, timeout=timeout)
        with open(out_gcode) as fh:
            res = parse_gcode(fh.read())
        res["gcode"] = out_gcode
        return res
    except Exception:
        return None


def estimate_parts(stl_paths, config=None):
    """Slice many parts. Returns {part_name: {time_s, filament_g}} for those sliced."""
    slicer = find_slicer()
    if not slicer:
        return {}
    out = {}
    for p in stl_paths:
        r = slice_part(p, config=config, slicer=slicer)
        if r and r.get("time_s"):
            out[os.path.splitext(os.path.basename(p))[0]] = {
                "time_s": r["time_s"], "filament_g": r["filament_g"]}
    return out


def fmt_minutes(minutes):
    m = int(round(minutes))
    return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m}m"
