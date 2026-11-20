# An arm sensor, 120 milliseconds ahead

Take the last 16 readings from the accelerometer on a walker’s right arm. What will its three axes read three samples later? On two people held out from fitting, a Transformer beat the simplest forecast, repeating the last reading. A linear ridge model beat both. The Transformer therefore failed the comparison set before the assessment.

| History in time order | Windows | Repeat last reading | Ridge | Transformer |
|---|---:|---:|---:|---:|
| Both walks | 1,680 | 1.182 | **0.781** | 0.855 |
| Parking-lot walking | 840 | 1.300 | **0.830** | 0.907 |
| Flat treadmill at 4 km/h | 840 | 1.065 | **0.732** | 0.803 |

Numbers are mean absolute errors across the three axes, in the original sensor’s stored units. Lower is better. The frozen rule required the Transformer to beat both alternatives for **each** assessment person. Ridge had the lowest error for both. Shuffling the first 15 readings while keeping the last in place raised the pooled error to 1.056 for ridge and 0.957 for the Transformer. Repeating the final reading still scored 1.182. That comparison tests sensitivity to order. The ordered histories determine the primary result. [Results by condition and axis](results.json)

## Try a forecast

From this folder, use Python 3.13 in a virtual environment. The study ran with Python 3.13.15, NumPy 2.5.3 and PyTorch 2.14.1+cpu. Install the dependencies in that environment and run the included example.

```sh
python -m pip install -r requirements.txt
python predict.py example.json
```

For the pinned Linux or Windows CPU build, install it from PyTorch’s CPU wheel index before running the requirements command.

```sh
python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu"
```

The example contains invented readings. Its last XYZ value is `[2.25, -0.2, 8.7]`. The command prints three forecasts as JSON. Persistence returns that last value, ridge gives approximately `[2.56523, 1.53920, 9.32458]`, and the Transformer gives approximately `[4.16441, 2.39885, 7.92765]`. The shipped checkpoint includes the fitted weights, TRAIN means and scales, and ridge coefficients. Inference runs locally on CPU. The example and software checks were exercised on Linux.

For a different history, provide a JSON array of exactly 16 rows of three finite numbers each, ordered from oldest to newest. Each row must contain the right-arm accelerometer’s X, Y and Z in that order, in the source instrument’s coordinate frame and native units, acquired consecutively at 25 Hz. Supply the stored values directly. The predictor applies its saved normalization.

```sh
python predict.py my-history.json
python -B test_predict.py
```

## Where the numbers came from

The UCI dataset records 19 activities with sensors on the body. This study selects two walking conditions and the three right-arm accelerometer columns. Four people supplied 3,360 training windows. Two other people supplied the 1,680 assessment windows. Each window lies inside one five-second clip. At 25 Hz the 16 readings span 0.60 seconds from the first to the last timestamp. The target follows the last reading by 0.12 seconds. Training and assessment left two more people in reserve. [Exact protocol of 20 November 2026](protocol.json)

The 17,891-parameter Transformer starts by repeating the final XYZ measurement. Training teaches it a correction. Ridge learns a correction from the same flattened history. Both use standardization fitted only on training inputs. The protocol fixed the twelfth epoch for assessment. Independent checking matched all 1,680 target rows and recomputed the scores. On the selected checkpoint spot checks, a second implementation of the attention calculation agreed within 0.000002 stored units.

These measurements describe acceleration in the sensor frame, with gravity retained. They do not identify joint angles, a person’s intent, or a neural signal. Only two people and two walking conditions contributed assessment data. Repeated windows from a five-minute activity bout share a movement pattern. Treating the windows as independent people would overstate the evidence. This is a standalone motion benchmark. The broader multimodal NeuroTranslation learner requires its own evaluation.

## Reproduce the study

Inference needs only the files in this folder. To reproduce fitting and scoring separately, download the original ZIP, retain it unopened, and use a fresh output directory. The reader selects the specified members directly from the ZIP. These commands re-create the study locally and produce per-window assessment arrays locally. The release includes model parameters and aggregate scores.

```sh
curl -fL 'https://archive.ics.uci.edu/static/public/256/daily+and+sports+activities.zip' -o daily-sports.zip
OMP_NUM_THREADS=2 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python forecast.py fit daily-sports.zip reproduction --threads 2
OMP_NUM_THREADS=2 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python forecast.py assess daily-sports.zip reproduction --threads 2
```

The frozen archive SHA-256 is `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`. The original training/scoring source SHA-256 is `9315662e2231db487802834703f397d81dab88ca4e00c7c36006a5dadfdb69b8`. The protocol SHA-256 is `3f538b53440c54fcc37b2f160be5e1ebfb5b62e97b896a95d0b231b5f8863014`. The released checkpoint SHA-256 is `96018afd0b6f5e38f6af721a540a1b6bca55b0f4c7c4a321c535b3d2722d873b`. To check the files on Linux, run `sha256sum -c SHA256SUMS`. On macOS, run `shasum -a 256 -c SHA256SUMS`.

**Dataset credit.** Billur Barshan and Kerem Altun, *Daily and Sports Activities* (2010), UCI Machine Learning Repository, DOI 10.24432/C5C59F. The creators supplied the measurements. This study selected two activities and three axes, extracted forecast windows, fitted two predictors, and calculated the reported errors. The underlying dataset carries its own attribution license. [UCI dataset and citation](https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities) · [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)
