About this repository
This repo is used by a non-technical person to design 3D-printable objects.
He interacts only from the ChatGPT mobile app, which is connected to Codex
running locally on a Mac Mini. Everything runs on that Mac — no paid services,
no cloud generation. Adjust all behavior accordingly.

Communication rules
Use plain language. No jargon (no "manifold," "B-Rep," "mesh," "venv" — say
"watertight," "solid model," "3D shape," "setup" instead).
Never ask him to run terminal commands, edit code, or use git directly.
You do all of that; he only describes, sends photos, answers questions, and approves.
Keep questions short and concrete. Ask about real-world measurements
("how tall should it be, in cm?") rather than technical parameters.
When showing results, always state plainly: what the object is, its final size,
the link to spin it around in 3D, and exactly which file he should download to
print (the .stl file).

Default task: 3D design
If he describes an object he wants to print — or sends a photo of something to
recreate — even without typing cad, use the CAD skill at
.agents/skills/cad/SKILL.md and follow its pipeline: interview, build, publish
an interactive 3D preview, wait for approval, then deliver files.

Two kinds of request (the skill picks automatically):
- A photo, or a character / figure / realistic object ("make it look like
  this") → the shape is generated from an image on the Mac's GPU.
- A measured mechanical part (holder, bracket, stand) → built as a parametric
  solid model.

Repository conventions
Every design lives in its own folder: designs/<slug>/
Each design folder contains: model.stl (the printable file), model.step when it
is a solid CAD part, and review.html (the interactive 3D preview).
Never delete or modify a previous design's folder unless he explicitly asks.
New versions of an old design get a new folder (e.g. designs/phone-stand-v2/).
Commit and push the interactive preview (review.html) BEFORE asking for
approval, and give him its link:
  https://ramofmt.github.io/3d-designs/designs/<slug>/review.html

Technical defaults (do not ask him about these)
build123d for solid modeling, trimesh + manifold3d for watertight cleanup,
TRELLIS-mac (local, on the Mac GPU) for turning photos into 3D shapes,
model-viewer for the interactive 3D preview. No photo renders, no paid services.
FDM printing: 0.4mm nozzle, 0.2mm layers, 2.4mm walls, 15% infill unless the
part bears load.
Always verify the STL is watertight before delivering it.
Setup is documented in SETUP.md. If packages are missing, the one-time fix
(adding them to the environment setup) is something his brother handles.
