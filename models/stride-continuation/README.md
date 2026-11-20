# Where will the next step land?

A motion-capture lab has tracked a person walking or running for half a second. Give the model those eleven observations. It predicts the next twelve positions of the head, chest, waist, arms and legs, one every 50 milliseconds. Select the movement-only model if the action is unknown. The tagged model also takes the word *walk* or *run*. In this study that word came from a catalogue entry written about a recording. Nobody gave the participant a recorded spoken command. [Marker definitions and clock](schema.json)

## Try a measured example

With Python and NumPy installed, run the following two commands from this folder. Each writes a forecast in millimetres in the original room coordinates. The walk and run files include the corresponding measured continuation, so you can compare where the model put the foot with where the lab saw it. Both examples come from training. [Walk](example-walk.json) · [Run](example-run.json) · [Source terms](RIGHTS.md)

```sh
python forecast.py example-walk.json --out predicted-walk.json
python forecast.py example-run.json --weights history-only.json --out predicted-run.json
```

For your own input, supply a JSON object with an `action` of `walk` or `run` and a `history` containing `timesS` and `positionsMm`. Use 11 times on an uninterrupted 20 Hz clock and 18 three-coordinate sites in the published order, with the Z axis pointing up. Each output contains twelve absolute `timesS`, 18 predicted absolute `positionsMm` at each time, and the mean of the two predicted waist positions in `pelvisMm`. The movement-only model needs no action. The fitted model expects the CMU marker definitions and scale. Arbitrary camera pixels, headsets, and unrelated skeleton layouts require their own calibration and validation. [Reference inference](forecast.py) · [Schema](schema.json)

## What did it get right?

We set aside twelve further CMU walk and run recordings before fitting. All twelve supplied a measured half-second history and at least one complete 600 ms outcome. On the six source group numbers, the tagged model put a body site **69.1 mm from its recorded pelvis-relative position**, averaged over sites and future times. We first averaged the overlapping windows within each recording, then the recordings within each group, then the groups. The movement-only model scored 71.9 mm. Looking for a similar past stride in three different training recordings scored 76.9 mm. [Scoring code](assess.py) · [Full results by source group and trial](fresh-results.json)

| Forecast | Body, mean | Body, 250 ms | Body, 600 ms | Pelvis, mean | Pelvis, 250 ms | Pelvis, 600 ms |
|---|---:|---:|---:|---:|---:|---:|
| History and action | 69.1 | 62.9 | 99.6 | 66.7 | 44.6 | 133.7 |
| History only, separately fitted | 71.9 | 64.6 | 106.5 | 63.8 | 44.7 | 125.3 |
| Retrieve similar training strides | 76.9 | 74.6 | 106.3 | 73.0 | 51.5 | 154.6 |
| Weighted linear fit (ridge) | 85.6 | 77.8 | 138.9 | **59.0** | 46.5 | **111.9** |
| Hold every site still | 142.1 | 144.4 | 172.3 | 432.3 | 326.9 | 812.4 |
| Continue the last 100 ms velocity | 250.5 | 182.6 | 474.5 | 96.7 | 72.0 | 186.6 |
| Swap the two action labels at inference | 105.3 | 96.3 | 151.3 | 99.8 | 75.7 | 180.0 |
| Give the tagged model eleven copies of the last pose | 92.3 | 97.1 | 115.0 | 419.5 | 324.2 | 777.2 |

All distances are in mm. Body error removes each pose’s own pelvic translation. Pelvis error measures how far the forecast places the centre of the waist from its measured position in the room. A model can get the step right and put the pelvis in the wrong place. The linear model tracked the pelvis most closely on average and had the smaller body error on groups 38 and 39. [Twelve-point error curves and trial results](fresh-results.json)

Five fresh groups walked. Just one ran. The tagged model missed body sites by 145.6 mm for the running group, with 148.2 mm on trial 127_03. The five walking group scores ranged from 37.2 to 100.2 mm. The catalogue can assign more than one number to the same person. The 351 overlapping forecasts therefore do not amount to 351 independent people or even 351 independent strides. Using the action entry reduced mean body error in all six groups, by 0.5–6.5 mm against the movement-only fit. It cannot establish how much a prospective spoken cue would help a new runner. [Source cohort](cohort.json) · [CMU database](https://mocap.cs.cmu.edu/)

A separate check reused eight recordings already examined in an earlier locomotion study. Five of these were recorded at 60 Hz, the other three at 120 Hz. Against 830 eligible windows across their three source group numbers, the tagged model scored 75.4 mm for body position. Retrieval scored 76.1 mm, the movement-only model 76.8 mm and ridge 83.0 mm. The ridge model again had the smaller pelvic error, 72.6 versus 81.8 mm. [Earlier-group results](previous-results.json) · [Coverage](previous-coverage.json)

## What the lab saw

The 18 sites come from 23 named optical skin markers. These are processed optical positions. The stored residuals do not establish physical measurement precision. The model gets three-dimensional coordinates. The pelvis is the mean of four waist markers. Each history fixes its own heading from the two waist sites at the last observation, so the model can issue a forecast before anyone has seen the rest of the stride. It has no access to future heel separation, future direction of travel or marker readings after the cutoff. Source frames are selected directly at 20 Hz. High-frequency motion can alias during downsampling. Occlusions and missing measurements can make a forecast impossible to test. [Exact window rules](protocol.md) · [C3D preparation](prepare.py)

Fifty-eight thousand adjustable numbers describe how the eleven observations go together. A Transformer compares observed poses across time, then predicts how the body changes relative to its last pose and how the pelvis departs from its recent velocity. Both fitted Transformers have 58,182 parameters. Neither imposes fixed limb lengths or foot contact. These outputs describe an optical marker forecast for CMU walking and running. They provide no muscle voltage, nerve activity, camera images, direct joint centres, clinical assessment or demonstrated control of a real limb. [Training source](fit.py) · [Reproduction](REPRODUCE.md)
