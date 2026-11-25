# Treadmill load from muscle readings

The compact model that reads 200 milliseconds of muscle activity and makes three passes had the lowest average error on the two treadmill plates in the main test. Its error was **21.97 newton-seconds**, against **26.79** for the model that always used the typical load from fitting. It improved for two of the three people scored. Including a fourth recording changed which model scored best. [Technical edition](TECHNICAL.md) · [Exact scores](RESULTS.json)

[Download the comparison and saved models](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/decline-treadmill/Decline-Treadmill.zip). Extract the folder, then open **Compare Results.html** in a browser. Choose which group of recordings and which kind of error to display. The viewer works offline.

## What the model predicts

The researchers used an instrumented treadmill. Each belt has a plate that measures the force on it. The forecast adds up the force at right angles to each plate over the next tenth of a second. This quantity is called **impulse**. If someone pushes against a plate with 500 newtons for a tenth of a second, the impulse is 50 newton-seconds, written N·s. The plate numbers in this study come from the recording file. [Original study and recordings](https://doi.org/10.35090/gatech/70296)

Electrodes on the skin measured the electrical activity of 16 leg muscles. Each forecast uses only earlier voltage readings. The longer model sees one second, divided into twenty sections of 50 milliseconds. The shorter model sees the last four sections. We summarize the voltage in each section by squaring the readings, averaging them, then taking the square root. We take the base-ten logarithm after setting a lower limit of one microvolt. Histories end ten milliseconds before the forecast time. Forecasts use the stored clock shared by the channels in the recording file. The original instruments sampled at different rates, and the delay between physical devices needs its own test. [Recording and processing methods](https://doi.org/10.1038/s41597-023-02840-6)

## How the forecasts were tested

Six people supplied 1,060 examples for fitting. Four other people supplied 712 forecasts on a five-degree treadmill decline. Earlier work used these people's recorded squats. Their decline recordings were held out of fitting here. We saved the forecasts and their exact sample indices before reading the force values used to score them.

Both plates had readings in all 712 forecast windows. The main comparison required each plate to show a load above 1 N·s while the other was at or below that threshold at least once. Each plate also had to exceed 10 N·s in at least one window. One recording had 173 windows where the first plate was always above 1 N·s. The second plate carried load in 131 of those windows, all while the first plate was also loaded. The main comparison therefore used **539 forecasts from three people**. The tested period comes from the original authors' annotation of the decline. The results apply to forecasting within that known period.

We tested two fixed force guesses, two linear models and six attention models. The fixed guesses use zero or the typical measured load in the fitting recordings. They both report the fitting event rate as the chance of load. A linear model multiplies each input by a learned number and adds the results. An attention model learns which earlier readings to use in each forecast. Repeating that calculation one, three or five times uses the same 9,924 learned numbers. Each learned version was fitted twice with different starting weights, and its two forecasts were averaged.

## Results

The force columns show the average size of the error in newton-seconds. The probability column scores the chance that measured impulse would exceed 1 N·s. It squares the difference between that chance and the outcome. A perfect score is zero. Each person has equal weight. The average plate score gives the two plates equal weight. The combined score adds the two measured and predicted loads before comparing them, so mistakes on different plates can cancel.

| Forecast | Plate 1 | Plate 2 | Mean | Combined | Probability score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Always predict zero force | 31.37 | 32.37 | 31.87 | 63.73 | 0.2192 |
| Typical load from fitting | 26.59 | 27.00 | 26.79 | 30.32 | 0.2192 |
| Linear fit, 200 ms | 29.29 | 27.13 | 28.21 | 21.15 | 0.2149 |
| Linear fit, 1 s | 24.41 | 28.88 | 26.65 | 43.37 | 0.1326 |
| Attention, 200 ms, 1 pass | 33.42 | 17.50 | 25.46 | 22.99 | 0.2260 |
| Attention, 200 ms, 3 passes | 29.24 | 14.70 | 21.97 | 22.45 | 0.2072 |
| Attention, 200 ms, 5 passes | 30.89 | 13.92 | 22.40 | 26.91 | 0.2003 |
| Attention, 1 s, 1 pass | 21.05 | 23.89 | 22.47 | 20.65 | 0.2170 |
| Attention, 1 s, 3 passes | 19.71 | 25.15 | 22.43 | 20.91 | 0.2291 |
| Attention, 1 s, 5 passes | 20.24 | 23.93 | 22.08 | 19.30 | 0.2184 |

- **Individual plates.** Three short passes lowered average error by 4.83 N·s against the typical-load rule. Five short passes increased force error by 0.44 N·s against three, and improved the probability score for all three people.
- **Combined load.** Five passes with a full second of muscle readings scored 19.30 N·s, against 30.32 for the typical-load rule. Combined error fell for all three people.
- **Chance of load.** The one-second linear model had the best probability score, 0.1326 against 0.2192 for the constant probability. The score fell for all three people.

To see how sensitive the result was to which people were tested, we drew groups of three from the original three, allowing the same person to appear more than once. Across 20,000 draws, the middle 95% of the change in individual-plate error for three short passes ran from a reduction of 13.50 N·s to an increase of 1.48 N·s.

We also scored all four people together after the main test. This used the same saved forecasts and all 712 windows with readings from both plates. Five passes over one second scored 19.572 N·s on the separate plates. A single pass over the same second scored 19.581, a difference of about 0.01 N·s. The 200-millisecond linear model had the lowest combined error at 18.18 N·s. The one-second linear model still gave the lowest probability error, 0.1482. The small sample and the change in rankings leave the best general choice open.

## Run a forecast

1. Install Python, NumPy and PyTorch. Use `python3 -m pip install numpy` on Linux or macOS, or `py -3 -m pip install numpy` on Windows. Install PyTorch for the same Python interpreter. [PyTorch installation](https://pytorch.org/get-started/locally/)
2. Open the extracted folder in a terminal. Run `sh "./Launch Linux.sh"` on Linux or `sh "./Launch macOS.command"` on macOS. In Windows Command Prompt, run `".\Launch Windows.cmd"`. The program reads two invented muscle histories from `EXAMPLE.npz` and prints each method's two impulse forecasts and two load probabilities in the original plate order.
3. To use a prepared recording, make a NumPy file with a `history` array of shape `(examples, 20, 16)` and a `muscles` array copied from the example. Enter the values after the 50-millisecond summary and logarithm. Pass the filename to the launcher or run `python3 predict.py your-file.npz` on Linux and macOS or `py -3 predict.py your-file.npz` on Windows. The technical edition explains how to apply the original reader.

The example ran from the extracted Linux download. The macOS and Windows launchers were checked as source. The original recordings are distributed by the authors under CC BY 4.0. The original project code and fitted checkpoint are supplied with the package licence. [Recording licence and citation](https://doi.org/10.35090/gatech/70296)
