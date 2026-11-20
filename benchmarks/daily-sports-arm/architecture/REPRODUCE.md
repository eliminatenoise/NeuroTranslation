# Reproduce the four-horizon arm study

## Try the fitted model

The forecast needs only Python 3 and NumPy. From this folder run the two commands below.

```sh
python -m pip install numpy
python predict.py example.json
```

The Linux, macOS and Windows launchers run the same example. Python must be available as `python3` on Linux and macOS, or as `py -3` or `python` on Windows. The command-line JSON and Linux launcher were exercised on Linux. Native macOS and Windows execution remains unverified.

For a recorded input use 16 consecutive samples at 25 Hz, with the oldest first. Give each sample as three numbers in X, Y, Z order. The timestamps are integer milliseconds. The body part must be `right_arm`, and the instrument, axes, conditions and scale must match the walking study. The timestamps locate the query on the input clock. The runner cannot detect that a sensor was worn on a different limb or turned upside down. The output contains the predicted sensor reading for each lead.

## Check the published scores

Keep this folder inside `benchmarks/daily-sports-arm/` in the NeuroTranslation checkout. The parent contains the already-fitted three-step ridge and arm Transformer. The prediction example above stands alone. The full comparison also uses the original walking archive and one separately downloaded open model.

The study ran with Python 3.13.15, NumPy 2.5.3, PyTorch 2.14.1+cpu, chronos-forecasting 2.3.2 and Transformers 4.57.6. In a fresh Python 3.13 virtual environment, install CPU PyTorch using the package index appropriate to your operating system, then install the pinned comparison requirements. These commands install the Linux CPU build used here.

```sh
python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu"
python -m pip install -r requirements.txt
python fetch_bolt.py
```

The fetcher obtains the pinned public model card, configuration and 34.6 MB safetensors weight file, checks their identities, and stores them in the local `.bolt/` directory. It needs no paid service or account. Save the UCI archive as `daily-sports.zip` and leave it zipped. The reader verifies its original SHA-256 and opens only the study’s named members. [Original UCI download](https://archive.ics.uci.edu/static/public/256/daily+and+sports+activities.zip) · [Input digests](sources.json)

```sh
python reproduce.py --archive daily-sports.zip --output my-scores.json
```

This mode reuses the shipped ridge coefficients and both Transformer checkpoints. It recalculates all four-horizon methods on p5 and p6, compares the ordered origins and measured targets with the study digests, and measures local CPU latency. The earlier arm Transformer makes its original single-horizon prediction for reference. Use `--arm-study PATH` if the parent arm benchmark lives elsewhere. The CPU reproduction uses two PyTorch threads and one BLAS thread. Allow for floating-point differences between kernels and for timing differences under load.

To reproduce fitting as well, request it explicitly with a new output filename.

```sh
python reproduce.py --archive daily-sports.zip --refit-ridge --output my-fit-and-scores.json
```

This fits only the 1-, 6- and 12-sample heads on p1 through p4. The 3-sample ridge already exists in the arm checkpoint. The script verifies all coefficient arrays, intercepts, means and scales against the saved model before evaluating. All windows end inside one five-second segment. None of the reads select p7 or p8. [Exact design](protocol.json) · [Published development scores](results.json)

Billur Barshan and Kerem Altun supplied *Daily and Sports Activities* under CC BY 4.0. This study selected two activities and the right-arm acceleration channels, fitted forecast heads and calculated the errors. The existing project dedication covers project-authored code and text. Upstream recordings, packages, checkpoint weights and documentation retain their own terms. The public example uses invented numbers and the download contains no participant-level recordings. [UCI citation](https://doi.org/10.24432/C5C59F) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Project licence](../../../LICENSE) · [Source inventory](sources.json)
