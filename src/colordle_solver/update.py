"""Download a fresh color list from the color-name API and save a cleaned copy."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__

API_URL = "https://api.color.pizza/v1/"
REFERRER = "colordle-solver"
# Python's default "Python-urllib/3.x" is often blocked (HTTP 403) by Cloudflare,
# so say who we are instead.
USER_AGENT = f"colordle-solver/{__version__}"
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def user_data_dir():
    """Per-user folder for the downloaded list (works without admin rights)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATAT") or Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "colordle-solver"


def user_list_path():
    """Where `colordle-update` saves the list, and where the solver looks first."""
    return user_data_dir() / "colornames.json"


def fetch_raw(url=API_URL, timeout=60):
    """Download the API response and return it as parsed JSON."""
    req = urllib.request.Request(url, headers={
        "X-Referrer": REFERRER,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_file(path):
    """Load a color list you downloaded yourself (API response or plain list)."""
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def clean(data):
    """
    Turn an API response ({"colors": [...]}) or a plain list into
    [{"name": ..., "hex": ...}], dropping anything malformed.
    """
    colors = data["colors"] if isinstance(data, dict) else data
    out, seen = [], set()
    for c in colors:
        name, hexv = c.get("name"), c.get("hex")
        if not name or not isinstance(hexv, str) or not HEX_RE.match(hexv):
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({"name": name, "hex": hexv.lower()})
    if not out:
        raise ValueError("The download contained no usable colors.")
    return out


def save(colors, path):
    """Write the list, replacing any old file only once the new one is complete."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(colors, f, ensure_ascii=False)
    os.replace(tmp, path)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="colordle-update",
        description="Download the latest color list from the color-name API.")
    p.add_argument("-o", "--output", help=f"where to save it (default: {user_list_path()})")
    p.add_argument("--url", default=API_URL, help="API address to download from")
    p.add_argument("--file", metavar="JSON",
                   help="clean and install a file you downloaded yourself "
                        "(e.g. with curl) instead of downloading")
    args = p.parse_args(argv)

    out = Path(args.output) if args.output else user_list_path()
    try:
        if args.file:
            print(f"Reading {args.file} ...")
            colors = clean(read_file(args.file))
        else:
            print(f"Downloading from {args.url} ...")
            colors = clean(fetch_raw(args.url))
    except urllib.error.HTTPError as e:
        print(f"Update failed: the server answered HTTP {e.code} ({e.reason}).",
              file=sys.stderr)
        if e.code in (403, 429):
            print("It may be blocked or rate-limiting this request. Download the "
                  "list another way, e.g.\n"
                  f'  curl -H "X-Referrer: {REFERRER}" {args.url} -o colors-api.json\n'
                  "then run:  colordle-update --file colors-api.json",
                  file=sys.stderr)
        return 1
    except Exception as e:   # network, missing file, bad JSON, empty list
        print(f"Update failed: {e}", file=sys.stderr)
        return 1
    save(colors, out)
    print(f"Saved {len(colors)} colors to {out}")
    
    from .solver import Solver  # imported here to avoid a circular import
    print("Working out the best opening guess for this list (one-off, about 20 seconds).")
    s = Solver([c["name"] for c in colors], [c["hex"] for c in colors])
    print(f"Opening guess: {s.names[s.opening_guess()]}") 
    if args.output:
        print(f"Use it with:  colordle {out}")
    else:
        print("`colourdle` will now use this list automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
