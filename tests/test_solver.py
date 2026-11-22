import numpy as np
import pytest

from colordle_solver import Solver, load_colors, score


@pytest.fixture(scope="module")
def colors():
    # Module-scoped fixtures run before the per-test temp-folder redirect in
    # conftest.py, so always load the bundled list explicitly.
    return load_colors(bundled=True)


def play(names, hexes, answer, seed):
    s = Solver(names, hexes, seed=seed)
    for turn in range(1, 30):
        g = s.suggest()
        if g == answer:
            return turn
        s.record(g, round(float(score(s.labs[g], s.labs[[answer]])[0]), 2))
        assert answer in s.alive, "the real answer was wrongly ruled out"
    return turn


def test_bundled_list_loads(colors):
    names, hexes = colors
    assert len(names) == len(hexes) > 1000


@pytest.mark.parametrize("seed", range(5))
def test_solves_within_ten_guesses(colors, seed):
    names, hexes = colors
    answer = int(np.random.default_rng(seed).integers(len(names)))
    assert play(names, hexes, answer, seed) <= 10


def test_loads_api_format(tmp_path):
    f = tmp_path / "api.json"
    f.write_text('{"colors": [{"name": "Red", "hex": "#ff0000", "rgb": {}}], '
                 '"paletteTitle": "x"}')
    assert load_colors(f) == (["Red"], ["#ff0000"])


def test_wrong_guess_is_removed(colors):
    s = Solver(*colors, seed=0)
    g = s.suggest()
    s.record(g, 50.0)
    assert g not in s.alive
