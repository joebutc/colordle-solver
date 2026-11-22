import numpy as np
import pytest

from colordle_solver import ciede2000, rgb_to_lab, score


def test_ciede2000_reference_pair():
    # Sharma, Wu & Dalal (2005) test data, pair 1
    d = ciede2000(np.array([50, 2.6772, -79.7751]), np.array([[50, 0, -82.7485]]))
    assert d[0] == pytest.approx(2.0425, abs=1e-4)


def test_white_lab():
    lab = rgb_to_lab(np.array([[1.0, 1.0, 1.0]]))[0]
    assert lab == pytest.approx([100, 0, 0], abs=0.01)


def test_identical_colours_score_100():
    lab = rgb_to_lab(np.array([[0.2, 0.5, 0.7]]))
    assert score(lab[0], lab)[0] == pytest.approx(100)
