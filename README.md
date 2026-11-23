# colordle-solver

[![PyPI](https://img.shields.io/pypi/v/colordle-solver)](https://pypi.org/project/colordle-solver/)
[![Python](https://img.shields.io/pypi/pyversions/colordle-solver)](https://pypi.org/project/colordle-solver/)

A command-line helper for [Colordle](https://colordle.ryantanen.com/), the daily color-guessing game. Tell it the score each guess got, and it suggests the next guess. It usually finds the answer in about 4 guesses.

## Install

```
pip install colordle-solver
```

Needs Python 3.9 or newer. Works on Windows, macOS, and Linux.

## Quick start

Run `colordle`, play the suggested color in the game, then type the score it gave you:

```
$ colordle
Using color list: .../colordle_solver/data/colornames.json
32004 possible colors.
After each guess, type the % score the game gave (e.g. 72.4).
To report your OWN guess instead, type: Color Name = 72.4

Suggested guess: Cosmic Void (#090533)  [32004 left]
> 44.95
Suggested guess: Moss (#009051)  [565 left]
> 29.71
Suggested guess: ...
```

Keep going until the game shows 100%, then type `100`. The first suggestion is always the same, but later ones can vary slightly between runs. If you'd rather play a color of your own choosing, enter it as `Color Name = 72.4` and the solver will still use the result.

## How it works

Colordle scores a guess as `|100 − ΔE2000|`, where ΔE2000 is the CIEDE2000 color difference, a measure of how different two colors look to the eye. The solver starts with every color in the list as a possible answer. After each guess it, it removes every color that couldn't have produced the score you saw. It then picks the guess expected to leave the fewest possibilities.

The best first guess is always the same for a given list, so it's worked out once and saved. For the bundled list it's **Cosmic Void**, a near-black.

## Results

Tested by playing a game against all 32004 colors in the bundled list:

| Guesses | Number of games |
|--------:|----------------:|
| 1       | 1 (0.0%)        |
| 2       | 32 (0.1%)       |
| 3       | 3,598 (11.2%)   |
| 4       | 23,242 (72.6%)  |
| 5       | 4,077 (12.7%)   |
| 6       | 693 (2.2%)      |
| 7       | 212 (0.7%)      |
| 8       | 78 (0.2%)       |
| 9       | 42 (0.1%)       |
| 10      | 13 (0.0%)       |
| 11      | 9 (0.0%)        |
| 12      | 1 (0.0%)        |
| 13      | 5 (0.0%)        |
| 17      | 1 (0.0%)        |

- **Average:** 4.099 guesses (median 4)
- **Unsolved:** none
- **Hardest colors:** very bright, saturated ones such as Alien Abduction (#0cff0c, 12 guesses) and Tiger Moth (#f8f2dd, 13 guesses). Many colors in the list sit very close to them, so a single score can't tell them apart. The worst color was Green Screen (#22ff00) with 17 guesses.

Run the benchmark yourself with `colordle --benchmark` (see below).

## Comands

### `colordle`

| Command | What it does |
|---|---|
| `colordle` | Play along with today's game |
| `colordle --simulate 20` | Play 20 games against random answers |
| `colordle --benchmark` | Play a game against every color and report  the results |
| `colordle --calibrate game.json` | Compare the solver's predicted scores with a real game |
| `colordle --bundled` | Use the list shipped with the package, even if you've downloaded a newer one |
| `colordle mylist.json` | Use a color list from a file |
| `colordle --tolerance 1.0` | Allow a bigger gap between predicted and real scores (default 0.6) |

### `colordle-update`

Downloads the latest color list from the [color-name API](https://github.com/meodai/color-name-api). `colordle` then uses it automatically.

```
colordle-update                          # download and install the latest list
colordle-update --file colors-api.json   # install a list you downloaded yourself
colordle-update -o mylist.json           # save it somewhere else instead
```

The list is saved to `%LOCALAPPDATA%\colordle-solver\` on Windows and `~/.local/share/colordle-solver/` on macOS and Linux. Delete `colornames.json` there to go back to the bundled list. If a download fails, your existing list is left as it was.

### Benchmark options

```
colordle --benchmark                  # every color (10-40 minutes, depending on your CPU)
colordle --benchmark --sample 1000    # quick estimate from 1,000 random colors
colordle --benchmark --workers 4      # limit how many CPU cores it uses
colordle --benchmark --fresh          # start over instead of resuming
```

Each result is saved to `benchmark.csv` as soon as it finishes (change this with `--out`), so you can open it in a spreadsheet. If you stop a run with Ctrl+C, the same command continues where it left off. Use `--fresh` after changing the solver, so old and new results don't get mixed.

## Using it from Python

```python
from colordle_solver import Solver

s = Solver.from_bundled()
guess = s.suggest()
print(s.names[guess])          # Cosmic Void
s.record(guess, 44.95)         # the score the game gave
print(len(s.remaining), "colors left")
print(s.names[s.suggest()])    # next guess
```

## Development

```
git clone https://github.com/joebutc/colordle_solver
cd colordle-solver
pip install -e ".[test]"
python -m pytest
```

Tests run automatically on Windows and Linux for every push.

- **Changing the bundled list:** if you replace `src/colordle_solver/data/colornames.json`, run `python scripts/build_openers.py` to work out its opening guess (about 40 seconds). A test fails if you forget.
- **Releasing:** bump `__version__` in `src/colordle_solver/__init__.py`, push, then publish a GitHub release tagged with the same version. The release workflow tests, builds, and uploads it to PyPI.

## Credits

Color names come from [meodai/color-names](https://github.com/meodai/color-names) (MIT licence, © 2017 David Aerne). Colordle is made by Ryan Tanen; this project isn't affiliated with it.
