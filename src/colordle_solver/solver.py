"""Candidate-elimination solver for Colordle."""
import hashlib
import json
import os
from importlib.resources import files
from pathlib import Path

import numpy as np

from .color import hex_to_rgb, rgb_to_lab, score
from . import update


def user_data_dir():
    return update.user_data_dir()   # looked up each call, so tests can redirect it


def user_list_path():
    return update.user_list_path()


OPENER_POOL = 3000          # guesses tried when working out the opening guess
OPENER_CACHE_VERSION = 2    # bump if the scoring or rating method changes
BUNDLED_OPENERS = files("colordle_solver") / "data" / "openers.json"


def opener_cache_path():
    return user_data_dir() / "openers.json"


def _read_cache(path):
    """Cached openers as {fingerprints: color name}; empty if missing or broken."""
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_cache(path, data):
    """Best effort: a cache that can't be saved just means recomputing next time."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except OSError:
        pass


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
    guess_pool:      how many guesses to try each turn (bigger = smarter, slower)
    """

    def __init__(self, names, hexes, tolerance=0.6,
                 guess_pool=400, seed=None):
        self.names = np.array(names)
        self.hexes = np.array(hexes)
        self.labs = rgb_to_lab(hex_to_rgb(hexes))
        self.alive = np.arange(len(names))
        self.index = {n.lower(): i for i, n in enumerate(names)}
        self.tolerance = tolerance
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
        keep &= self.alive != guess_idx             # a guess under 100% isn't the answer
        self.alive = self.alive[keep]
    
    def suggest(self):
        """Index of the guess expected to leave the fewest candidates."""
        if len(self.alive) == 0:
            raise ValueError("No colors fit the recorded scores.")
        if len(self.alive) <= 2:
            return int(self.alive[0])
        if len(self.alive) == len(self.names):
            return self.opening_guess()             # nothing guessed yet
        half = self.guess_pool // 2
        pool = list(self.rng.choice(self.alive, min(half, len(self.alive)), replace=False))
        pool += list(self.rng.choice(len(self.names), half, replace=False))
        return self._best_of(pool)

    @property
    def fingerprint(self):
        """Identifies this color list + settings, so a cached opener is only
        reused when it would still be the right answer."""
        h = hashlib.sha256()
        h.update(f"v{OPENER_CACHE_VERSION}|{self.tolerance}|".encode())
        for n, x in zip(self.names, self.hexes):
            h.update(f"{n}\t{x}\n".encode("utf-8"))
        return h.hexdigest()

    def opening_guess(self):
        """
        The best first guess is the same every day, so work it out once (with a
        much bigger search than later turns) and cache it.
        """
        fp = self.fingerprint
        for path in (opener_cache_path(), BUNDLED_OPENERS):
            name = _read_cache(path).get(fp)
            if name is not None and self.lookup(name) is not None:
                return self.lookup(name)
        best = self.compute_opening_guess()
        cache = _read_cache(opener_cache_path())
        cache[fp] = str(self.names[best])
        _write_cache(opener_cache_path(), cache)
        return best

    def compute_opening_guess(self, pool_size=OPENER_POOL):
        """Search a large, fixed sample of colors for the best first guess."""
        rng = np.random.default_rng(0)               # fixed, so results are repeatable
        n = len(self.names)
        pool = rng.choice(n, min(pool_size, n), replace=False)
        return self._best_of(pool)

    def expected_remaining(self, g):
        """
        Average number of candidates that would still be possible after
        guessing g, assuming each candidate is equally likely to be the answer.
        Uses the same tolerance as record(), so it never counts a split that
        the filter can't actually make.
        """
        p = score(self.labs[g], self.labs[self.alive])
        ps = np.sort(p)
        tol = self.tolerance
        counts = (np.searchsorted(ps, p + tol, side="right")
                  - np.searchsorted(ps, p - tol, side="left")).astype(float)
        hit = np.flatnonzero(self.alive == g)
        if hit.size:                                # g itself is a candidate:
            counts -= np.abs(p - p[hit[0]]) <= tol  # a wrong guess removes itself
            counts[hit[0]] = 0                      # and it it's right, we've won
        return counts.mean()
    
    def _best_of(self, pool):
        """Of the guesses in pool, the one expected to leave the fewest candidates."""
        best, best_cost = None, None
        for g in pool:
            cost = self.expected_remaining(int(g))
            if best_cost is None or cost < best_cost:
                best, best_cost = int(g), cost
        return best
