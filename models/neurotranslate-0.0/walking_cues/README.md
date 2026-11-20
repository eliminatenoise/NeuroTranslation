# Which way is forward?

A walker crosses a laboratory in one direction, then turns and crosses it the other way. Which part of the next step depends on the way the cameras face? This reader sets forward from the walker’s last 200 milliseconds of travel. It forecasts where the pelvis and the right heel will go over the next 100 milliseconds. Both forecasts use millimetres. [Open the offline reader](index.html) · [Watch the two recorded walks](https://eliminatenoise.github.io/Interoceptomics/walking-instructions/)

Open **index.html**, turn the heading control, then change the output axes from the walker’s to the laboratory’s. The same invented movement produces the same forecast in the walker’s coordinates. The laboratory coordinates turn with the walk. Change the instruction while keeping the movement fixed to compare two requests used in the original experiment, “as usual” and “fast but not running”. The words apply to whole recordings. There is no recording of speech or its arrival time.

## Use measured positions

Run `python predict.py walking_cues/example.json` from the folder containing `predict.py`, with NumPy installed. The example contains an invented history. To supply your own, use 21 consecutive camera frames at 100 Hz in `history_mm`. Each frame contains a pelvis XYZ position followed by a right-heel XYZ position, in millimetres with Z up. In the source, the pelvis is the average of four skin markers over the hip bones. Do that averaging before sending the two positions. The clock starts at the first of the two annotated right foot strikes. Set `offset_frames` to 10, 20, 30 or 40 frames after the first strike. Keep enough earlier frames for the entire history.

Choose `frame: laboratory` for original camera coordinates. The reader subtracts the final pelvis position and turns the horizontal axes using the pelvis travel during the observed history. Travel must reach 10 mm for forward to be defined here. The output contains forecast changes in forward, left and up, and also the original laboratory XYZ. The option `frame: travel` accepts coordinates already transformed by this rule. An instruction-dependent method accepts the exact phrase or its source code, 4 or 5. Motion-only methods omit the instruction field.

| Method | What it uses |
|---|---|
| `encoder_cue`, `encoder_motion` | The shared movement encoder and a fitted output, with the instruction or with it withheld |
| `linear_cue`, `linear_motion` | The same recorded movement features and a linear correction, with or without the instruction |
| `random_cue` | An untrained comparison encoder, a fitted output and the instruction |
| `pace_phase` | The most recent movement, pelvis pace and time since foot strike |
| `condition_phase_mean`, `cue_only` | An average from the fitting records or a fitted estimate based on instruction and time |
| `hold`, `repeat_100ms`, `velocity_50ms` | Stay still, repeat the last 100 ms, or extend the last 50 ms of motion |

## What did the instruction add?

In 60 walks from ten people outside the fit, the shared encoder with the correct instruction missed the pelvis by **5.63 mm** and the right heel by **7.65 mm** on average. Withholding the instruction gave **6.00 mm** and **7.98 mm**. Giving the opposite instruction to the fitted model gave **7.64 mm** and **9.45 mm**. Both landmarks met the prespecified comparison in those ten people. Neither met it across the development folds. The historical participants had already been used in earlier studies. Their recordings cannot establish how the method works with a new instruction.

The [directly trained Transformer](https://eliminatenoise.github.io/NeuroTranslation/walking-instructions/) gave lower historical errors overall. Its motion-only version was already close. That model did not establish an improvement from adding the two instructions to observed movement. Architecture and instruction benefit answer different questions. [Read the paper](https://eliminatenoise.github.io/NeuroTranslation/papers/walking-instructions/) · [Between-model comparison](historical-model-comparison.json)

## Reproduce the fit

Use the [original data reader](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/walking-instructions) to prepare the development and historical NumPy files for the licensed source. In the parent folder containing `predict.py` run:

```sh
python walking_cues/study.py fit prepared/development.npz fitted.json development.json
python walking_cues/study.py score prepared/historical.npz fitted.json historical.json
```

Each participant stays in one development fold. Each result gives equal weight to people, then instructions, repeat walks and eligible time windows. The five-fold development scores and the final model use only the 30 development people. The archived C4 and C5 movement records came from 100 Hz camera data that the source authors filtered in both time directions. A prediction on this stored clock does not establish biological processing time. [Prespecified comparison](DESIGN.md) · [Development results](development.json) · [Historical results](historical.json) · [Original study](https://doi.org/10.1038/s41597-019-0124-4) · [Version 8 data and CC BY 4.0 licence](https://doi.org/10.6084/m9.figshare.7734767.v8)
