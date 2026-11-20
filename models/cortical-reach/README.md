# Can earlier sensory spikes improve a handle forecast?

A macaque held a handle while an apparatus pushed the arm. A later visual cue prompted a reach. The source contains handle positions, arm-marker trajectories and neural spike counts from area 2 of the sensory cortex during the same original trials. The models forecast how far the handle moves in the next 100 ms. The two outputs refer to the encoder’s X and Y axes, in centimetres.

On 778 matched examples from 105 later originals, the Transformer with spikes averaged 0.6044 cm of endpoint error. A model trained with the same budget on the handle and available cues averaged 0.4974 cm. Using an earlier matched trial’s spikes gave no clear difference from correctly paired spikes. The models, simpler alternatives, failure cases and eligibility counts are included. [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/cortical-reach/) · [Try both models](https://eliminatenoise.github.io/NeuroTranslation/cortical-reach/) · [Rotate the measured marker paths](https://eliminatenoise.github.io/Interoceptomics/cortical-reach/)

## Run one forecast

Extract the entire training ZIP and open the launcher for your operating system to start the offline reader, or open **reader/index.html**. For a machine-readable forecast, run either command from this package directory. Each accepts the same weights and synthetic input and prints the forecast displacement.

```sh
node launch.mjs fit/out/weights-all-17.json fit/synthetic-history.json
python fit/predict.py fit/out/weights-all-17.json fit/synthetic-history.json
```

The trained models take five 40-ms intervals. Each contains handle position and change, completed spike counts for the 30 named putative units, and flags and directions for task events that occurred before its end. A hidden cue has zero direction components. The separate marker model also takes the 3D hand and ulna endpoints and their changes. It predicts the very same 2D encoder target. [Neural input specification](fit/README.md) · [Data preparation](source/README.md) · [Landmark model design](landmarks/DESIGN.md)

## Repeat the experiment

Run the [source reader](source/README.md) on the selected public MAT member. The frozen split keeps each original trial’s two events together. Rebuild the [eighteen neural fits](fit/README.md) and run the [matched comparisons](score/README.md). To reproduce the secondary marker study from the package root, fit only on the earlier block. Apply the resulting weights unchanged to the later blocks.

```sh
python landmarks/landmarks.py train source/train.npz landmark-weights.json
python landmarks/landmarks.py score source/validation.npz landmark-weights.json --output validation-landmarks
python landmarks/landmarks.py score source/test.npz landmark-weights.json --output test-landmarks
```

Thirty positive-sort-code columns and 52 other spike-count columns were present. The primary study used the former. The published position traces were processed offline. This comparison cannot establish accuracy on another animal or day, the source of each spike, or live decoder latency. [Source and reuse](NOTICE.md)
