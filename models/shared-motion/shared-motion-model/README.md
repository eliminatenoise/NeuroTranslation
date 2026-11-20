# One model for wrist movement and a rat on a track

Give NeuroTranslate 0.0 five observations from a moving point. It predicts how many centimetres separate the last observation from the position roughly a quarter-second later. One set of attention weights reads both kinds of movement. A small final layer converts the result for the instrument that made the recordings.

A headset followed a human right wrist in three dimensions. A camera followed the location of one rat in two dimensions during repeated trips on a W-shaped track. Both instruments can measure the straight-line distance between two positions in their own frame. A change in the direction of the laboratory axes leaves that distance intact. The forecast contains no direction of travel, limb command or measured neural activity. [Sources and recording credits](../shared-motion-data/NOTICE.md)

## Try it

Extract the whole ZIP. Open the launcher for Windows, macOS or Linux from the outer folder with Python 3 and NumPy installed. It runs the fitted model twice and prints a distance in centimetres for each of two invented movements. Run the same two examples from the outer folder.

```sh
python shared-motion-model/run_examples.py
```

The wrist example produces **0.524102 cm**. The rat example produces **1.010150 cm**. Each example includes the five positions, their actual times, the four intervals supplied to the model and the reference output. Neither has a measured future position. To run a batch of admitted motion intervals, supply its JSON path to the prediction script. [Example inputs](reference-examples.json) · [Inference](predict.py) · [Weights](shared-weights.npz)

```sh
python shared-motion-model/predict.py shared-motion-model/reference-examples.json
```

## Does sharing help?

We fitted the same small network separately on each dataset, then fitted it on both together. The deployed checkpoint was chosen by seed before scoring. Every cell below gives mean absolute error in centimetres. We first averaged within each recording group or rat trip, then gave each group or trip the same weight.

| Forecast | Wrist, 6 recording groups | Rat, 9 trips |
| --- | ---: | ---: |
| Stay at the last point | 2.127 | 2.870 |
| Continue at the last observed speed | 2.561 | 1.209 |
| Linear fit to distance | 2.155 | 1.184 |
| Linear fit to log distance | 1.922 | **1.119** |
| Attention on one dataset, matched examples from that dataset | 1.782 | 1.342 |
| Attention on one dataset, matched total training examples | 1.759 | 1.388 |
| **Shared attention** | **1.725** | **1.310** |

The human wrist is the case where the shared model beat the physical and linear forecasts. On the rat track, the linear model had the lowest error, and simply extending the last observed speed also beat shared attention. We scored 583 wrist windows and 106 rat windows. The human recording groups have been used in an earlier study. The nine rat trips come from a single previously examined recording. The comparison says little about a different person, animal or task. [All aggregate errors and comparisons](summary.json)

Adding rat examples reduced wrist error by 0.057 cm against the single-dataset model that saw the same wrist examples. Resampling the six recording groups gave a 95% interval from −0.142 to +0.003 cm for the change in error. Adding wrist examples reduced rat error by 0.032 cm, with an interval from −0.081 to +0.011 cm when neighbouring trips were resampled together. In both cases the interval includes zero. The comparison that matched the total number of training examples favoured the shared checkpoint on both datasets, but one of the other two seeds reversed that comparison for the wrist. Neither dataset met the rule we set in advance for evidence of positive transfer. [Decision rule](protocol.json) · [Results across all three seeds](summary.json)

## What enters the model

The inputs are five distinct observations spanning a nominal second in a single recording. For each of four intervals, the model sees distance travelled in a straight line, actual elapsed time, age of the final observation at its requested time, two-step straight-line distance and the cosine of the change in direction. It also receives a speed-derived length over 250 ms. The timestamps come from originating hand readings or from the rat recording's own clock. Each observation must be available by the requested time and at most 50 ms old. Tracking gaps, conflicting clocks or an unavailable endpoint can exclude an example. The actual time between the measured endpoints can range from 200 to 300 ms. An offline capture timestamp gives no guarantee about when a live device would deliver a sample. [Exact data and clock contract](../shared-motion-data/contract.json)

For new inputs, keep positions in one instrument frame throughout, in centimetres. Wrist histories have three axes and rat histories have two. Use `history_tokens(positions_cm, history_s, cutoff_s)` after applying the appropriate tracking and source-clock checks. It returns four rows in time order. Supply these to `forecast(x, domains, checkpoint)`, with one `"wrist"` or `"rat"` label per row of the batch. The checkpoint contains 5,234 float32 parameters. It stores one encoder and two output rows. Domain identity enters only at the output. The input representation was set from physical quantities before fitting. [Geometry](../shared-motion-data/features.py) · [Source-window checks](../shared-motion-data/prepare.py) · [Network](network.py)

## Reproduce the comparison

The archive includes all 15 fitted attention comparisons, the domain-specific linear fits, sampling receipts and restoration scripts for the pinned source recordings. Only aggregate accuracy is distributed. Rebuilding from the publisher sources creates recording-linked data locally. [Reproduction commands](REPRODUCE.md) · [Credits and licences](NOTICE.md)
