"""Command-line interface: `colordle` or `python -m colordle_solver`."""
import argparse
import json

import numpy as np

from . import __version__
from .color import hex_to_rgb, rgb_to_lab, score
from .solver import Solver, load_colors


def interactive(solver):
    print(f"{len(solver.alive)} possible colors.")
    print("After each guess, type the % score the game gave (e.g. 72.4).")
    print("To report your OWN guess instead, type:  Color Name = 72.4\n")
    while True:
        s = solver.suggest()
        print(f"Suggested guess: {solver.names[s]} ({solver.hexes[s]})  "
              f"[{len(solver.alive)} left]")
        line = input("> ").strip()
        if not line:
            continue
        if "=" in line:
            name, val = line.rsplit("=", 1)
            g = solver.lookup(name)
            if g is None:
                print("  Unknown color name, try again.")
                continue
        else:
            g, val = s, line
        try:
            val = float(val.strip().rstrip("%"))
        except ValueError:
            print("  Couldn't read that score, try again.")
            continue
        if val >= 100:
            print(f"Solved: {solver.names[g]}!")
            return
        solver.record(g, val)
        if len(solver.alive) <= 10:
            print("  Still possible:", ", ".join(solver.remaining))


def simulate(names, hexes, games, seed, tolerance):
    rng = np.random.default_rng(seed)
    turns = []
    for _ in range(games):
        s = Solver(names, hexes, tolerance=tolerance, seed=int(rng.integers(1 << 3)))
        answer = int(rng.integers(len(names)))
        for t in range(1, 30):
            g = s.suggest()
            if g == answer:
                break
            s.record(g, round(float(score(s.labs[g], s.labs[[answer]])[0]), 2))
        turns.append(t)
        print(f"answer={names[answer]!r:40} solved in {t} guesses")
    print(f"\naverage {np.mean(turns):.2f}, worst {max(turns)}")


def calibrate(names, hexes, path):
    """
    Compare predicted scores with a real game. GAME.json looks like:
      {"answer": "Fairy Tale", "guesses": [["Sky Blue", 41.2, ["Mint", 66.9]]]}
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    idx = {n.lower(): i for i, n in enumerate(names)}
    labs = rgb_to_lab(hex_to_rgb(hexes))
    a = idx[data["answers"].lower()]
    for name, real in data["guesses"]:
        pred = float(score(labs[idx[name.lower()]], labs[[a]])[0])
        print(f"{name:30} game={real:6.2f}  predicted={pred:6.2f}  diff{pred - real:+.2f}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="colordle", description="Colordle solver")
    p.add_argument("colors", nargs="?", help="colornames.json (default: bundled list)")
    p.add_argument("--simulate", type=int, metavar="N", help="play N random games")
    p.add_argument("--calibrate", metavar="GAME.json", help="check scores from a real game")
    p.add_argument("--tolerance", type=float, default=0.6)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    names, hexes = load_colors(args.colors)
    if args.calibrate:
        calibrate(names, hexes, args.calibrate)
    elif args.simulate:
        simulate(names, hexes, args.simulate, args.seed, args.tolerance)
    else:
        try:
            interactive(Solver(names, hexes, tolerance=args.tolerance, seed=args.seed))
        except (KeyboardInterrupt, EOFError):
            print()
