name: cad
description: Design-to-print CAD pipeline. Use when the user asks to design a 3D-printable part. Interviews the user, builds a parametric build123d model, renders previews for approval, then delivers STL/STEP files.
CAD Design Pipeline
Run a design-to-print pipeline for the part the user described in their task.
Follow these phases IN ORDER. Do not skip the approval gate.
Phase 1: Interview
Before writing any code, ask the user about the design. Ask only questions
whose answers actually change the geometry. Cover whichever apply:
Critical dimensions (overall size, hole diameters, clearances)
What it interfaces with (does it need to fit a real object? Ask for measurements)
Orientation on the print bed and overhang tolerance
Material/process assumptions (FDM default: 0.4mm nozzle, 0.2mm layers)
Wall thickness preference (default 2.4mm = 6 perimeters for strength)
Aesthetic preferences only if they matter (fillets, chamfers)
Ask all questions in ONE batch. Propose sensible defaults for anything
not specified, and state the defaults you chose.
Phase 2: Build
Write a parametric build123d Python script in designs/<slug>/model.py
All key dimensions as named variables at the top of the file
Add printability guards: no walls thinner than 1.2mm, flag overhangs > 50°
Install build123d and trimesh in the environment if missing.
Run the script. It must export BOTH:
model.stl (for slicing)
model.step (for future editing)
Validate the mesh: confirm it is watertight/manifold
(trimesh.load('model.stl').is_watertight). If not, fix and re-export.
Phase 3: Render for review
Render the model to PNG images from 3-4 angles (front, side, top,
isometric). Use matplotlib 3D mesh plotting (no GPU in the sandbox),
saved to designs/<slug>/renders/.
Commit the renders so the user can view them in the diff/PR, and
provide a summary table of final dimensions.
STOP and ask for approval. Do not proceed until the user explicitly
approves. If they request changes, edit the parameters, re-run
Phase 2 + 3.
Phase 4: Deliver
Once approved:
Commit model.stl and model.step to designs/<slug>/ and state
their paths clearly.
Summarize: final dimensions, suggested print orientation, whether
supports are likely needed, and recommended infill (default 15%,
higher if the part bears load).
Rules
Never proceed past a phase gate without an explicit user response.
Keep every dimension parametric: "make the slot 2mm wider" should be
a one-variable change.
If a request is unprintable as described (zero-thickness surface,
floating geometry), explain the problem and propose the closest
printable alternative before building it.
Note that the sandbox may have no internet access after setup; declare
pip dependencies (build123d, trimesh, matplotlib) in the environment
setup script if package installs fail at runtime.
