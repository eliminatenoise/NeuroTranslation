# Forecasting treadmill force with gaps in muscle readings

[Compare in your browser](https://eliminatenoise.github.io/NeuroTranslation/treadmill-muscle-gaps/) · [Technical edition](TECHNICAL.md) · [Download the tested models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/803c645d63055245b084efb10f34b13d83a10d29/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip)

On Georgia Tech treadmill recordings from nine people, the compact NeuroTranslate 0.1 model was more accurate when it had learned to cope with interrupted muscle readings. With the latest 60 milliseconds of those readings hidden, its average force forecast error was **12.03 newton-seconds**. The same model trained with complete readings missed by **16.18**. Error fell for all nine people. [Georgia Tech recordings](https://doi.org/10.35090/gatech/70296)

## Read the results

Choose a recording scope and a condition in the [browser comparison](https://eliminatenoise.github.io/NeuroTranslation/treadmill-muscle-gaps/). The whole recording includes changes in speed, different treadmill movements and pauses. The marked walk limits the same forecasts to the part the authors labelled as walking at 1.2 metres per second. The three input conditions show complete readings, a simulated 20-millisecond delay, and a simulated gap in the most recent 60 milliseconds. Past force readings stay available in each condition.

The forecast estimates the upward support force on one treadmill belt over the next tenth of a second. Adding force over time gives an amount called **force impulse**, measured in newton-seconds, or N·s. A steady 100 newtons for a tenth of a second adds up to 10 N·s. A forecast of 8 N·s against a measured 10 N·s has an error of 2 N·s. Smaller numbers in the comparison mean closer forecasts.

### Whole recording, 7,268 forecast times

| Forecast method | Complete readings | 20 ms delay | Latest 60 ms hidden |
| --- | ---: | ---: | ---: |
| Three-pass model trained in Belgium | 12.84 | 12.98 | 14.53 |
| Three-pass model trained with complete readings | 12.04 | 12.60 | 16.18 |
| Three-pass model trained with simulated interruptions | 11.96 | 11.98 | 12.03 |
| Carry the latest force forward | 17.55 | 17.55 | 17.55 |
| Continue the recent force trend with damping | 17.48 | 17.48 | 17.48 |
| Ridge linear fit | 12.21 | 12.41 | 12.81 |
| Boosted decision trees | 13.59 | 13.83 | 14.40 |

### Marked 1.2 m/s walk, 440 forecast times

| Forecast method | Complete readings | 20 ms delay | Latest 60 ms hidden |
| --- | ---: | ---: | ---: |
| Three-pass model trained in Belgium | 6.74 | 6.87 | 9.12 |
| Three-pass model trained with complete readings | 5.16 | 5.89 | 11.77 |
| Three-pass model trained with simulated interruptions | 5.21 | 5.22 | 5.39 |
| Carry the latest force forward | 11.63 | 11.63 | 11.63 |
| Continue the recent force trend with damping | 11.43 | 11.43 | 11.43 |
| Ridge linear fit | 7.92 | 7.80 | 8.90 |
| Boosted decision trees | 7.33 | 7.74 | 8.44 |

With the newest muscle readings hidden, training with interruptions lowered the average error by **4.15 N·s** across the whole recording. The range from resampling the nine people was **3.52 to 4.70 N·s lower**. The simpler linear fit scored **12.81 N·s** with the same inputs. The model trained with interruptions was more accurate than that fit for eight of the nine people.

In the marked walk, the same change in training lowered error from **11.77 to 5.39 N·s**. The reduction was **6.38 N·s**, with a resampling range of **5.38 to 7.49 N·s lower**. All nine people improved in this subset as well. With complete readings, the same change gave **12.04 to 11.96 N·s** across the whole recording and **5.16 to 5.21 N·s** in the marked walk. The uncertainty ranges leave room for either model to lead in both comparisons. With a 20-millisecond simulated delay, training with interruptions gave a smaller advantage. [Exact scores and differences](../../../docs/treadmill-muscle-gaps/results.json)

### How the scores handle people with different numbers of forecasts

At every forecast time, each method is scored against the same later force measurement. The study takes the size of the error and averages those errors for each person. The final score gives each person equal weight. A person with a longer recording still contributes one average. The uncertainty range comes from drawing nine people with replacement from the original group 20,000 times, carrying each person’s two scores together. The draw starts from the fixed number 20261126 so the same calculation can be repeated. Each reported range covers the middle 95 percent of those paired differences. The forecasts within a recording provide detail about that person’s performance.

## The recordings and the forecast clock

The study used ten nominated Georgia Tech treadmill recordings. A separate engineering recording helped identify the belt from its position and confirm the named muscle signals. One of the nominated recordings lacked that belt. The final comparison covers **nine people and 7,268 forecast times**. The marked walk contains **440 of those times**. Its beginning and end come from the study’s annotations based on force. A two-second margin at each end keeps the selected histories and targets inside the marked interval.

The files store 2,000 samples each second. The study checked the muscle names on samples from one to two seconds into the file. It then started issuing forecasts at 2.4 seconds and advanced the forecast time by three tenths of a second. Each issue uses the previous two tenths of a second as input and the next tenth as its target. Within a recording, each forecast time has its own block of earlier and later samples. All methods and muscle conditions use the same blocks at that time. The forecasts were saved before the measured outcomes were read for scoring. An independent calculation reproduced the scores, the participant comparisons and their uncertainty ranges. [Original methods](https://pubmed.ncbi.nlm.nih.gov/38129422/)

## The inputs and models

Surface electrodes measure small voltages over six muscles on the left leg and hip. The six sites are the tibialis anterior at the shin, the medial gastrocnemius at the calf, the vastus lateralis and rectus femoris at the front of the thigh, the biceps femoris at the back of the thigh, and the gluteus medius at the side of the hip. The force plate under the belt measures support force. The model receives ten pieces of past history, each twenty milliseconds long. Each piece supplies average force, two summaries of muscle activity and two indicators of measurement availability. Force is divided by 800 newtons to put it on the input scale used during training.

For each muscle, the system estimates signal strength by squaring the voltage, averaging it and taking the square root. This is the root mean square, or RMS. It compares that strength with the level in at least three earlier available pieces. It takes the logarithm of one plus the ratio, then summarizes the muscles using the median and the 80th percentile. The latter is a value at or above about four fifths of the muscle summaries. The first pieces supply the earlier measurements needed for this comparison.

Each version of the compact model starts its forecast by carrying the latest force average forward for one tenth of a second. It estimates a correction to that starting point. The same learned calculation runs three times for each forecast. The study compares the following seven methods.

- The **Belgium-only model** uses the original three-pass weights fitted to recordings from 12 Belgian walkers.
- Two **matched three-pass models** started from the same weights fitted on those 12 people and eight people from İzmir. Each received 900 more training updates on the same draws of past readings. One always saw the complete input. The other had a 15 percent chance of shifting muscle inputs one piece later and a separate 20 percent chance of removing the latest three pieces. Both changes include the availability indicator. The test applies the two disruptions separately.
- The **last-force rule** carries the latest 20-millisecond force average forward. The **damped trend** estimates the direction of change from the latest five force averages and lets that change slow with a 50-millisecond time constant.
- The **linear fit** combines the inputs using fitted multipliers whose size is penalized. The **decision trees** combine many small rules for splitting the input into groups. Both were fitted on the earlier Belgian and İzmir group and receive the same encoded past inputs as the matched models. [Earlier walking study and fitting details](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/walking-neural-scaling/held-walks)

## Run the saved models

1. [Download the tested checkpoint ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/803c645d63055245b084efb10f34b13d83a10d29/benchmarks/walking-neural-scaling/held-walks/Held-Walking-Forecasts.zip) and extract it into one folder. Use Python 3.13. In that folder, create an environment with `python3.13 -m venv .venv` on Linux or macOS, or `py -3.13 -m venv .venv` on Windows. Install the exact packages with `.venv/bin/python -m pip install -r requirements.txt` on Linux or macOS, or `.venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows.
2. Run `sh "Open on Linux.sh"` or `sh "Open on macOS.command"`. On Windows, run `"Open on Windows.cmd"` from Command Prompt. The archive first uses an invented history. It prints forecasts in N·s for the saved recurrent models and the last-force rule. The extracted Linux launcher was tested. The macOS and Windows launchers were checked from source.
3. To compare the matched models, run one launcher with `--model clean_08` and run it again with `--model augmented_08`. Add `--condition delay-muscle` to shift the muscle history or `--condition hide-muscle` to hide the latest 60 milliseconds. Use `--input history.json` to supply your own compatible history. In that file, put ten average forces in newtons under `measured_plate_force_n` and ten rows of four or six RMS voltages under `emg_rms_volts`. Put the oldest piece first and use `null` for a missing voltage. See the Georgia score file for the fitted linear and tree comparisons.

The model weights were already fixed before the Georgia test. The project has used these participants in other Georgia studies. The simulated gaps describe behavior on stored inputs from this setup. The paper describes different sample rates at acquisition before storage on the common clock. Timing on a live device and the effect of resampling still need measurement.

Keaton Scherpereel, Dean Molinaro, Omer Inan, Max Shepherd and Aaron Young published the original recordings under CC BY 4.0. This comparison distributes aggregate scores. The authors host the measurements. The checkpoint archive credits the earlier model training sources. [Dataset and terms](https://doi.org/10.35090/gatech/70296)
