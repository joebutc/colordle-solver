"""Colordle solver: narrows down the daily color from your guesses' scores."""

__version__ = "0.1.2"

from .color import ciede2000, rgb_to_lab, score
from .solver import Solver, load_colors

__all__ = ["Solver", "load_colors", "score", "ciede2000", "rgb_to_lab", "__version__"]
