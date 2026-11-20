[The studies](../README.md) › Study 26 · Walking: a small transformer on an arm sensor

# A straight-line fit beat a small transformer at forecasting an arm sensor 120 ms ahead

A sensor strapped to a walker’s right arm records how its speed changes along three directions, X, Y and Z (an accelerometer). Take its last 16 readings: what will it read three samples, 120 milliseconds, later? For the two people it was tested on, a small transformer, the kind of network behind today’s large language models, missed by **0.855** on average. A straight-line fit on the same 16 readings missed by **0.781**, and was lower for both people. Both beat the simplest forecast, repeating the last value. The rule set before the assessment asked the transformer to beat both, so it failed. Motion only: no brain or muscle signal.

| History in time order | Windows | Repeat the last value | Straight-line fit | Transformer |
|---|---:|---:|---:|---:|
| Both walks | 1,680 | 1.182 | **0.781** | 0.855 |
| Parking-lot walking | 840 | 1.300 | **0.830** | 0.907 |
| Flat treadmill at 4 km/h | 840 | 1.065 | **0.732** | 0.803 |

Numbers are the plain average miss (mean absolute error) across the three axes, in the original sensor’s stored units. Lower is better. The rule set before the assessment required the transformer to beat both alternatives for **each** of the two people it was tested on. The straight-line fit had the lowest error for both ([each person’s scores](architecture/earlier-results.json)). Shuffling the first 15 readings while keeping the last in place raised the pooled error to 1.056 for the straight-line fit and 0.957 for the transformer. Repeating the final reading still scored 1.182. That comparison tests sensitivity to order. The ordered histories determine the primary result. [Results by condition and axis](results.json)

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

The example contains invented readings. Its last XYZ value is `[2.25, -0.2, 8.7]`. The command prints three forecasts as JSON. Repeating the last reading returns that value, the straight-line fit gives approximately `[2.56523, 1.53920, 9.32458]`, and the transformer gives approximately `[4.16441, 2.39885, 7.92765]`. The shipped checkpoint includes the fitted weights, the means and scales of the people the models were fitted on, and the straight-line fit’s coefficients. Inference runs locally on CPU. The example and software checks were exercised on Linux.

For a different history, provide a JSON array of exactly 16 rows of three finite numbers each, ordered from oldest to newest. Each row must contain the right-arm accelerometer’s X, Y and Z in that order, in the source instrument’s coordinate frame and native units, acquired consecutively at 25 Hz. Supply the stored values directly. The predictor applies its saved normalization.

```sh
python predict.py my-history.json
python -B test_predict.py
```

## Where the numbers came from

The UCI dataset records 19 activities with sensors on the body. This study selects two walking conditions and the three right-arm accelerometer columns. The four people the models were fitted on supplied 3,360 windows. The two other people they were tested on supplied 1,680. Each window lies inside one five-second clip. At 25 Hz the 16 readings span 0.60 seconds from the first to the last timestamp. The target follows the last reading by 0.12 seconds. Two more people were set aside and never opened. [Exact protocol of 20 November 2026](protocol.json)

The 17,891-parameter transformer starts by repeating the final XYZ measurement. Fitting teaches it a correction. The straight-line fit (ridge regression) learns a correction from the same 16 readings laid end to end. Both rescale their inputs with averages and spreads taken only from the people they were fitted on. The plan fixed in advance that the transformer after its twelfth pass through the fitting data would be the one assessed. Independent checking matched all 1,680 target rows and recomputed the scores. On the selected checkpoint spot checks, a second implementation of the attention calculation agreed within 0.000002 stored units.

These measurements describe acceleration in the sensor frame, with gravity retained. They do not identify joint angles, a person’s intent, or a neural signal. Only two people and two walking conditions contributed assessment data. Repeated windows from a five-minute activity bout share a movement pattern. Treating the windows as independent people would overstate the evidence. This is a standalone motion benchmark. Two later comparisons scored the same two people again, so neither is a fresh test: the project’s general model fitted to this sensor alone, and a comparison of how far ahead to forecast. Both are in [architecture/](architecture/README.md) and on [the studies page](../README.md).

## Reproduce the study

Inference needs only the files in this folder. To reproduce fitting and scoring separately, download the original ZIP, retain it unopened, and use a fresh output directory. The reader selects the specified members directly from the ZIP. These commands re-create the study locally and produce per-window assessment arrays locally. The release includes model parameters and aggregate scores.

```sh
curl -fL 'https://archive.ics.uci.edu/static/public/256/daily+and+sports+activities.zip' -o daily-sports.zip
OMP_NUM_THREADS=2 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python forecast.py fit daily-sports.zip reproduction --threads 2
OMP_NUM_THREADS=2 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python forecast.py assess daily-sports.zip reproduction --threads 2
```

The archive’s SHA-256 is `f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e`. The SHA-256 of the original fitting and scoring code is `9315662e2231db487802834703f397d81dab88ca4e00c7c36006a5dadfdb69b8`. The protocol SHA-256 is `3f538b53440c54fcc37b2f160be5e1ebfb5b62e97b896a95d0b231b5f8863014`. The released checkpoint SHA-256 is `96018afd0b6f5e38f6af721a540a1b6bca55b0f4c7c4a321c535b3d2722d873b`. To check the files on Linux, run `sha256sum -c SHA256SUMS`. On macOS, run `shasum -a 256 -c SHA256SUMS`.

**Dataset credit.** Billur Barshan and Kerem Altun, *Daily and Sports Activities* (2010), UCI Machine Learning Repository, DOI 10.24432/C5C59F. The creators supplied the measurements. This study selected two activities and three axes, extracted forecast windows, fitted two predictors, and calculated the reported errors. The underlying dataset carries its own attribution license. [UCI dataset and citation](https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities) · [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)
