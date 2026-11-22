"""Candidate-elimination solver for Colordle."""
import json
from importlib.resources import files
from pathlib import Path

import numpy as np

from .color import hex_to_rgb, rgb_to_lab, score
from .update import user_list_path


def default_list_source(bundled=False):
    """
    Which list `load_colors()` uses when no path is given: the one saved by
    `colordle-update` if it exists, otherwise the copy shipped in the package.
    """
    user = user_list_path()
    if not bundled and user.exists():
        return user
    return files("colordle_solver") / "data" / "colornames.json"


def load_colors(path=None, bundled=False):
    """
    Return (names, hexes) from a color file, or the default list.
    
    Accepts either the plain list from the color-name-list package
    ([{"name": ..., "hex": ...}, ...]) or the API's response
    ({"colors": [...]}, from https://api.color.pizza/v1/).
    Set bundled=True to ignore any list downloaded by `colordle-update`.
    """
    source = default_list_source(bundled) if path is None else Path(path)
    with source.open(encoding="utf-8-sig") as f:    # -sig: also accept files with a BOM
        text = f.read()
    data = json.loads(text)
    if isinstance(data, dict):
        data = data["colors"]
    return [c["name"] for c in data], [c["hex"] for c in data]


class Solver:
    """
    Tracks which colors could still be the answer and suggests guesses.

    tolerance:       how far a predicted score may be from the real one
                     before a candidatet is ruled out (the game rounds scores)
    bucket_decimals: precision used when grouping candidates to rate a guess
    guess_pool:      how many guesses to try each turn (bigger = smarter, slower)
    """

    def __init__(self, names, hexes, tolerance=0.6, bucket_decimals=0,
                 guess_pool=400, seed=None):
        self.names = np.array(names)
        self.hexes = np.array(hexes)
        self.labs = rgb_to_lab(hex_to_rgb(hexes))
        self.alive = np.arange(len(names))
        self.index = {n.lower(): i for i, n in enumerate(names)}
        self.tolerance = tolerance
        self.bucket_decimals = bucket_decimals
        self.guess_pool = guess_pool
        self.rng = np.random.default_rng(seed)

    @classmethod
    def from_bundled(cls, **kwargs):
        return cls(*load_colors(), **kwargs)

    @property
    def remaining(self):
        """Names of colors hat could still be the answer."""
        return list(self.names[self.alive])

    def lookup(self, name):
        """Index of a color by name (case-insensitive), or None."""
        return self.index.get(name.strip().lower())

    def record(self, guess_idx, observed):
        """Keep only candidates whose predicted score matches the real one."""
        pred = score(self.labs[guess_idx], self.labs[self.alive])
        keep = np.abs(pred - observed) <= self.tolerance
        keep &= self.alive != guess_idx
        self.alive = self.alive[keep]
    
    def suggest(self):
        """Index of the guess expected to leave the fewest candidates."""
        if len(self.alive) == 0:
            raise ValueError("No colors fit the recorded scores.")
        if len(self.alive) <= 2:
            return int(self.alive[0])
        half = self.guess_pool // 2
        pool = list(self.rng.choice(self.alive, min(half, len(self.alive)), replace=False))
        pool += list(self.rng.choice(len(self.names), half, replace=False))
        alive_set = set(self.alive.tolist())
        cand = self.labs[self.alive]
        best, best_cost = None, None
        for g in pool:
            buckets = np.round(score(self.labs[g], cand), self.bucket_decimals)
            _, counts = np.unique(buckets, return_counts=True)
            cost = (counts ** 2).sum() / len(cand)  # expected candidates left
            if g in alive_set:
                cost -= 0.5                         # small bonus: it might win outright
            if best_cost is None or cost < best_cost:
                best, best_cost = int(g), cost
        return best
