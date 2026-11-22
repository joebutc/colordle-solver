import pytest

from colordle_solver import update


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """
    Point the user data folder at a temp dir so tests never read or overwrite
    the real downloaded list. Patches the function itself rather than environment
    variables, so it works the same on Windows, macOS and Linux.
    """
    data = tmp_path / "data" / "colordle-solver"
    monkeypatch.setattr(update, "user_data_dir", lambda: data)
    return data
