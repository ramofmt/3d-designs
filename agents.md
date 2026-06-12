About this repository
This repo is used by a non-technical person to design 3D-printable objects.
He interacts only from the ChatGPT mobile app. Adjust all behavior accordingly.
Communication rules
Use plain language. No jargon (no "manifold," "B-Rep," "venv" — say
"watertight," "solid model," "setup" instead).
Never ask him to run terminal commands, edit code, or use git directly.
You do all of that; he only describes, answers questions, and approves.
Keep questions short and concrete. Ask about real-world measurements
("how wide is the desk edge in mm?") rather than technical parameters.
When showing results, always state plainly: what the object is, its
final size, and exactly which file he should download to print
(the .stl file).
Default task: 3D design
If he describes an object he wants to print — even without typing $cad —
use the CAD skill at .agents/skills/cad/SKILL.md and follow its pipeline:
interview, build, render previews, wait for approval, then deliver files.
Repository conventions
Every design lives in its own folder: designs//
Each design folder contains: model.py (parametric build123d script),
model.stl, model.step, and renders/ with preview PNGs.
Never delete or modify a previous design's folder unless he explicitly
asks. New versions of an old design get a new folder (e.g.
designs/phone-stand-v2/).
Commit preview renders BEFORE asking for approval so he can view them.
Technical defaults (do not ask him about these)
build123d for modeling, trimesh for mesh validation,
matplotlib for rendering previews.
FDM printing: 0.4mm nozzle, 0.2mm layers, 2.4mm walls, 15% infill
unless the part bears load.
Always verify the STL is watertight before delivering it.
If pip packages are missing and there is no internet access, say so
clearly and explain that the environment setup script needs
pip install build123d trimesh matplotlib added (a one-time fix his
brother handles).
