name: cad
description: Design-to-print pipeline. Use whenever the user wants a 3D-printable object — whether they describe a mechanical part OR send a photo / describe a real-world thing to recreate. Builds the model, publishes an interactive 3D preview the user can spin on their phone, waits for approval, then delivers the printable STL.

# CAD Design Pipeline

Run this for the object the user described (or sent a photo of) in their task.
Follow the phases IN ORDER. Never skip the approval gate. Everything runs
LOCALLY on this Mac — no paid services, no cloud generation. Run pipeline
commands with the repo environment active (`source .venv/bin/activate`); if it
isn't set up yet, run the setup skill (.agents/skills/setup/SKILL.md) first.

Pick the track first:

- TRACK A — Organic / "make it look like this": the user sends a PHOTO, or asks
  for a character / figure / sculpture / realistic object (a hand, an animal, a
  bust). Reconstruct real geometry from an image with the local GPU model.
  Do NOT try to hand-write an organic shape in code — it never looks right.
- TRACK B — Mechanical / measured: brackets, holders, stands, boxes, adapters —
  things defined by dimensions and fits. Write a parametric build123d model.

## Phase 1: Interview
Ask only what changes the geometry, in ONE short batch, in plain language:
- Track A: if no photo was provided, ask for one (or a clear reference image).
  Ask the real-world SIZE it should be ("how tall, in cm?") and whether it has
  to hold or fit anything (and that object's measurements).
- Track B: critical dimensions, what it interfaces with (ask for measurements),
  print orientation.
- Both: is it one piece or several that fit together (base + lid, moving parts)?
  How do they connect? Each piece prints separately, and anything bigger than the
  printer bed is auto-split.
- Defaults: Prusa MK4S, 0.4mm nozzle, 0.2mm layers, 2.4mm walls, 15% infill;
  several MK4S units are available for parallel printing. State any defaults you chose.

## Phase 2: Build

TRACK A (from a photo):
1. Generate the shape on the Mac's GPU:
       python -m pipeline.generate <photo> --out designs/<slug>
   (defaults to geometry-only TRELLIS-mac; local, a few minutes.)
2. Clean it into a printable solid and scale to the real size the user gave:
       from pipeline.cleanup import make_printable
   Make it watertight and single-volume; scale so the longest side matches.
3. Add functional features parametrically with build123d / trimesh (a flat seat,
   a pocket, a hidden cable channel) ONLY if the user asked for them.
4. Export designs/<slug>/model.stl (and model.step if it is solid CAD). It's one
   piece; if it's bigger than the MK4S bed it gets auto-split in Phase 4.

TRACK B (mechanical):
1. Write designs/<slug>/model.py — parametric build123d, key dimensions as named
   variables at the top; guards: no wall < 1.2mm, flag overhangs > 50°.
2. Run it; export model.stl + model.step.
3. Validate it is watertight (trimesh.load(...).is_watertight); fix and
   re-export if not.
4. If it's an assembly, model each piece as its own named solid and keep them as
   {name: solid_or_stl} for packaging in Phase 4; export the assembled whole to
   model.stl for the preview.

## Phase 3: Interactive 3D preview for review
1. Build the interactive preview (NOT photo renders):
       python -m pipeline.viewer designs/<slug>/model.stl --title "<name>"
   → designs/<slug>/review.html (spin / zoom in a browser).
2. Commit and push it so the 3D site updates, then give the user the tappable
   link:  https://ramofmt.github.io/3d-designs/designs/<slug>/review.html
3. Tell them the final real-world size and STOP for approval. If they want
   changes, adjust and redo Phase 2 + 3.

## Phase 4: Deliver
Once approved:
1. Package into printable parts (auto-splits anything bigger than the MK4S bed,
   adding alignment pins so the pieces line up):
       python -m pipeline.parts designs/<slug>/parts/*.stl --name "<name>" --printers <N>
   or call pipeline.parts.package_parts({name: solid_or_stl}, "designs/<slug>",
   printers=<N>, assembly_notes="...") from the build script. This writes
   parts/<piece>.stl, PARTS.md (parts list + split-across-printers plan), and
   parts_preview.html. With a PrusaSlicer MK4S config (pipeline/profiles/mk4s.ini),
   PARTS.md also shows real per-part print time + filament and balances printers
   by minutes.
2. Commit and push so the parts list and previews are saved.
3. Tell the user — in plain language — the pieces and their sizes, which to run on
   each MK4S unit (the plan in PARTS.md), suggested orientation, supports, infill
   (15% default, more if load-bearing), and EXACTLY which files to print (every
   .stl in parts/).

## Rules
- Everything is local. Never use a paid or cloud generation service.
- Never pass a phase gate without an explicit user response.
- Track B stays parametric: "make the slot 2mm wider" = a one-variable change.
- If something is unprintable as described (zero-thickness, floating bits),
  explain it simply and propose the closest printable version first.
- Talk to the user in plain language (see agents.md). Keep the jargon in code.
