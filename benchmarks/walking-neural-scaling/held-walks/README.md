# Forecasting walking force when muscle readings drop out

[Download the offline models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip) · [Technical edition](TECHNICAL.md) · [Exact scores](results.json)

Training with simulated delays and gaps in muscle readings made the walking-force forecasts more accurate. On recordings from six people it had never trained on, the model missed by **1.81 newton-seconds** when the last 60 milliseconds of muscle readings were hidden. The version trained with complete readings missed by **8.79**. The model trained with disruptions also made closer forecasts with complete readings, at **1.69** compared with **2.16**. [Original walking recordings](https://aperta.ulakbim.gov.tr/records/286866)

## What the model forecasts

A force plate is part of the floor that measures how hard a person pushes against it. Electrodes on the skin record small voltages associated with muscle activity. The model gets the previous fifth of a second of both measurements, cut into ten pieces of 20 milliseconds each. It estimates how much upward force the plate will measure over the next tenth of a second.

We report force added over time because a single sharp peak and a more sustained push can have different effects. The unit is a **newton-second**, shortened to N·s. For example, 100 newtons held for the entire tenth of a second adds to 10 N·s. We compare each forecast with the later force readings, then take the size of the difference. Smaller average differences mean closer forecasts.

The floor plates record 2,000 values per second. Each forecast uses only the 400 samples before its starting time and is checked against the next 200. It receives one force average for each of the ten pieces. The four muscle channels are summarized by how strongly each channel has changed from its own earlier readings. For each piece, the model gets the middle and upper-range change across the muscle channels and an indication of which measurements are available. Force is expressed as a fraction of 800 newtons. Person and site identifiers are used only to group the results. A simple comparison uses the average force from the latest 20 milliseconds and assumes it continues for the next 100 milliseconds. The learned forecast starts with that estimate. From the past force and muscle readings, it estimates how much to add or subtract.

## The new test group

The open İzmir archive includes walks from 29 people. Before fitting, we set aside one person to test the file reader, assigned 16 to fitting and set another six aside for early development. The six people in this follow-up were held back from all of those groups. Each contributed three recorded walks across an instrumented floor, so the comparison covered 18 walks. We kept the separate Belgian final group closed. [Source and recording methods](https://aperta.ulakbim.gov.tr/records/286866) · [Earlier fitting and Belgian data](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/walking-neural-scaling)

We scheduled forecasts 20 milliseconds apart when there was enough room in the recording for the full input and the full outcome. We computed and saved all **863 forecasts per model and input condition** before extracting their later force values. Two file readers then agreed on which analog values and force calibration to use. Every past history reproduced when the full recordings were checked. The readers agreed to within a trillionth of a newton, and adding the force at two different sample rates gave the same impulse well within a trillionth of a newton-second. One file had an extra zero-filled block after the recorded frames. Every force value used in the test fell inside the declared data.

## What changed during fitting

The smaller three-pass model uses the same calculation three times to refine its forecast. Its original versions learned from recordings by 12 Belgian walkers and from zero, four, eight or sixteen İzmir walkers. Shorter and longer versions had their own fits and used the same reference windows for comparison. We use the previously chosen saved run numbered 20261124 for each configuration.

To compare training with and without disruptions, we started two copies from the same saved weights and trained each for 900 more updates with the same draws of walking histories. One copy continued with the readings as recorded. In the other, each training history had a 15% chance of delaying the muscle summaries by one 20 ms piece and separately a 20% chance of hiding the newest three pieces, which cover 60 ms. The force readings and the answers stayed the same. We ran this comparison starting from both the eight-person and sixteen-person fits.

The test first used the complete archived inputs. It then delayed the muscle readings and separately hid the most recent 60 milliseconds. Those disruptions were made for the comparison. The measured force stayed available in each version, and the same later plate readings scored the answers. We also compared the model with two simpler fits. Ridge combines input values using fitted multipliers and a penalty for large multipliers. Boosted trees combine a series of small decision trees. Both used the same past readings as the recurring model.

## Forecast errors

| Method | Complete input | Muscle readings 20 ms late | Latest 60 ms of muscle readings hidden |
| --- | ---: | ---: | ---: |
| Carry the latest force forward | 7.012 | 7.012 | 7.012 |
| Ridge | 5.483 | 5.702 | 6.335 |
| Boosted trees | 3.326 | 3.676 | 4.582 |
| Eight added people, original three-pass model | 2.676 | 4.364 | 13.769 |
| Eight added people, more training with complete readings | 2.163 | 3.750 | 8.793 |
| Eight added people, more training with generated disruptions | **1.693** | **1.743** | **1.813** |
| Sixteen added people, more training with complete readings | 2.002 | 2.506 | 11.285 |
| Sixteen added people, more training with generated disruptions | 1.903 | 1.845 | 2.147 |

First we averaged the misses along each walk. Then we averaged the three walks for each person and gave all six people the same weight. The eight-person model trained with disruptions lowered error by **0.470 N·s** with complete readings, by **2.007** with delayed readings and by **6.980** with missing recent readings. All six people had a lower error in all three comparisons. To see how much the estimate depends on the people in this test, we drew six people from this same group with repeats allowed. We counted all 46,656 ordered draws and kept each person's two models together. The middle 95% of the reductions ran from **0.302 to 0.670**, **1.479 to 2.594** and **6.054 to 7.792 N·s**, respectively. Each person supplies many forecasts, so 863 forecasts still represent six people.

On complete readings, the original three-pass versions missed by **4.602, 3.064, 2.676 and 3.004 N·s** when they had zero, four, eight and sixteen additional İzmir walkers for fitting. The difference between sixteen and eight averaged **0.329 N·s higher** for sixteen. The middle 95% ranged from **0.030 lower to 0.664 higher**, so this group leaves the difference uncertain. The one-, three-, five- and eight-pass starting fits using eight added walkers averaged **3.826, 2.676, 3.074 and 3.287 N·s**. The exact results list every tested method and condition. [All scores](results.json)

## Try the models

1. Download and extract the whole archive. Keep the files together. Install Python 3.13 if it is missing. In the extracted folder, run `python3.13 -m venv .venv` on Linux or macOS or `py -3.13 -m venv .venv` on Windows. That puts the example's packages in its own folder. Install them with `.venv/bin/python -m pip install -r requirements.txt` on macOS or Linux or `.venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows.
2. Run `sh "Open on Linux.sh"` on Linux or `sh "Open on macOS.command"` on macOS. On Windows, run `"Open on Windows.cmd"` from Command Prompt. We tested the extracted launcher on Linux and checked the other launchers from source. The first run uses invented values. It prints a forecast in N·s for each of the eleven recurrent models and the simple last-force rule. The study table above also includes ridge and trees.
3. Append `--input history.json` to use your own prepared recording. Put ten average force values, in newtons, under `measured_plate_force_n`. Put ten matching rows of four or six muscle measurements under `emg_rms_volts`. Each value is the root mean square voltage for that 20 ms piece, a way to give one size to a signal that goes positive and negative. Put the oldest piece first and use `null` where a muscle value is missing. Include `--model augmented_08` to run just the eight-person model trained with generated disruptions plus the simple rule. Include `--condition delay-muscle` or `--condition hide-muscle` to see how the same history changes when muscle readings are late or absent.

The download includes the exact saved weights in 32-bit format, the code, aggregate scores and a list of file checksums. The original recordings are available through the dataset publisher. The comparisons are forecasts made from past readings collected during overground walking at one site. Most methods already learned from other people at that site. The Belgium-only version also tests a change of site. Actual equipment delays, other walking setups and other movements require their own measurements. The six people in this comparison have now been scored. A choice based on these results needs a fresh test group.

Project code and fitted weights are available under CC0 to the extent of our rights. Şenay Mihcin, Mehmet Yılmaz, Ahmet Mert Şahin and Sevinç Akdeniz released the original measurements under CC BY 4.0. [Dataset and credit](https://aperta.ulakbim.gov.tr/records/286866)
