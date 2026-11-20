# From a muscle signal to a pedal reading

A seated volunteer tries to lift the forefoot against a fixed pedal. An electrode measures electrical activity over the tibialis anterior on the front of the shin. A load cell under the pedal produces a second electrical output. This model estimates how much that output will change over the next 100 sample positions after seeing the preceding 201 observations. The study reports a simultaneous 1 kHz acquisition, so the horizon is nominally 100 milliseconds. Some original files include time vectors and some use time labels derived from sample order. [Open the shared model](https://eliminatenoise.github.io/NeuroTranslation/shared-pedal-load/) · [See the recording and the platform](https://eliminatenoise.github.io/Interoceptomics/pedal-load/)

## Change the muscle signal

Open **index.html** in a browser. Keep the pedal trend fixed and move the muscle-burst control. The models that use muscle activity can give different forecasts. The response model uses two running averages of rectified muscle voltage. At the cutoff, it predicts a load change toward a fitted level. Those rates are modelling choices; the experiment did not measure a muscle activation time constant.

To run a forecast in Python, start in the package directory containing `predict.py`, install NumPy and run:

```sh
python predict.py pedal_load/example.json
```

Use the `pedal_load` domain. All modes take 201 `load` readings from earliest to latest. `recent` repeats the change over the previous 100 samples; `hold` assumes no change. `setting_median` uses the typical training change for the supplied setting. The setting must be the original category `angle0` or `angle5`. The latter is distinct from `angle_5`; anatomical direction is unverified.

| Modes | Additional inputs |
| --- | --- |
| `hold`, `recent`, `shared_load_no_setting` | None |
| `setting_median`, `linear_load`, `shared_load`, `relaxation_setting` | Setting |
| `linear_both`, `shared_both`, `random_both`, `relaxation_emg` | Setting and 201 corresponding `emg` readings |

The output gives the signed change and later load reading on the same native acquisition scale. The paper describes measuring a calibration gain using known weights. That gain is missing from the source evidence available for these trials. The 0.1 m platform lever can turn a calibrated force into a net ankle moment; it cannot convert an uncalibrated voltage directly into newton-metres. A joint moment does not identify one muscle’s force.

## What the independent recordings support

Two people supplied the eight training recordings. When the two other participants' records were opened, one neutral trial contained two columns labelled as the right load channel, with no verified 1 kHz clock for either. The registered two-person test for an EMG advantage **remains incomplete**. The other seven trials support the following separate descriptions. The model was fixed before the assessment, and no person or trial replaced the missing comparison.

* For the person with both settings and both repetitions, the load-and-setting model averaged 0.0434 error across 272 windows. Adding matched EMG gave 0.0437, versus 0.0505 with the other trial’s signal.
* For the other person’s angle5 pair, the corresponding errors over 116 windows were 0.1023, 0.1533 and 0.1542.
* For the single usable neutral recording, load and setting averaged 0.0969 error and adding muscle voltage gave 0.1506 over 58 windows. The other-trial comparison is unavailable.

For the three qualified recordings from that second participant, the authors’ stored 1 kHz time, EMG and right-load arrays equal every tenth row of their 10 kHz originals. For the wrong-input comparison the same fitted shared model keeps each recipient's pedal history and uses the EMG history at proportionate rank in the other completed trial at that setting. The task-trained Transformer uses the same original cutoff index. These retrospective comparisons never enter a live input. With one person in each descriptive group, differences do not establish a general benefit or a physiological cause. [Qualified group results](assess-summary.json) · [Paper and all comparators](https://eliminatenoise.github.io/NeuroTranslation/papers/pedal-load/)

## Reproduce the fit and the qualified descriptions

Run the [original acquisition reader and assessment adapter](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/pedal-load) on the declared Task 1 sources. In the main CPU package, run `python pedal_load/study.py fit DATA_DIRECTORY FIT_OUTPUT` to regenerate the readouts from the development files and their source receipts. The complete, strict `study.py assess` path cannot score the planned two-person roster with the source files as released. Run `python pedal_load/describe.py DATA_DIRECTORY OUTPUT_DIRECTORY` for the verified descriptive groups in this package. These use the same fitted readouts and include every supported trial. [Frozen design](DESIGN.md) · [Source clock details](CLOCK.md)

The shared encoder is the original movement encoder, frozen. A fitted linear readout corrects the recent load change; linear and random-encoder comparisons use the same inputs. The independent directly trained Transformer is available in its [own reader](https://eliminatenoise.github.io/NeuroTranslation/pedal-load/). This model package includes coefficients, aggregate results and an invented example. Zhang, Hakam, Akinniyi, Iyer, Bao and Sharma released the AnkleImage dataset under CC BY 4.0. [Data and licence](https://doi.org/10.6019/S-BIAD1482) · [Original article](https://doi.org/10.1038/s41597-024-04285-x)
