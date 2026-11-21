# Where will the visible points go?

Put one dot on a paw and another on a nose. Keep each dot in its own slot while the animal moves. Give the model one camera frame and it returns each visible dot at its current position. Give it five frames and it can estimate how far each dot will move, using its own movement and the movement of nearby dots.

From the directory containing `predict.py`, run the two prefixes of the same invented seven-point figure. Both use Python and NumPy.

```sh
python predict.py first_use_body/frame-one.json
python predict.py first_use_body/example.json
```

Record one animal in a common 2-D view. Supply an object with four fields.

| Field | What to supply |
| --- | --- |
| `domain` | `"first_use_body"` |
| `xy` | One array per observed frame, in time order. Give each landmark a fixed slot with coordinates `[x, y]`. Use `null` for a missing point. A missing coordinate also makes the point unavailable. Keep both axes in the same units. |
| `seconds` | A strictly increasing timestamp in seconds for each frame. |
| `horizon_s` | How far beyond the last frame to forecast, in seconds. The primary evaluation used endpoints near 0.12 s and one slower recording near 0.20 s. Other positive horizons are extrapolations. |

The output gives the number of landmarks, the observation and target times, and a position in the original plane for each slot. Look beside it in `method`. If the point was missing at the last frame, its answer is `null` and its method is `unobserved`. A point visible now starts with `last_position`. To reach `learned`, it needs at least three observations in the last five frames, including the last one. Those five frames must span at most 0.96 s with no gap over 0.24 s. An older observation cannot fill a missing current point. The files below show every slot after one and five frames. [First answer](frame-one-expected.json) · [Fifth answer](expected.json)

The mixed fit learned from one mouse recording, one gerbil recording, one fly recording and two worm recordings. A new set of points uses the same coefficients from its first forecast. Point names and species labels never enter the calculation. The observations measure projected positions. A dot on the outline of a bending worm can move along the tissue even when the tracker keeps its slot. The study covered 5–49 landmarks per track. You can supply a different count, subject to the memory needed for pairwise distances.

On ten held recordings near 120 ms, mean normalized error was 0.1563 with the mixed fit, 0.1490 with its geometry features removed and 0.1959 for holding each dot still. Each recording counted equally. These outcomes describe the held recordings. How well a different camera, body or landmark definition transfers needs measurements from that setting. [Study and reproduction](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/first-use-body) · [Browser experiment](https://eliminatenoise.github.io/NeuroTranslation/first-use-body/) · [Recordings, authors and licenses](SOURCES.md) · [File provenance](provenance.json)
