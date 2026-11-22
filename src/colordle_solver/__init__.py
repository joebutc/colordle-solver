"""Colordle solver: narrows down the daily color from your guesses' scores."""

from .color import ciede2000, rgb_to_lab, score
from .solver import Solver, load_colors

__version__ = "0.1.0"
__all__ = ["Solver", "load_colors", "score", "ciede2000", "rgb_to_lab", "__version__"]
