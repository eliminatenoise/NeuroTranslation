# Hand movement forecasts on a separate recording day

Recent hand motion and handle force predicted where the hand would be a tenth of a second later with an average miss of 2.126 mm. Giving the forecast a way to adjust how much it used electrical activity from the brain produced the same average error to three decimal places. Motion and force remain the reference for this task.

## What the recordings measured

A macaque named Han held a handle and moved it in a plane. Instruments measured where the hand was and how hard it was pushing or pulling against the handle in three directions. Sometimes the handle pushed back during a trial. The experiment also recorded electrical activity from Area 2, a part of the brain that receives information about the arm. Each forecast predicted the later position of the handle as a measure of hand movement. [Original experiment](https://doi.org/10.7554/eLife.48198)

We used 218 trials recorded on December 7, 2017 to fit the two forecasts. Another 72 trials from the same day helped select their settings and fit the two ways of blending them. We kept out the [74 trials used in the original comparison](../README.md). The test here used Han's December 4 recording from a different archive export. Of 805 trials on that day, 786 were long enough to make at least one forecast. [December 7 archive, CC BY 4.0](https://dandiarchive.org/dandiset/000127/0.220113.0359) · [December 4 archive, CC0](https://datadryad.org/dataset/doi:10.5061/dryad.nk98sf7q7)

## How a forecast works

At the forecast time, the program knows the current position of the hand. It looks back 200 milliseconds, divided into ten spans of 20 milliseconds each. At the start of each span, it reads where the hand was relative to the current position and how much force the handle measured. It also counts the electrical events recorded from each unit during the span. The December 4 file stores counts in 10 millisecond spans, so the program adds two consecutive counts to get each 20 millisecond count.

The fitted forecasts learn how to turn those readings into a predicted change in position. The motion and force forecast uses those two kinds of reading. The other forecast uses the same readings and adds three summaries of electrical activity for each span. They describe the typical event count, how much it varies across units and the fraction of units that fired at least once. Before taking the first two summaries, the program shrinks large counts using the logarithm of one plus the count. It combines the 65 units from the fitting day and the 83 sorted units from the test day in this way, without trying to match individual units from one day to the other. [Recording conversion used by the study authors](https://github.com/raeedcho/preprocess-from-limblab/blob/d7b78757bdfdd82cbc99aeeec549c763cc76ad17/convertCOactpasfiles.m)

The two forecasts learn a weighted sum of their inputs. We first put the readings on comparable scales using the 218 fitting trials. During fitting, a penalty discourages very large weights. Both forecasts selected the smallest of six tested penalties, 0.0001.

The two blends average the fitted forecasts. The fixed blend puts about 36% of the weight on the forecast with the brain signal. The adaptive blend changes that weight using how far the hand moved in the latest 20 milliseconds, the change in force over the window, the distance the motion and force forecast predicts, and how far apart the two forecasts are. The program shrinks large values and scales the four inputs based on the 72 configuration trials. It caps each scaled input at five standard deviations from its typical value. A smooth curve converts their weighted sum to a number between zero and one. The blend fitting smooths differences near zero at a scale of 0.01 mm. A 0.05 mm penalty discourages the adaptive weight from reacting too strongly to any one input. The middle 90% of test weights ranged from about 34% to 44%, with a median near 37%.

The other two forecasts give simple comparisons. Stay put predicts the hand will be in the same place a tenth of a second later. Constant speed and direction extends the last 20 milliseconds of movement into the next 100. The first forecast in each trial came 200 milliseconds after the trial began. Later forecasts came 320 milliseconds apart. The spacing kept the later position used to score one forecast out of the hand-position inputs for the other forecasts. All six methods used the same 5,921 forecast times. We saved every prediction before reading the corresponding later hand positions.

## Results

| Forecast | Average endpoint error | Average error in distance alone |
| --- | ---: | ---: |
| Stay put | 7.391 mm | 7.391 mm |
| Constant speed and direction | 3.788 mm | 2.758 mm |
| Motion and force | 2.126 mm | 1.528 mm |
| Motion, force and Area 2 activity | 2.141 mm | 1.538 mm |
| Fixed blend | 2.126 mm | 1.528 mm |
| Adaptive blend | 2.126 mm | 1.528 mm |

Endpoint error measures the distance between the predicted position and the recorded one. Error in distance alone asks how far the hand moved and ignores the direction. Each trial contributes equally after its errors are averaged. We estimated a range for each difference by drawing and averaging whole trials 4,000 times, with some trials drawn more than once.

Compared with motion and force, the adaptive blend reduced endpoint error by about 0.00001 mm. The middle 95% of the resampled estimates runs from a 0.0026 mm loss to a 0.0028 mm gain. Compared with the fixed blend, the adaptive blend was about 0.00007 mm worse. The range runs from a 0.00038 mm loss to a 0.00023 mm gain. Using the forecast that always adds the brain signal raised endpoint error by 0.0151 mm, with an estimated range of 0.0081 to 0.0217 mm. [All scores and paired ranges](results.json)

| Distance the hand actually moved | Forecast times | Trials | Change in endpoint accuracy with the adaptive blend |
| --- | ---: | ---: | ---: |
| Under 2 mm | 2,373 | 677 | 0.0023 mm worse |
| 2 mm to under 10 mm | 2,149 | 735 | 0.0015 mm worse |
| 10 mm to under 20 mm | 803 | 517 | 0.0016 mm better |
| 20 mm or more | 596 | 472 | 0.0062 mm better |

Every group has an estimated range that includes zero change. For moves of at least 20 mm, the range runs from a 0.0030 mm loss to a 0.0153 mm gain. We used the measured movement to group the test results only after the forecasts were saved. A trial can appear in more than one distance group. The results file also breaks out trials with and without a handle push. That flag covers the whole trial, so it can include forecasts made outside the push itself.

The original comparison showed a larger gain from Area 2 for movements of 20 mm or more within one day. Here the recording day, the way the data was exported and the way the forecast represented the brain signal all changed. The test cannot tell which change accounts for the difference. Both recordings came from the same animal and laboratory. The archived hand positions and force readings were processed before the study, and the original position filtering can use later raw samples. The device delay is unknown. The timing and accuracy in this report apply to the archived values.

## Run the example

Install Python and NumPy. Download the script, fitted numbers and example input to the same folder. The example contains invented numbers so you can check that the program works on your computer. In that folder, run `python infer.py example-input.npz forecasts.npz`. Use a new output filename each time. It produces six named tables of x and y movement in millimetres, and one number per forecast for the weight assigned by the adaptive blend. [Python program](infer.py) · [Fitted numbers](blend-weights.npz) · [Example input](example-input.npz)

An NPZ file holds named tables of numbers. For your own prepared input, the `motion` table needs ten pairs of positions in millimetres relative to the hand at forecast time. The `force` table needs ten sets of three readings in newtons. The `counts` table needs ten event counts for each sorted unit. Put the oldest of the ten spans first and keep the same coordinate axes and timing described above. Different numbers of sorted units are allowed. This test used only the unit counts and archive conditions described here. [Technical edition](TECHNICAL.md)

Recording credit goes to Raeed Chowdhury, Joshua Glaser and Lee E. Miller for the Dryad data, and Felix Pei, Raeed Chowdhury, Lee E. Miller and the source contributors for the DANDI recording.
