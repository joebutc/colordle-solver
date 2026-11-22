import io
import json

import pytest

from colordle_solver import load_colors, update
from colordle_solver.solver import default_list_source

API_RESPONSE = {
    "paletteTitle": "x",
    "colors": [
        {"name": "Red", "hex": "#FF0000", "rgb": {"r": 255, "g": 0, "b": 0}},
        {"name": "Café au Lait", "hex": "#a67b5b"},
        {"name": "red", "hex": "#ff0001"},       # duplicate name, dropped
        {"name": "Broken", "hex": "not-a-hex"},  # malformed, dropped
        {"hex": "#123456"},                      # no name, dropped
    ],
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_api(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["headers"] = dict(req.header_items())
        seen["url"] = req.full_url
        return FakeResponse(json.dumps(API_RESPONSE).encode("utf-8"))

    monkeypatch.setattr(update.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_tests_use_temp_data_folder(tmp_path):
    # If this fails, tests/conftest.py is missing and the other tests would
    # overwrite the real downloaded color lists.
    assert tmp_path in update.user_list_path().parents


def test_clean_keeps_only_valid_name_and_hex():
    assert update.clean(API_RESPONSE) == [
        {"name": "Red", "hex": "#ff0000"},
        {"name": "Café au Lait", "hex": "#a67b5b"},
    ]


def test_clean_rejects_empty():
    with pytest.raises(ValueError):
        update.clean({"colors": []})


def test_update_saves_to_user_folder_and_solver_uses_it(fake_api, capsys):
    assert update.main([]) == 0
    assert fake_api["headers"].get("X-referrer") == "colordle-solver"
    saved = update.user_list_path()
    assert saved.exists()
    assert default_list_source() == saved
    assert load_colors() == (["Red", "Café au Lait"], ["#ff0000", "#a67b5b"])
    # --bundled still gets the shipped list
    assert len(load_colors(bundled=True)[0]) > 1000


def test_update_to_custom_output(fake_api, tmp_path):
    out = tmp_path / "mine.json"
    assert update.main(["-o", str(out)]) == 0
    assert json.loads(out.read_text("utf-8"))[1]["name"] == "Café au Lait"
    assert not update.user_list_path().exists()


def test_failed_download_keeps_old_list(monkeypatch, tmp_path):
    out = tmp_path / "list.json"
    out.write_text('[{"name": "Old", "hex": "#000000"}]', encoding="utf-8")

    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    assert update.main(["-o", str(out)]) == 1
    assert load_colors(out) == (["Old"], ["#000000"])


def test_sends_own_user_agent(fake_api):
    update.main([])
    ua = fake_api["headers"].get("User-agent", "")
    assert ua.startswith("colordle-solver/")


def test_403_explains_workaround(monkeypatch, capsys):
    def forbidden(req, timeout=None):
        raise update.urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(update.urllib.request, "urlopen", forbidden)
    assert update.main([]) == 1
    err = capsys.readouterr().err
    assert "HTTP 403" in err and "--file" in err


def test_install_from_downloaded_file(tmp_path):
    raw = tmp_path / "colors-api.json"
    raw.write_text(json.dumps(API_RESPONSE), encoding="utf-8")
    assert update.main(["--file", str(raw)]) == 0
    assert load_colors() == (["Red", "Café au Lait"], ["#ff0000", "#a67b5b"])


def test_file_with_bom_loads(tmp_path):
    f = tmp_path / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf" + b'[{"name": "Red", "hex": "#ff0000"}]')
    assert load_colors(f) == (["Red"], ["#ff0000"])
