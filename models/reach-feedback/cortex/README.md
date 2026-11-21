# How many spikes follow a reach?

At the second go signal of trial 90, the task cues a macaque to reach again. Five samples later, stop the clock. The model has 200 ms of hand, elbow and handle positions, spikes from 23 sorted units in somatosensory cortex, and the sequence of go signals. Can a forecast of the arm's next 100 ms help predict the spikes in the 100 ms after that?

Read the two forecasts side by side with Python 3 and NumPy.

```sh
python replay_counts.py
python replay_counts.py --family glm
```

Each row is one recorded unit. The first two numbers identify the electrode channel and the source's offline sort code. The next columns give the expected spike count from history alone and from history plus the predicted movement. The last column is the number of spikes recorded. On channel 18, sort 1, for instance, the seed-17 Transformer forecasts 4.855 spikes from history and 5.947 with the additional motion forecast. Six spikes occurred. Trial 90 helped train both count heads. This example lets you check the arithmetic. The study's held-out comparisons determine how well each approach travels to other reaches.

## Did the motion forecast help?

The direct history model performed better on the transfer reaches. Adding the movement forecast increased its mean error by 0.0100 deviance per unit (95% interval 0.0011 to 0.0185). On later reaches within the training workspace, the change was +0.0035 (−0.0232 to +0.0277). The intervals use whole original trials in contiguous blocks of eight. They compare errors in each unit's total count over ten bins, averaged over units and three fixed model seeds. Lower deviance corresponds to a closer count forecast.

Pairing each reach with the correct predicted path lowered error relative to substituting an earlier trial's predicted path in the training workspace (−0.0194, interval −0.0375 to −0.0048). In the transfer workspace the difference was −0.0033 (−0.0080 to +0.0024). The matched comparisons covered 113 reaches from 42 original trials in the first workspace and 822 from 315 in the second. The proposed advantage required improvements over both direct history and the wrong path in each workspace. Neither workspace met that criterion.

## Use another reach

`count_model.predict` takes one saved weight archive and a batch of windows in native time order. A complete 200 ms history has twenty 10 ms bins. Supply hand XYZ and ulnar marker XYZ in metres, followed by the handle's encoder XY in centimetres. The code calculates changes from the final pre-cutoff position and retains absolute position as well. Use the 23 sorted unit columns in the saved `unit_guide` order. The three cue channels contain the number of go signals recorded strictly before each bin, seconds since the latest such go (zero before the first), and an indicator that a go has occurred.

```python
import numpy as np
from count_model import predict

with np.load("example.npz") as reach, np.load("weights/transformer-full-17.npz") as head:
    rates = predict(head, pose=reach["pose"], spikes=reach["spikes"],
                    cue=reach["cue"], movement=reach["forecast"][0])
print(rates.shape)  # (1 reach, 10 bins, 23 units)
```

Each value estimates the expected spike count in one bin. Sum across the ten bins for a 100 ms forecast. For a rate in spikes per second, divide a single bin's expectation by 0.010 s. A displacement forecast must use the same eight axes, units and last-observed reference as the pose record. The example includes three motor forecasts trained on earlier original trials, one per seed, and a ridge regression forecast paired with the count regression. The fitted count weights are frozen. Production of a new displacement forecast requires the matching motor model and its training convention.

The seven fitted variants use history alone (`direct`), history plus predicted movement (`full`), predicted movement alone (`predicted_only`), earlier spikes alone (`spikes_only`), known task cues alone (`cue_only`), earlier positions and cues (`pose_cue`), or history plus the movement that actually followed (`privileged`). Only the last reads a measured future trajectory. In the paired wrong-movement test the full head receives an earlier trial's predicted path and the original reach's own history. The three Transformer seeds are 17, 41 and 73. Each regression has a log link and the same allowed input groups.

These measurements come from one animal on one day, 7 September 2017. The coordinate histories use the authors' offline processing. A lower error on later counts can establish a predictive association within the tested recordings. To establish that movement itself caused those spikes would require a different experiment. The task did not export the exact visual target location for each reach. [Chowdhury, Glaser and Miller (2020)](https://doi.org/10.7554/eLife.48198) · [CC0 data on Dryad](https://doi.org/10.5061/dryad.nk98sf7q7)
