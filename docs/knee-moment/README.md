# The turning knee

Four seconds of right and left knee, hip and ankle angles go in. Two numbers come out, the estimated internal turning moments at the knees 25 stored frames later. A positive moment acts toward bending and a negative moment toward straightening. Either direction can resist the movement you see. Moment is expressed in newton-metres per kilogram of body mass. This is an offline walking experiment.

Open the launcher for Windows, macOS or Linux, or open **index.html** directly. The page includes its model and works offline. Move the slider to advance the cutoff through a mathematically generated walk. Choose a joint to see its angle history. Switching the method recomputes both moments from the same 400 frames. Open a local JSON history to try your own series. The browser displays one history per file, while Node also accepts batches.

## Run the model with Node

The example needs only Node and the files in this folder.

```sh
node predict.cjs
node predict.cjs --example-input > invented.json
node predict.cjs invented.json
```

To read JSON on standard input, pass `-` as the filename. The reusable function `require('./src/knee-moment.js').predict(record, weights)` accepts the same record and the object in `src/weights.json`. The invented example comes from `src/example.js`.

| Input | Meaning |
| --- | --- |
| `domain` | `knee_moment` |
| `mode` | `trained` task-trained residual, `shared` frozen movement encoder, `scrambled` shuffled encoder, `ridge` linear readout or `mean` training mean |
| `frames` | 400 consecutive nonnegative integer sample numbers below 2⁵³ at 100 Hz |
| `angles_deg` | 400 rows of six finite angles, in degrees. Columns are right knee, left knee, right hip, left hip, right ankle, left ankle. |

Under the source protocol any exact zero angle excludes that history. This can omit genuine zero crossings. For batches, supply one frame array and angle matrix per history. The output `internal_knee_moment_Nm_per_kg` contains one right/left pair per history, in the order given by `axes`. The matched lag `period_frames` is the smallest lag from 75 through 300 that best aligns the last 100 bilateral knee samples with an earlier sequence. A repeated pattern can yield a multiple of a stride. The output `horizon_stored_frames` is 25 and `stored_hz` is 100. Reconstruction and filtering delay during live capture is unknown.

## What the comparison found

Seven training walkers provided 3,559 windows of level treadmill walking at a nominal 0.8 m/s. Three held walkers provided 1,207 overlapping test windows. Their knee angles had been examined in an earlier angle-prediction study. The present test concerns their later knee moments. Cameras and treadmill force plates contributed to the reference moments through inverse dynamics. The predictors saw only earlier angles. A net joint moment does not determine individual muscle force or joint contact force.

The task-trained residual averaged 0.08874 N·m/kg absolute error, compared with 0.09761 for the raw linear fit and 0.09373 for matching to a training walk. It beat those comparators for two people and one person respectively. The frozen encoder averaged 0.10190 versus 0.10349 for shuffled weights and 0.09761 for the raw linear fit. Neither encoder met its requirement to win both comparisons for all three people. The trained fit learned a correction specific to this task.

When an earlier moment was available, replaying the moment from the matched earlier stride averaged 0.06785 N·m/kg versus 0.08884 for the trained model on those same 1,187 windows. This comparator needs earlier moment measurements. Matching to a training walker needs reference windows from the source. Both appear in the comparison table or explanation. The five interactive methods can run without distributing participant windows. [Complete numerical results](src/results.json) · [Source credits and rights](NOTICE.md)

## Rebuild and verify

Python 3.11 or newer and NumPy can reproduce the numeric export from the released movement checkpoint. The page builder uses the Python standard library. Both the source checkpoint and the aggregate assessment are hash-pinned. From this directory, run the following against the model in the full repository.

```sh
python export.py ../../models/neurotranslate-0.0/movement-weights.npz
python build.py
python verify.py ../../models/neurotranslate-0.0 ../../models/neurotranslate-0.0/movement-weights.npz
```

The verification compares Node with Python on invented histories in all five modes, including constant-angle lag ties, and checks invalid records. Add `--archive /path/to/Streaming.mat` to exercise three eligible earlier-angle histories for each held walker. This requires h5py and the original CC0 archive. Source rows pass directly to the process under test and the verification prints only aggregate differences. To reproduce the original fitting and assessment, use the fixed method and study in the model release. [Forecast method](https://github.com/eliminatenoise/NeuroTranslation/blob/main/models/neurotranslate-0.0/load/METHOD.md) · [Study source](https://github.com/eliminatenoise/NeuroTranslation/blob/main/models/neurotranslate-0.0/load/study.py) · [Versioned recording](https://doi.org/10.6084/m9.figshare.14558181.v1)
