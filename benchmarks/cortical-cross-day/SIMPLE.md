# Forecasting hand position on a second day

[Technical guide](TECHNICAL.md) · [Aggregate results](results.json) · [Download the model](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cortical-cross-day/Cortical-Cross-Day.zip)

This NeuroTranslate model forecasts where a hand will be a tenth of a second later. It uses two tenths of a second of brain activity already recorded at the time of the forecast. The experiment asks how much the model improves when it gets examples from a new recording day.

## Open the forecast

Download and extract the ZIP. Open a terminal in the extracted folder. The reference environment uses Python 3.12. Run `python -m pip install -r requirements.txt` once to install the programs the model uses. Then run `python predict.py`. The Windows, macOS and Linux launchers run the same program once those packages are installed. The Linux launcher was tested with both generated and recorded inputs.

The default command creates a short set of invented spike counts for the demonstration. It prints two numbers, `x_mm` and `y_mm`. Those are the predicted coordinates in millimetres. The generated example is a way to check that the program runs and displays a forecast.

For recorded spikes from the actual study, run `python -m pip install pynwb==3.1.3` and download the linked MC Maze Medium behavior archive. Run `python predict.py --archive PATH_TO_NWB --issue-ms 200`, replacing the path with the downloaded file. The number 200 is the point in the archive at which the forecast is made. At that point, the program uses spikes from the preceding 200 milliseconds, up to the moment of the forecast. It estimates the hand position 100 milliseconds later. [Exact public NWB file](https://api.dandiarchive.org/api/assets/7ef450a8-8684-42e2-8598-cd38ca2b2e50/download/)

Use `python predict.py --input window.json` to supply a prepared window. The file has a `counts` table and an `available` table, with ten rows ordered oldest to newest. Each row covers 20 milliseconds and each column is one recorded stream of spikes. Put `true` in the corresponding availability entry if the unit was observed for the whole bin. A missing observation uses `false` and a zero count. The `corrected_electrode_rows` list gives the archive label, from 0 through 191, for each unit. Use the authors' corrected row ordering from the study. [Author mapping](https://neurallatents.github.io/datasets#mc_maze)

## What the model learns from the recordings

The archives record streams of small electrical events, called spikes, while one rhesus macaque moved its hand in a reaching task. Each stream has a label linking it to a sensor row. The model reads how the counts changed in the last ten short time bins. It keeps track of which sensor rows were available so silence and missing input are represented separately. The first 96 rows describe one motor area, the dorsal premotor cortex. The next 96 describe the primary motor cortex, using the authors' correction to those labels.

A small network looks at adjacent bins together. It carries a working state through the sequence and revises its estimate eight times using the same learned operation. The last estimate corrects a fixed starting guess. That guess is the average position from the training trials. The two archives were recorded on 28 and 29 September 2009. We used 75 trials from the first day in all four training sets, and added 0, 24, 72 or 188 trials from the second day. Whenever both recording days were included, each day had equal weight. Each trial counted equally within its day. Every version used 600 training updates of 96 rows and three independently initialized sets of weights. [Small archive](https://doi.org/10.48324/dandi.000140/0.220113.0408) · [Medium archive](https://doi.org/10.48324/dandi.000139/0.220113.0408)

## How much error fell on the reserved trials

We first compared the models on 42 separate trials from the second day. The eight-pass model that had seen 72 second-day fitting trials scored 23.25 mm and led that comparison. We froze its weights and its comparison models before scoring another 20 reserved trials from that day. The reported error is the distance between the predicted point and the measured point. It averages across 1,281 forecasts that had a measurement at the exact required archive time. Each trial counts equally, and the eight-pass results average across the same three trained models. The first day's spare confirmation trials and both official benchmark tests remain closed.

| Model | Average miss (mm) |
| --- | ---: |
| Eight passes, day one only | 42.94 |
| Eight passes, 24 added trials from day two | 30.07 |
| Eight passes, 72 added trials from day two | 27.33 |
| Eight passes, 188 added trials from day two | 27.69 |
| Simpler linear model with the same 72 added trials and sensor inputs | 49.79 |
| Fixed average position with the same training trials | 55.53 |
| Five passes using combined measures by brain area and 72 added trials | 54.24 |

Adding 72 trials from the new day reduced the miss by **15.61 mm, or 36.3%**, compared with using day one alone. Error fell in 19 of the 20 trials. Compared with the simpler linear model, the miss was **22.46 mm lower, or 45.1%**, and error fell in all 20 trials. To estimate how much the choice of these 20 trials could affect the results, we resampled those trials 20,000 times and recalculated the two gains. The middle 95% of the resampled gains was 11.13–20.34 mm and 18.02–26.84 mm. This describes the uncertainty within this recording and animal.

## How sensor labels affect the answer

We generated two extra conditions from the same recorded inputs. Giving the model readings from 40 ms earlier than normal raised its error from 27.33 to 30.29 mm. Shuffling which sensor readings went into each label within the same brain area raised the error to 81.10 mm. The drop in performance shows how much the forecast depends on the identity of the archive channels. The files verify which area and row each signal is assigned to. Their physical alignment across days is still an open measurement question. A different animal or recording device needs its own transfer test.

## The downloadable model

The ZIP contains the original weights in SafeTensors format and a portable ONNX copy of the same model. It uses the first of the three starting states, numbered 20261124, chosen before the reserved trials were scored. That one model had an average miss of 28.31 mm on the normal recorded inputs. The portable software matched the original PyTorch positions within 0.00023 mm per coordinate in the checked development and reserve forecasts, including the generated disruptions.

On the tested CPU, a single forecast after startup took a median of 0.048 milliseconds using the portable program and 0.174 milliseconds in PyTorch. The portable program processed all 1,281 inputs together in 18.00 milliseconds. PyTorch split the same set into groups of up to 256 inputs and took 12.14 milliseconds. These measurements time the calculation after the input is ready. Loading the archive and counting spikes take additional time. The authors provide both recordings under Creative Commons Attribution 4.0. The package contains the model, program and aggregate results, and the source links provide the recordings. [DANDI archive](https://dandiarchive.org/dandiset/000139/0.220113.0408)
