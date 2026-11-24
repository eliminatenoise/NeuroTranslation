# Area 2, handle force and 100 ms hand displacement

The [separate-day technical report](separate-day/TECHNICAL.md) evaluates fixed and adaptive blends using a pooled Area 2 signal.

We estimated the two-dimensional difference between the archived hand positions at issue and 100 ms later. The pinned Area2_Bump source is DANDI 000127 version 0.220113.0359, asset `ded26b6c-418d-43f5-8a37-dfd072c2dbd4`. The archive describes both hand position and handle measurements on a 1 kHz clock with the same recorded start time. We converted hand x and y from archival centimetres to millimetres and used the three measured force axes in newtons. The three moment columns were excluded. [Source archive](https://dandiarchive.org/dandiset/000127/0.220113.0359) · [Primary methods](https://doi.org/10.7554/eLife.48198)

We sorted the source's 364 labelled trials by start time. The first 218 supplied fitting values, the next 72 selected the ridge penalty, and the remaining 74 supplied the held comparison. Each forecast used the previous ten 20 ms bins. We represented hand position at each bin start relative to its measured position at issue, sampled force at each bin start and counted half-open spike bins from 65 sorted Area 2 units with observation coverage. Candidate times were spaced 20 ms apart in development and 320 ms apart in the held trials. This kept the future hand positions used for scoring out of the held feature packet. All arms used the same eligible rows.

The four models fit a regularized linear map from their specified inputs to displacement. They used FP64, with means and scales determined on the fitting trials and each fitting trial weighted equally. Each selected the smallest tested ridge penalty, 0.0001, on configuration trials. The stay-put control predicted zero displacement. The constant-velocity control extrapolated the displacement from 20 ms before issue to issue for the next 100 ms. We froze 624 forecasts per arm before reading the corresponding future positions. All 624 targets were finite. Within-trial averages received equal weight in each reported group. Paired intervals use 4,000 resamples of whole trials.

| Input | Displacement vector error, mm | Displacement length error, mm |
| --- | ---: | ---: |
| Stay put | 8.018 | 8.018 |
| Constant velocity | 4.159 | 3.185 |
| Motion | 2.396 | 1.818 |
| Motion and force | 2.276 | 1.695 |
| Motion and Area 2 | 2.453 | 1.824 |
| Motion, force and Area 2 | 2.328 | 1.716 |

The paired decrease in vector error after adding force to motion was 0.121 mm (95% interval 0.041 to 0.203). The change after adding Area 2 to motion and force was a gain of −0.052 mm (95% interval −0.107 to 0.003). In descriptive strata defined by measured movement, the Area 2 gain was −0.340 mm for displacement under 2 mm (239 rows, 73 trials), −0.064 mm for 2 to under 10 mm (225 rows, 73 trials), 0.300 mm for 10 to under 20 mm (77 rows, 48 trials), and 0.563 mm for at least 20 mm (83 rows, 62 trials). The gain in the largest stratum had a 95% interval of 0.324 to 0.804 mm. Trials remain the unit of resampling because forecasts within a trial can be correlated despite the 320 ms spacing.

Groups with and without an archived centre-hold bump flag refer to whole trials. A forecast from a flagged trial can fall outside the bump period. The archive identifies position filtering at 100 Hz. Filter phase and physical inter-device delay remain unknown. The result is an archived comparison within one recording. A gate that uses forecast-time signals to choose how much to rely on Area 2 would need a separate test, since the reported movement groups use future measurements.

## Reuse the coefficients

Use Python with NumPy. The input is an NPZ with `motion` shaped `(rows, 10, 2)` in millimetres relative to issue, `force` shaped `(rows, 10, 3)` in newtons, and `counts` shaped `(rows, 65, 10)` in the source file's unit order. Order the bins from oldest to newest. Run `python infer.py inputs.npz forecasts.npz` to write one `forecasts.npz` with six named arrays of planar displacement in millimetres. For a different recording, first verify the coordinate frame, sampling clock, and correspondence of the neural rows.

Credit Felix Pei, Raeed Chowdhury, Lee E. Miller and the source contributors. The archived recording is CC BY 4.0. This folder contains fitted coefficients and aggregates. [Simple edition](README.md) · [Numerical results](results.json)
