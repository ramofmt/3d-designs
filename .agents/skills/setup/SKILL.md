name: setup
description: One-shot local setup for this repo on the Mac. Use when the user says "set this up here", "set up the repo", "install everything", or on a fresh checkout (no .venv yet). Installs everything locally and turns on the 3D-preview site.

# First-time setup

Make this repo fully ready to design from photos and descriptions, locally on
this Mac. You do all the work; only ask the user for the one token in step 2.

1. From the repo root, run:
       bash scripts/setup.sh
   It is safe to re-run; it skips anything already done. It installs the Python
   stack, installs the local 3D model (TRELLIS-mac) on the Mac GPU, writes .env,
   and turns on the 3D-preview website.

2. The 3D engine downloads its model from Hugging Face (free, one-time). If the
   script prints "Hugging Face: NOT signed in", ask the user — in plain language —
   to make a free account at huggingface.co, create an access token, and paste
   it; then run:
       hf auth login
   Explain it's a one-time step so the Mac can download the 3D engine.

3. Quick check (no GPU needed) — with the repo environment active
   (`source .venv/bin/activate`): build a tiny test cube with build123d, run
   `pipeline.viewer` on it, confirm the preview HTML is created, then delete the
   test files. If Hugging Face is signed in, optionally do one small photo→3D run
   to confirm the GPU path end to end.

4. Tell the user plainly that setup is done: they can now describe a part or send
   a photo, and the spinnable previews will appear at
   https://ramofmt.github.io/3d-designs/

If a step is stuck, explain in plain language what you need (usually just the
free Hugging Face token).
