import json

import numpy as np
import pytest

from colordle_solver import Solver, load_colors
from colordle_solver import solver as solver_mod

# A small random list keeps these tests fast; the real list takes ~20s to search.
RNG = np.random.default_rng(42)
NAMES = [f"Color {i}" for i in range(300)]
HEXES = ["#%02x%02x%02x" % tuple(RNG.integers(0, 256, 3)) for _ in NAMES]


@pytest.fixture
def small():
    return Solver(NAMES, HEXES, seed=0)


def test_bundled_list_has_a_matching_opener():
    # Fails if colornames.json changed without running scripts/build_openers.py
    s = Solver(*load_colors(bundled=True))
    cache = solver_mod._read_cache(solver_mod.BUNDLED_OPENERS)
    assert s.fingerprint in cache, "run: python scripts/build_openers.py"
    assert s.lookup(cache[s.fingerprint]) is not None


def test_first_suggestion_is_the_opener(small):
    assert small.suggest() == small.opening_guess()


def test_opener_is_computed_once_then_cached(small, monkeypatch):
    first = small.opening_guess()
    assert solver_mod.opener_cache_path().exists()

    def fail(*a, **k):
        raise AssertionError("should have used the cache")

    monkeypatch.setattr(Solver, "compute_opening_guess", fail)
    assert Solver(NAMES, HEXES).opening_guess() == first


def test_changed_list_does_not_reuse_old_opener(small):
    small.opening_guess()
    other = Solver(NAMES[:-1], HEXES[:-1])
    assert other.fingerprint != small.fingerprint


def test_broken_cache_file_is_ignored(small):
    path = solver_mod.opener_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert small.opening_guess() == small.compute_opening_guess()
    assert json.loads(path.read_text("utf-8"))  # rewritten with a valid cache
