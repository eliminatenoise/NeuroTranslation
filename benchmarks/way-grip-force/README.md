# How hard will the fingers squeeze?

A thumb and forefinger squeeze a small object before lifting it. Force plates under the fingertips measure the squeeze. What does scalp EEG tell us about the force 120 ms later, once we know the cue, the recent force and how the hand and object are moving? We tested that question on stored voluntary pinch lifts from healthy adults in the WAY-EEG-GAL study. [Original experiment and measurements](https://doi.org/10.1038/sdata.2014.47)

## EEG missed the control

The fits were frozen before scoring three new people from the same study. The main comparison used 25,578 matched forecast windows from 882 trials. We calculate root mean squared error (RMSE) separately for each person and then average the three errors. Smaller is better.

| Forecast | Mean participant RMSE |
| --- | ---: |
| Continue at the last measured grip force | 0.788 N |
| Extend the recent change in grip force | 0.673 N |
| Cue and trial context | 1.426 N |
| Context, force and motion history | 0.44418 N |
| Same inputs plus aligned scalp EEG | 0.44018 N |
| Same inputs plus surface EMG | 0.45714 N |
| Same inputs plus scalp EEG and surface EMG | 0.45463 N |

The aligned EEG model gained 0.00400 N on the mechanical model. Would it still win if the EEG came from another lift? The control rotates whole EEG trials within the same person, series, weight and surface, with the same time relative to the cue. All three models in this comparison were fit and scored on matched support. On 25,578 windows, the rotated EEG model scored **0.43880 N**, below the aligned model’s **0.44018 N**. The planned test for incremental, trial-specific EEG value failed.

The small gain also disappeared in the 5,140 windows from all three people where the measured target exceeded 0.5 N. On that descriptive subset, the mechanical model scored **0.77496 N** and the aligned EEG model **0.77580 N**. The windows overlap, so the study has three development participants, even with thousands of forecasts. The final three-person test set remains reserved. [Development aggregates](DEVELOPMENT-AGGREGATE.json)

## Try four forecasts

Move the cutoff on the invented pinch lift to see what the models predict 120 ms later. Inspect the past force, motion, scalp EEG and surface EMG that change those predictions. Open a compatible local JSON window to run the same calculation in your browser. [Open the forecast](https://eliminatenoise.github.io/NeuroTranslation/grip-force/) · [Download the offline browser](WAY-EEG-GAL-grip-force-browser.zip)

## Run the desktop forecast

[Download the desktop ZIP](WAY-EEG-GAL-grip-force-experimental-preview.zip) and extract the entire folder. Open `Run-Windows.cmd`, `Run-macOS.command` or `Run-Linux.sh` for your system. You need Python 3.10 or later and NumPy. The Linux demo ran in an extracted copy. Native Windows and macOS launches remain unchecked.

The included example runs five fitted models and two formula baselines on an invented window. To forecast a compatible local recording, use the input contract and command in the ZIP’s `INFERENCE.md`. The runner expects aligned 400 ms histories, measured force and motion, and the known LED cue, series type and trial ordinal. The phase control is a study comparison that uses other trials. Actual object weight and surface enter only diagnostic comparisons and control pairing. Open `METHOD.md` in the ZIP for the fitting and comparison rules.

The 120 ms horizon belongs to the stored sample clock. Filter timing and live acquisition latency remain unverified. An EEG association also leaves muscle and motion artefacts as possible explanations. The benchmark covers offline forecasts of force measured at the plates in this recorded task.

## Check the files

From this benchmark folder, run `python verify.py` to check the Python runner and all its ZIP members against the source manifest. Run `python browser-release/build.py` to regenerate the browser's study data and offline ZIP in memory and compare both with the checked-in files. Add `--write` to write the rebuilt copies. [Source and package manifest](SOURCE.json)

The archives carry frozen model parameters, aggregate summaries and the project’s inference code. The original recordings and their licence notices are available from the data authors. [WAY-EEG-GAL collection v2](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
