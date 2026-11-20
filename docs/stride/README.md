# The next stride

Open **index.html** or use the launcher for Windows, macOS or Linux. The page runs two fitted transformers and a linear model directly in the browser. It carries their weights and two short training recordings. Playback, forecasting, file import and saving the page work offline.

Choose a CMU walk or run. The first eleven frames show half a second of observed movement. Time zero is the last frame the model can see. The next twelve frames show its predictions at 0.05-second intervals. The dotted blue figure marks the last observed pose. Gold points show the forecast. Select **Later recorded movement** to reveal where the markers actually went. The lines between markers are a drawing aid.

Keep the same eleven poses and change **Requested action**. Only the action label changes. To see what the poses buy on their own, select the movement-only transformer or linear model under **Comparison**. The recorded gait remains the original gait in either case. CMU assigned the labels from the recorded activities. These examples teach us about short continuations of a stride, without a spoken command or a recorded transition between gaits.

Use the time slider to move one frame at a time. With the figure focused, arrow keys rotate the camera and Home restores the original angle. **Inspect a landmark** shows absolute X, Y and Z in millimetres for each visible layer. Each trail follows that landmark. The grid lies at the lowest displayed height.

## Bring a measured window

Choose **My pose window**. Paste JSON and press **Use these coordinates**, choose a file, or drop it on the file area. **Download an example input** gives a working template with the site order, coordinate convention and source credit. The flat input has these fields.

| Field | Value |
| --- | --- |
| `action` | Exact string `walk` or `run` |
| `timesS` | 11 finite times in seconds, 0.05 s apart, on one clock |
| `positionsMm` | 11 frames × 18 named sites × 3 lab coordinates in millimetres |
| `units`, `axes`, `sampleRateHz`, `siteNames` | Optional declarations matching the downloaded example |

The site order runs from head and chest through left/right waist, shoulder, elbow, wrist, knee, ankle, heel and toe. The full order and source marker names appear on the page. Use a right-handed optical capture frame with +Z up. The two waist sites must be at least 40 mm apart horizontally at the cutoff. A source file can also keep `timesS` and `positionsMm` inside a `history` object, with `action` at the top level. A user-supplied future is ignored. The bundled CMU training examples are the only source of verified recorded overlays.

Imports stay in page memory. Changing a pasted input clears its forecast until it is applied. **Save offline copy** saves the original page, embedded weights and public examples. It excludes local coordinates and session selections.

## Results and scope

The primary comparison used 351 overlapping windows from 12 recordings in six fresh CMU catalogue groups. Only one group ran. CMU may assign the same person more than one catalogue number. The gait-conditioned transformer reached 69.1 mm average error in the 18 body sites relative to the pelvis. Its movement-only counterpart reached 71.9 mm and the linear model reached 85.6 mm. For the pelvis position in the lab, the linear model did better, 59.0 mm versus 66.7 mm for the conditioned transformer. Full per-horizon and per-group scores, the earlier assessment cohort, source hashes and scientific limits accompany the fitted model. [Model and study](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/stride-continuation)

The earlier word-only model generates from a label alone and remains available as a separate experiment. [Word-only movement](https://eliminatenoise.github.io/NeuroTranslation/word-motion/)

## Rebuild the standalone page

With NumPy and Python 3, run this command from the viewer folder in the extracted package or repository.

```sh
python -B build.py --model ../../models/stride-continuation
```

The build verifies the original network files, regression coefficients, training examples, schema, reference forecast code, protocol and fresh assessment against the pinned SHA-256 hashes. It serializes the exact fitted float32 coefficients. Browser inference uses double precision for calculations.

## Source rights

The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. CMU permits redistribution and prohibits directly reselling its data, including after conversion. The measured excerpts from 07_01 and 09_01 retain those terms. [CMU Motion Capture Database](https://mocap.cs.cmu.edu/) · [CMU data terms](https://mocap.cs.cmu.edu/faqs.php)

Original viewer code and text use CC0 1.0. The camera adapts the NeuroTranslation whole-body viewer. The fitted models and data retain their own notices. [Viewer dedication](LICENSE) · [Model and data rights](https://github.com/eliminatenoise/NeuroTranslation/blob/main/models/stride-continuation/RIGHTS.md)
