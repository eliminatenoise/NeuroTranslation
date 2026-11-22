# Try the compact walking model

1. [Download the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/Compact-walking-preview.zip) and extract the whole folder.
2. Open **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. You can also open **index.html** directly in a desktop browser with JavaScript enabled. Keep the files together. The demo runs offline.
3. Choose **Heel positions only** or **Heel positions and vertical force**, then move the sliders. The default averages two training runs for that input. Choose a single run to see its forecast.

These four models use the NeuroTranslate 0.0 attention block to weigh earlier readings. The sliders create 200 milliseconds of invented walking readings. The model looks 100 milliseconds ahead and estimates each heel's movement, force impulse (vertical force added up over time), and the chance that a foot starts bearing weight. The browser averages movement in each direction, impulse and probability after each run produces its own forecast. The demo inputs have no measured next step to score.

## Comparison on recorded walks

This comparison used 16 walkers at a separate lab in Utah. Each recording was labelled **0.6 metres per second** and was kept out of fitting. The models made forecasts at the same 2,052 times. The table uses original calibrated force and the same later measurements for every method. Each walker counts equally within each measure.

| Forecast | Heel error (mm) | Impulse error (N·s) | Load chance error |
| --- | ---: | ---: | ---: |
| Simple physical forecast | 31.5750 | 9.6866 | 0.076722 |
| Fixed Research Edition blend | 31.4145 | 9.7494 | 0.072049 |
| Compact heel positions only, two-run average | 23.6755 | 16.3527 | 0.066044 |
| Compact heel positions and force, two-run average | 23.8788 | 7.1270 | 0.063780 |

Lower errors are better. Scores cover 4,069 heel forecasts and 3,526 impulse forecasts from all 16 walkers, and 2,619 load chance forecasts from 15 walkers. Each count is for one foot at one forecast time. The load chance score averages squared differences between the forecast probabilities and whether loading began.

The simple forecast carries forward recent heel motion and the last average vertical force, and uses the rate of load starts seen during fitting. The Research Edition blend combines its forecasts with that reference using fixed weights. Its fitting history differs from the two compact variants, which used the same Kuopio fitting histories as each other.

Adding force to the compact fit lowered mean impulse error by **9.23 N·s** and lowered that error for all 16 walkers. The paired 95% interval was **6.94 to 11.37 N·s lower**. Heel error was 0.20 mm higher on average, with a paired interval from 1.26 mm lower to 1.97 mm higher. The result describes these recorded walks at one speed.

## Model files and credits

The [model files](model/) contain the four checkpoints, which are the weights saved after fitting. Each stores 9,450 parameters as 32-bit numbers in a Safetensors file. The browser has a copy of these weights in `weights.js`. The model folder also contains the constants and source fingerprints.

The project's contributions to the code and fitted model files are available under [CC0 1.0](LICENSE). The source recordings have their own terms. [Dataset credits](DATASET-CREDITS.md)
