# Force forecasts for two treadmill belts

With 150 fitting windows, the average error across the two individual belt forecasts fell from **8.26 to 7.86 newton-seconds** when the fitting set drew from two labs. That average improved for eight of the nine people in the test. Using all 222 windows from both labs gave an error of **7.96**. [Technical edition](TECHNICAL.md) · [Exact scores](RESULTS.json)

[Download and extract the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/expanded-walking-research/cross-lab-force/source-mix/paired-belts/Two-Belt-Force.zip), then open **Compare Results.html** in a browser. The menus switch between individual belt errors, combined error and the comparisons between fitting sets.

## The force this study measures

An instrument beneath each belt measures how hard the walker pushes on it. The recordings mark each value by belt. Here the model forecasts the force at right angles to the belt surface, close to vertical in these recordings.

The instruments record a thousand times a second. Each forecast looks at the previous 200 milliseconds, grouped into ten averages of 20 readings. It estimates how much force will act on each belt over the next 100 milliseconds. That quantity is called **impulse**. A steady force of 500 newtons for a tenth of a second produces 50 newton-seconds, written N·s. We measured the outcome by adding the 100 readings in that next tenth of a second and multiplying by the time between readings. [Recordings and licence](https://doi.org/10.5281/zenodo.16970717) · [Recording methods](https://doi.org/10.1038/s41598-026-46937-5)

## The forecasts

- **Hold the last average.** Assume that each belt continues to carry the same force that it carried in the final 20 milliseconds of the history.
- **Damped trend.** Estimate how the force has risen or fallen across the latest five averages. Carry that change forward and gradually slow it down.
- **Trend for the total and hold the split.** Take the combined force from the trend forecast. Use the difference between the last left and right averages to divide it between the belts.
- **Research Edition.** The full NeuroTranslate 0.1 decoder reads both force histories, runs the middle part of its calculation three times, and estimates a correction to the trend. One readout, or rule for using the model's output, compares the average combined force in the first two bins with the average in the last two bins. It applies the correction when those averages differ by more than 50 newtons, which happened in 230 of the 270 test windows. The other readout uses a correction in every window. We ran the model in both belt orders, then restored left and right order before averaging the forecasts.

The new fitting step adjusts two numbers. It first chooses how much of the model's estimate to use for the total force on both belts. With the total fixed, it chooses how much of the model's estimated difference to use for the split. A split weight of about 0.73 takes the difference roughly three quarters of the way from the simple estimate to the Research Edition estimate. We chose the first weight from errors on the total and the second from errors on the individual belts.

## Fitting and testing on different people

We used one recording to verify the file layout. Five other people in the same collection supplied 150 fitting windows. The second fit used 78 of those windows and 72 from an earlier study of two different people. The third used all 222 windows. The earlier data measured vertical force. The new data measure force perpendicular to each belt. The two fitting sources also differ in participants, equipment and walking conditions. The equal-size comparison holds the number of windows fixed while those differences remain. [Additional fitting recordings](https://doi.org/10.6084/m9.figshare.19718500.v1) · [Additional study methods](https://doi.org/10.1038/s41597-022-01817-1)

For the test, nine people walked with both belts travelling at the same speed and the feedback display off. These were separate people from those who supplied the fitting windows. We forecast the next tenth of a second at 30, 40, 50 seconds and so on through 320 seconds. Each person supplied 30 windows. We saved the 270 forecasts and their exact sample numbers before reading the force values used to score them.

## Errors on the nine test participants

The error on a belt is the average size of the difference between forecast and measurement. We calculate it for each person and give all nine people equal weight. The average belt error gives the left and right results equal weight. The **combined** error compares the sums of the two belts. Some mistakes cancel in that sum. For example, a forecast that is 4 N·s too high on one belt and 4 N·s too low on the other gets the total right.

| Forecast | Left (N·s) | Right (N·s) | Average belt (N·s) | Combined (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Hold the last average | 8.23 | 8.73 | 8.48 | 7.02 |
| Damped trend | 8.14 | 8.54 | 8.34 | 6.99 |
| Trend for the total and hold the split | 8.29 | 8.85 | 8.57 | 6.99 |
| Research Edition, changing force | 8.09 | 8.43 | 8.26 | 6.76 |
| Research Edition, all windows | 8.07 | 8.47 | 8.27 | 6.96 |
| One lab, changing force | 8.09 | 8.43 | 8.26 | 6.76 |
| One lab, all windows | 8.07 | 8.47 | 8.27 | 6.96 |
| Two labs, 150 windows, changing force | **7.63** | **8.09** | **7.86** | 6.76 |
| Two labs, 150 windows, all windows | 7.65 | 8.13 | 7.89 | 6.96 |
| Two labs, 222 windows, changing force | 7.74 | 8.17 | 7.96 | 6.76 |
| Two labs, 222 windows, all windows | 7.75 | 8.21 | 7.98 | 6.96 |

The 150-window mix lowered average belt error by **0.40 N·s**, or about **4.8%**, when the correction was applied to changing force. It lowered left-belt error for all nine people and right-belt error for eight. To see how much that average depended on the people tested, we drew 20,000 groups of nine from the original nine, allowing the same person to appear more than once in a group. The middle 95% of those draws gave an improvement of **0.23 to 0.55 N·s**. When the correction was applied in every window, the reduction was **0.38 N·s**, with a range of **0.19 to 0.56**.

Using all 222 windows gave lower average belt error than using one lab. It raised error by **0.09 N·s** relative to the equal-size mix for each type of readout. Those ranges are **0.04 to 0.14 higher** for changing force and **0.02 to 0.15 higher** for the correction used in all windows. These are differences among three specified fits on one small test group.

Each fit kept the full Research Edition estimate of the combined force. That is why the one-lab and two-lab versions have the same combined error within each readout. For the combined measurement, the changing-force readout beat the damped trend for all nine people. The two-lab gain in the other column came from how the prediction divided force between the belts.

## Run the fitted readouts

1. Install Python 3 and open the extracted folder. Open **Launch Linux.sh**, **Launch macOS.command**, or **Launch Windows.cmd** for your system. You can also run `python3 apply_readouts.py` in a terminal in that folder. Use `py -3 apply_readouts.py` on Windows.
2. The example starts with two invented cases in `EXAMPLE.json`. Each case supplies four forecasts. The program prints all 11 outputs as left and right impulse pairs in N·s.
3. For your own forecasts, copy those four fields and supply the hold and trend estimates and the two Research Edition estimates. Put the left belt first in each pair. Use `python3 apply_readouts.py your-file.json` or `py -3 apply_readouts.py your-file.json` on Windows. `READOUTS.json` gives the decoder and original force readout identities.

The example and all saved weights run with Python's standard library. To fit new weights, use NumPy, your forecasts, the matching measured impulses, and the participant label for each case. The archive includes the fitting function and the technical edition gives its inputs. The extracted Linux launcher and the Chromium menus were run. The macOS and Windows launchers were checked as source.

Project code and fitting coefficients use CC0. Obtain Jin and colleagues' recordings under CC BY 4.0 and Van der Zee and Kuo's additional fitting recordings under CC0. [Jin data](https://doi.org/10.5281/zenodo.16970717) · [Van der Zee and Kuo data](https://doi.org/10.6084/m9.figshare.19718500.v1)
