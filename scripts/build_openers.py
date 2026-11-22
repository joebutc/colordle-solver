"""
Regenerate src/colordle_solver/data/openers.json for the bundled color list.

Run this after replacing the bundled colornames.json, or after changing the
scoring or OPENER_CACHE_VERSION, so new installs get an instant first guess:

    python scripts/build_openers.py
"""
import json
import time
from pathlib import Path

from colordle_solver.solver import Solver, load_colors

out = Path(__file__).resolve().parent.parent / "src" / "colordle_solver" / "data" / "openers.json"

s = Solver(*load_colors(bundled=True))
start = time.time()
best = s.compute_opening_guess()
print(f"Opening guess: {s.names[best]} ({s.hexes[best]}), took {time.time() - start:.0f}s")

with open(out, "w", encoding="utf-8") as f:
    json.dump({s.fingerprint: str(s.names[best])}, f, ensure_ascii=False, indent=1)
print(f"Saved to {out}")
