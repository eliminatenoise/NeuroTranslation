# Cortical forecasts across recording days

[Simple guide](SIMPLE.md) · [Aggregate results](results.json) · [Download the model](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cortical-cross-day/Cortical-Cross-Day.zip)

## Run a forecast

Extract the download and open a terminal in the extracted folder. The reference environment is Python 3.12. Install dependencies with `python -m pip install -r requirements.txt`, then run `python predict.py`. This runs a generated example. The Linux, macOS and Windows launchers call the same program. The Linux launcher was exercised with generated and recorded inputs.

For recorded input, run `python -m pip install pynwb==3.1.3`, download the exact public MC Maze Medium behavior archive, then run `python predict.py --archive PATH_TO_NWB --issue-ms 200`. The time is in milliseconds on the archive clock. The program reads spike histories and observation intervals. The forecast at issue 200 uses spikes from `[0, 200)` ms. The output gives `x_mm` and `y_mm` at a 100 ms horizon. [Exact public NWB file](https://api.dandiarchive.org/api/assets/7ef450a8-8684-42e2-8598-cd38ca2b2e50/download/)

To supply already binned input, run `python predict.py --input window.json`. Use `counts` and Boolean `available` arrays of shape 10 by number of units. Ten rows represent successive 20 ms bins, oldest first. An unavailable entry carries a zero count. The one-dimensional `corrected_electrode_rows` array has one integer in 0–191 per unit. The supplied model expects the recording's row labels in the authors' corrected order. [Author mapping](https://neurallatents.github.io/datasets#mc_maze)

## Inputs and fitted models

The network forecasts planar hand coordinates from a 200 ms spike history. Ten half-open bins preserve time order. A bin counts spikes only within the observed span of each unit. For each electrode row, the model uses the mean square-root count of its observed units and an availability flag. Separate rows preserve which electrode rows carried activity. Rows 0–95 identify dorsal premotor cortex. Rows 96–191 identify primary motor cortex, using the authors' correction of +96 for units whose identifier starts with 2. The archives establish row labels and regions. Physical electrode alignment across days remains unverified.

The compact network applies a short temporal convolution, a recurrent layer that carries a state across input bins, and eight updates with one shared recurrent cell. It predicts a correction to the training position mean. Both archives came from the same rhesus macaque, on 28 and 29 September 2009. Training used 75 trials from day one plus 0, 24, 72 or 188 from day two. Mixed fits gave equal weight to the two days, then each trial and each issue within it. The same 600 updates, 96-row batches and three initial weight seeds were used across fitting sizes. Regularized linear forecasts and the fixed training mean used matched groups. [Small archive](https://doi.org/10.48324/dandi.000140/0.220113.0408) · [Medium archive](https://doi.org/10.48324/dandi.000139/0.220113.0408)

## Second-day confirmation

The development comparison used 42 day-two trials and selected the 72-added-trial eight-pass model at 23.25 mm. The models and all three seeds were frozen before forecasting the 20 reserved day-two trials. The final score used 1,281 forecasts on timestamps with an exact position measurement at the horizon. The mean gives each trial equal weight after averaging Euclidean endpoint error within it. The three trained seeds are averaged as separate forecasts. The day-one confirmation group and both official NLB test files remain closed.

| Model | Confirmation error (mm) |
| --- | ---: |
| Eight passes, day one only | 42.94 |
| Eight passes, plus 24 day-two trials | 30.07 |
| Eight passes, plus 72 day-two trials | 27.33 |
| Eight passes, plus 188 day-two trials | 27.69 |
| Linear reference, 72 added trials | 49.79 |
| Fixed position mean, 72 added trials | 55.53 |
| Area summaries, five passes, 72 added trials | 54.24 |

The selected setting reduced mean error by 15.61 mm (36.3%) versus day one alone and improved 19 of 20 trials. Against the linear reference, it reduced error by 22.46 mm (45.1%) and improved all 20. Descriptive paired trial bootstrap intervals were 11.13–20.34 mm and 18.02–26.84 mm, respectively, using 20,000 draws. These intervals describe this reserve within one animal and one recording day.

A generated 40 ms delay in the input raised the selected model's error to 30.29 mm. Permuting electrode row labels within each area on day two raised it to 81.10 mm. The latter comparison measures the importance of label order in this dataset. Transfer to another animal or changed recording hardware requires separate evaluation.

## Portable checkpoint

The package includes the original FP32 SafeTensors weights and an ONNX export of seed 20261124, chosen before the reserve was scored. This individual model averaged 28.31 mm on unmodified confirmation inputs. The export matched the frozen PyTorch predictions to within 0.00023 mm per coordinate across the development and reserve rows and conditions. On the tested CPU, a warm single forecast took a median of 0.048 ms with ONNX Runtime and 0.174 ms with PyTorch. ONNX Runtime processed 1,281 rows in one warm call in 18.00 ms. PyTorch used 256-row chunks and took 12.14 ms for those same inputs. These timings cover model inference. Reading an archive and preparing its spike bins are separate operations.

The two DANDI archives are licensed under CC BY 4.0. The download contains code, weights, instructions and aggregate measurements. The recordings are available through their source links. [DANDI archive](https://dandiarchive.org/dandiset/000139/0.220113.0408)
