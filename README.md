# colordle-solver

Suggests guesses for [Colordle](https://colordle.ryantanen.com/) based on the scores your earlier guesses got.

## How it works

Colordle scores a guess as `|100 − ΔE2000|`, where ΔE2000 is the CIEDE2000 color difference. The solver starts with every color in the list. After each guess it drops any color that would not have produced the score you saw, then suggests the guess expected to leave the fewest colors. Most games take 3 to 6 guesses.

## Install

```
pip install .            # or: pip install -e ".[test]" for development
```

## Use

```
colordle                       # play along: type each score the game gives you
colordle --simulate 20         # test on random answers
colordle --calibrate game.json # compare predicted scores with a real game
```

### Gettting the latest color list

The package ships with a copy of the list. To download the newest one from the color-name API:

```
colordle-update                  # saves it to your user data folder
colordle                         # now uses the downloaded list automatically
colordle --bundled               # go back to the shipped list for one run
colordle-update -o mylist.json   # or save it somewhere else and pass it in
```

The downloaded lists is saved to `%LOCALAPPDATA%\colordle-solver\colornames.json` on Windows and `~/.local/share/colordle-solver/colornames.json` elsewhere. Delete that file to go back to the bundled list for good. If a download fails, your existing list is left as it was.

To report a guess you chose yourself, type `Color Name = 72.4`.

From Python:

```python
from colordle_solver import Solver

s = Solver.from_bundled()
g = s.suggest()
s.record(g, 63.2)
print(s.remaining[:10])
```

## Opening guess

The best first guess is the same every day for a given list, so it is worked out once and cached. The bundled list's opener (Cosmic Void) ships in `data/openers.json`, and `colordle-update` works out the opener for each list it downloads. If you replace the bundled list, run `python scripts/build_openers.py` (about 40 seconds) to regenerate it. A test fails if you forget.

## Credits

The color list comes from [meodai/color-names](https://github.com/meodai/color-names) (MIT licence, © 2017 David Aerne). Its licence is in `src/colordle_solver/data/LICENSE-color-names`.
