"""
Play a full game against every color in the list (or a sample) and report
how many guesses the solver needs: average, spread, worst, and best colors.

Results are written to a CSV as they come in, so a long run can be stopped
with Ctrl+C and continued later by running the same command again/
"""
import csv
import multiprocessing as mp
import os
import signal
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .color import score
from .solver import Solver

MAX_TURNS = 30            # a game that reaches this counts as unsolved
FIELDS = ["name", "hex", "guesses", "solved"]


def play(solver, answer, seed=None, max_turns=MAX_TURNS):
    """Play one game with a known answer. Returns (guesses used, solved?)."""
    solver.reset(seed)
    for turn in range(1, max_turns + 1):
        g = solver.suggest()
        if g == answer:
            return turn, True
        # The game shows scores to 2 decimal places
        observed = round(float(score(solver.labs[g], solver.labs[[answer]])[0]), 2)
        solver.record(g, observed)
        if len(solver.alive) == 0:
            break                                 # shouldn't happen; counts as unsolved
    return turn, False


# worker processes: each builds the solver once, then plays many games
_worker = None


def _init_worker(names, hexes, opener, tolerance):
    global _worker
    # Let the main process handle Ctrl+C, so workers don't each print a traceback
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _worker = Solver(names, hexes, tolerance=tolerance)
    _worker.opener = opener


def _play_one(answer):
    turns, solved = play(_worker, answer, seed=answer)  # seed = answer: repeatable
    return answer, turns, solved


def read_results(path):
    """Rows already in the CSV, keyed by color name."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def summarise(rows, opener_name, top=10):
    """Text summary of a list of result rows."""
    if not rows:
        return "No results yet."
    guesses = np.array([int(r["guesses"]) for r in rows])
    unsolved = [r for r in rows if r["solved"] != "True"]
    lines = [
        f"Colors tested:    {len(rows):,}",
        f"Average guesses:  {guesses.mean():.3f}",
        f"Median guesses:   {np.median(guesses):g}",
        f"Unsolved:         {len(unsolved)} (gave up after {MAX_TURNS} guesses)",
        "",
        "Guesses needed:",
    ]
    counts = Counter(guesses.tolist())
    biggest = max(counts.values())
    for k in sorted(counts):
        bar = "#" * max(1, round(40 * counts[k] / biggest))
        lines.append(f"  {k:>2}  {counts[k]:>6,}  {100 * counts[k] / len(rows):5.1f}% {bar}")

    ordered = sorted(rows, key=lambda r: (-int(r["guesses"]), r["name"].lower()))
    lines += ["", f"Worst {min(top, len(rows))} colors:"]
    lines += [f"  {int(r['guesses']):>2}  {r['name']} ({r['hex']})" for r in ordered[:top]]

    others = [r for r in rows if r["name"] != opener_name]
    if others:
        fewest = min(int(r["guesses"]) for r in others)
        best = sorted((r for r in others if int(r["guesses"]) == fewest),
                      key=lambda r: r["name"].lower())
        lines += ["", f"Best: {opener_name} takes 1 guess (it's the opening guess). "
                      f"After that, {len(best):,} color(s) take {fewest}, e.g.:"]
        lines += [f"      {r['name']} ({r['hex']})" for r in best[:top]]
    return "\n".join(lines)


def run(names, hexes, out="benchmark.csv", sample=None, workers=None,
        tolerance=0.6, fresh=False, seed=0, progress=True):
    """
    Benchmark the solver. Returns the summary text.

    sample:  only test this many randomly chosen colors (None = all of them)
    workers: processes to use (default: all CPU cores; 1 = no extra processes)
    fresh:   ignore and overwrite an existing results file instead of resuming
    """
    out = Path(out)
    solver = Solver(names, hexes, tolerance=tolerance)
    opener = solver.opening_guess()               # cached; worked out once if needed
    opener_name = str(solver.names[opener])

    answers = np.arange(len(names))
    if sample:
        answers = np.sort(np.random.default_rng(seed).choice(
                len(names), min(sample, len(names)), replace=False))

    if fresh and out.exists():
        out.unlink()
    done = read_results(out)
    todo = [int(a) for a in answers if names[a] not in done]
    if done:
        print(f"Resuming: {len(done):,} colors already in {out}, {len(todo):,} to go.")
    workers = max(1, workers or os.cpu_count() or 1)
    if todo:
        print(f"Playing {len(todo):,} games on {workers} worker(s). "
              "Press Ctrl+C to stop; run again to continue.")
    
    new_file = not out.exists()
    f = open(out, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        writer.writeheader()

    pool = None
    start, finished, total_guesses = time.time(), 0, 0
    try:
        if workers == 1:
            _init_worker(names, hexes, opener, tolerance)
            results = map(_play_one, todo)
        else:
            pool = mp.Pool(workers, initializer=_init_worker,
                           initargs=(names, hexes, opener, tolerance))
            results = pool.imap_unordered(_play_one, todo, chunksize=20)

        last_print = 0.0
        for answer, turns, solved in results:
            writer.writerow({"name": names[answer], "hex": hexes[answer],
                             "guesses": turns, "solved": solved})
            finished += 1
            total_guesses += turns
            now = time.time()
            if progress and (now - last_print > 0.5 or finished == len(todo)):
                last_print = now
                rate = finished / (now - start)
                eta = (len(todo) - finished) / rate if rate else 0
                # The first few results come in unevenly, so wait before guessing an ETA
                eta_text = (f"ETA {int(eta // 60)}m {int(eta % 60):02d}s"
                            if now - start > 5 else "ETA ...")
                print(f"\r  {finished:,}/{len(todo):,} "
                      f"({100 * finished / len(todo):.0f}%)  "
                      f"avg {total_guesses / finished:.2f}  {eta_text}   ",
                      end="", file=sys.stderr, flush=True)
                f.flush()
        if progress and todo:
            print(file=sys.stderr)
    except KeyboardInterrupt:
        print(f"\nStopped after {finished:,} new games. Run the same command "
              "again to continue.", file=sys.stderr)
    finally:
        f.close()
        if pool is not None:
            pool.terminate()
            pool.join()

    wanted = {names[a] for a in answers}
    rows = [r for r in read_results(out).values() if r["name"] in wanted]
    return summarise(rows, opener_name)
