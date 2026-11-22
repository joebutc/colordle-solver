import csv

import numpy as np
import pytest

from colordle_solver import Solver, benchmark

# Small random list so these run in a second or two
RNG = np.random.default_rng(7)
NAMES = [f"Color {i}" for i in range(150)]
HEXES = ["#%02x%02x%02x" % tuple(RNG.integers(0, 256, 3)) for _ in NAMES]


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_play_finds_every_answer():
    s = Solver(NAMES, HEXES)
    for answer in range(0, 150, 15):
        turns, solved = benchmark.play(s, answer, seed=answer)
        assert solved and turns <= 10


def test_benchmark_every_color(tmp_path):
    out = tmp_path / "bench.csv"
    summary = benchmark.run(NAMES, HEXES, out=out, workers=1, progress=False)
    results = rows(out)
    assert sorted(r["name"] for r in results) == sorted(NAMES)
    assert all(r["solved"] == "True" for r in results)
    assert "Average guesses" in summary and "Worst" in summary
    assert sum(r["guesses"] == "1" for r in results) == 1   # only the opener


def test_benchmark_resumes_without_repeating(tmp_path):
    out = tmp_path / "bench.csv"
    benchmark.run(NAMES, HEXES, out=out, sample=40, workers=1, progress=False)
    assert len(rows(out)) == 40
    benchmark.run(NAMES, HEXES, out=out, workers=1, progress=False)
    names = [r["name"] for r in rows(out)]
    assert len(names) == len(set(names)) == 150


def test_fresh_starts_over(tmp_path):
    out = tmp_path / "bench.csv"
    benchmark.run(NAMES, HEXES, out=out, sample=30, workers=1, progress=False)
    benchmark.run(NAMES, HEXES, out=out, sample=10, workers=1, progress=False,
                  fresh=True)
    assert len(rows(out)) == 10


def test_results_same_with_several_workers(tmp_path):
    one, two = tmp_path / "one.csv", tmp_path / "two.csv"
    benchmark.run(NAMES, HEXES, out=one, sample=40, workers=1, progress=False)
    benchmark.run(NAMES, HEXES, out=two, sample=40, workers=2, progress=False)
    key = lambda p: sorted((r["name"], r["guesses"]) for r in rows(p))
    assert key(one) == key(two)


def test_summary_picks_worst_and_best():
    data = [{"name": n, "hex": "#000000", "guesses": str(g), "solved": "True"}
            for n, g in [("Opener", 1), ("Easy", 2), ("Also Easy", 2), ("Hard", 9)]]
    text = benchmark.summarise(data, "Opener")
    worst = text.split("Worst")[1]
    assert worst.index("Hard") < worst.index("Easy")
    assert "2 color(s) take 2" in text
