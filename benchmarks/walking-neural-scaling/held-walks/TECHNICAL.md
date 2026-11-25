# Held evaluation of walking-force forecasts

[Simple edition](README.md) · [Exact scores](results.json) · [Download the offline models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip)

The three-pass model trained with generated sensor disruptions reduced mean absolute error in 100 ms vertical impulse from **8.793 to 1.813 N·s** under a generated 60 ms gap in muscle input. On complete inputs, the same training reduced error from **2.163 to 1.693 N·s**. Both comparisons use the continuation from the same checkpoint fitted with eight İzmir participants. The evaluation uses **863 issue times, 18 overground walks and six İzmir participants** kept out of all fitting and earlier development in this study. [İzmir recordings](https://aperta.ulakbim.gov.tr/records/286866)

## Source and time boundaries

Reuse the original whole-person assignment made from the directory in the publisher's `MoCap.zip`. The 29 participants contribute one engineering participant, 16 fitting participants, six development participants and six reserved for this evaluation. Retain the three original walking cycles per reserved person. The Belgian final group remains sealed. [Earlier working comparison and fitting details](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/walking-neural-scaling) · [Belgian gait recordings](https://doi.org/10.6084/m9.figshare.24192480.v1)

At 2,000 samples per second, compute ten past bins of 40 samples, ending immediately before each issue. Advance by 40 samples between issues. Each input uses four channels of surface electromyography, which measures voltage over muscles, and calibrated laboratory +Z force from one plate. Recover force using the recorded type 4 calibration matrix and plate orientation. For the outcome, sum the next 200 signed samples and divide by 2,000. The frame clock must contain the entire history and outcome. Every model uses the same issue keys. The baseline extends the last 20 ms force mean to 100 ms. Each recurrent checkpoint estimates a signed correction. Its forecast is `I_pred = (0.1 s) × F_last + r(x)`, where `F_last` is the last-bin mean in newtons and `r(x)` is the learned correction in N·s from the encoded history `x`.

Read only through the last admissible input cutoff when preparing a recording. Each issue uses its own earlier samples. Freeze the forecast arrays, then reopen the 18 exact files and check the stored analog readings, clock and calibration with two C3D readers. All histories reproduced. Their largest calibrated force difference was `2.28 × 10⁻¹³ N` or less. Summing the native force or summing pair-averaged samples at 1 kHz agreed within `2.85 × 10⁻¹⁴ N·s`. One file contained an extra all-zero 512-byte block after its declared data. All eligible targets lay in the declared frames.

## Inputs and comparison

The five features per bin are force divided by 800 N, the median and 80th percentile of channel changes, and two availability indicators for force and muscle. A channel change is `log(1 + RMS_now / RMS_previous)`, with the preceding bins supplying `RMS_previous` and at least three required. RMS is the square root of the mean squared voltage. The initial three bins mark the muscle summaries as unavailable. Use recording, person and lab identifiers only for grouping the analysis.

Use the previously designated seed **20261124**. The frozen model has a width of 24 and repeats a shared recurrent calculation. Its three-pass starting fits used 12 Belgian people plus **0, 4, 8 or 16** İzmir people at matched update counts. The one-, five- and eight-pass comparisons at the eight-person rung are separately fitted checkpoints. The two continued models start from the same weights at each rung and use the same 900 further optimizer updates and training-row draws. The augmented arm independently chooses a 20 ms shift with probability 0.15 and removal of the latest 60 ms of muscle summaries with probability 0.20 for each drawn row. Force inputs and targets are unchanged. The archived evaluation applies each disruption separately. Ridge and boosted trees receive the same force and encoded muscle histories and use the eight-person fitting rung.

| Method | Complete input | 20 ms muscle delay | Latest 60 ms of muscle input missing |
| --- | ---: | ---: | ---: |
| Extend last force mean | 7.012 | 7.012 | 7.012 |
| Ridge | 5.483 | 5.702 | 6.335 |
| Boosted trees | 3.326 | 3.676 | 4.582 |
| Eight added people, original three-pass fit | 2.676 | 4.364 | 13.769 |
| Eight added people, continued with complete input | 2.163 | 3.750 | 8.793 |
| Eight added people, continued with generated disruptions | **1.693** | **1.743** | **1.813** |
| Sixteen added people, continued with complete input | 2.002 | 2.506 | 11.285 |
| Sixteen added people, continued with generated disruptions | 1.903 | 1.845 | 2.147 |

Each entry is mean absolute impulse error in N·s. Average issue errors within each trial, weight trials equally within each person, then weight people equally. For the primary eight-person-rung comparison, augmentation reduced error by **0.470**, **2.007** and **6.980 N·s**, respectively. The paired central 95% intervals were **[0.302, 0.670]**, **[1.479, 2.594]** and **[6.054, 7.792]** across all 46,656 ordered resamples of six people with replacement. All six had lower error in each comparison. The 863 partially overlapping windows represent six independent people.

With complete input the zero-, four-, eight- and sixteen-person base fits scored **4.602, 3.064, 2.676 and 3.004 N·s**. The paired sixteen-minus-eight difference was **+0.329 N·s**, with interval **[−0.030, 0.664]**. At eight added people the 1-, 3-, 5- and 8-pass starting fits scored **3.826, 2.676, 3.074 and 3.287 N·s** on complete input. Model size and pass count should be compared again on another cohort. [All methods and paired changes](results.json)

## Run the offline model

1. Extract the whole ZIP. Use Python 3.13 and install the pinned packages in `requirements.txt`. To use a local environment, create `.venv` with `python3.13 -m venv .venv` on macOS or Linux or `py -3.13 -m venv .venv` on Windows. Install with `.venv/bin/python -m pip install -r requirements.txt` or `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
2. Run `sh "Open on Linux.sh"` or `sh "Open on macOS.command"`. On Windows, run `"Open on Windows.cmd"` from Command Prompt. The default uses an invented history and prints 100 ms forecasts in N·s for the eleven checkpoints and last-force rule. The extracted Linux launcher was run. The other launchers were checked from source.
3. Append `--input history.json` to supply ten values in `measured_plate_force_n` and ten rows of four or six RMS voltages in `emg_rms_volts`. Arrange rows oldest first. Use `null` for a missing muscle value. Pass `--model augmented_08` to run the checkpoint trained with disruptions at the eight-person rung. Use `--condition delay-muscle` or `--condition hide-muscle` to reproduce either generated disruption. The archive includes `SHA256SUMS` and uses FP32 weights and CPU inference. The fitted ridge and trees appear in the study results. The archive contains the eleven recurrent models and the last-force rule.

These data validate short forecasts of a measured plate from archived inputs under this recording setup. Most arms were fitted in both labs, so this evaluates new people at a known site. The Belgium-only fit tests transfer to a different lab. The generated conditions provide controlled input tests. Actual sensor delay, new-load probability, other movements and online use need separate measurements. The six reserve people have now been scored. Any settings chosen from these results require another evaluation set.

Project code and weights in this download are available under CC0 to the extent of our rights. The study used the original measurements released by Şenay Mihcin, Mehmet Yılmaz, Ahmet Mert Şahin and Sevinç Akdeniz under CC BY 4.0. The archive distributes the code, weights and aggregate scores. The publisher hosts the recorded data. [Dataset and attribution](https://aperta.ulakbim.gov.tr/records/286866)
