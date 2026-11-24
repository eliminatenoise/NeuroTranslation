# Forecasts from a force plate and a waist watch

For the force plate, holding the latest reading steady gave the smallest average miss across the whole test. For the waist watch, both learned methods reduced the error by about 40% compared with holding the latest average steady. Ridge regression scored 0.306853 radians per second. The attention model was close at 0.307716. [Exact results](results.json) · [Technical edition](TECHNICAL.md)

## What the devices measure

A force plate measures how hard the ground pushes back. The watch measures how fast the device turns in three directions. Those are different measurements with different units. The recorded tasks were walking, jogging, running, heel drops and step drops. We used one person to check the recordings, six different people to train the two models and three other people to test them. [Study](https://doi.org/10.1038/s41597-026-07183-6) · [Source archive](https://doi.org/10.5281/zenodo.17376717)

The experiment asks what each device will measure next from its own earlier readings. The watch and plate started their recordings separately. The study lined them up afterward using what happened in the recordings, so we ran the tests on their own clocks. The watch result is about how fast the device turns at the waist. Wrist recordings had gaps longer than a second in 154 of 460 files. At the waist there were 13 such files out of 451. The comparison uses the waist and force files.

## How we made the forecasts

Each model sees one fifth of a second of earlier readings. We split that time into ten groups and calculate a mean for each group. The force plate recorded one value every millisecond. Its target adds 100 later readings and divides by 1,000 to measure *impulse*. If the ground pushes up with 300 newtons for a tenth of a second, the impulse is 30 newton-seconds. We measure the average size of the force forecast’s miss.

The watch readings arrive at slightly different intervals. We schedule forecasts 400 milliseconds apart, then use the first recorded sample at the scheduled time or up to 25 milliseconds later. When we take an average, each reading counts until the next one arrives. Only earlier samples contribute to the ten input averages. The sample at the forecast time begins the target for the next tenth of a second. We leave out a window if it has a gap longer than 25 milliseconds or if the reading at a needed cutoff would be more than 25 milliseconds old. A watch input includes six readings in each group: acceleration in three directions, then turning rate around three axes.

The same two basic rules apply to both devices. One holds the most recent average steady. The other looks at the last two averages and extends the rise or fall. Ridge learns a weighted sum of the earlier readings and discourages very large weights. The attention model learns to focus on parts of the earlier history. It has separate inputs and outputs for the plate and watch, with one shared part that processes both. Training used 5,763 force examples and 5,058 waist examples, and the training program made 240 updates to the model’s 9,220 values.

## How the forecasts did

We saved the forecasts before decoding the readings used to check them. All methods were compared on the same usable windows. We averaged errors within each recording, then within each person, and gave the three people equal weight. We scored 2,537 force windows from 128 recordings. At the waist we scored 1,561 of 1,573 forecasts from 102 recordings. Twelve lacked a usable 100 millisecond follow-up window, and another recording failed its clock check before any predictions were issued. To combine the three mistakes on the watch’s turning axes, we square them, average them and take the square root.

| Method | All force (N·s) | Latest mean ≥20 N (N·s) | Latest mean <20 N (N·s) | Waist (rad/s) |
| --- | ---: | ---: | ---: | ---: |
| Keep the latest average | **2.979701** | 20.106671 | **0.635377** | 0.516938 |
| Extend the recent trend | 4.081067 | 25.460167 | 0.744325 | 1.309280 |
| Ridge | 4.239630 | **18.202190** | 1.783313 | **0.306853** |
| Shared attention | 3.900747 | 19.607338 | 1.431896 | 0.307716 |

The latest-average rule led on force for all three people. Ridge led the force comparison on the 372 windows where the last measured average was at least 20 newtons. The latest-average rule led on the 2,165 windows below that threshold. At the waist, both learned methods beat the latest-average rule for all three people. Ridge edged attention for two. This measures short forecasts from stored readings for those three held people. [Exact aggregate scores](results.json)

## Try the examples

Open the browser preview and choose **Force plate** or **Waist watch**. The graph shows a generated example from the last fifth of a second. Choose **Edit earlier readings** to change a value, or click a place on the graph to go straight to that reading. The four forecasts update as you type. With the waist watch selected, use **Input channel** to choose which of its six readings to plot and edit. The forecast table shows the three directions in which the watch can turn. **Restore example** brings back the original values for the device you are viewing. [Browser preview](https://eliminatenoise.github.io/NeuroTranslation/walking-force/force-and-waist/)

Open **Results on recorded data** to see the scores from the three held people. When viewing force, you can see all the scored windows or split them by whether the latest force average reached 20 newtons.

The browser package works from a folder after extraction. Open `index.html` in your browser or use **Open on Linux.sh**, **Open on macOS.command** or **Open on Windows.cmd**. The page carries the same trained weights as the version that runs from the command line.

For the command-line program, extract `Native-Force-and-Waist.zip`. Use `Run-Forecasts.sh` on Linux, `Run-Forecasts.command` on macOS, or `Run-Forecasts.cmd` on Windows. You need Python 3.10 or later and NumPy. To install NumPy, enter `python3 -m pip install numpy` on Linux and macOS, or `py -3 -m pip install numpy` on Windows. If Windows has `python` and cannot find `py`, use `python` in place of `py -3`. The program runs locally and prints four forecasts for each of two generated histories.

To try your own readings, save an input called `history.json` in the extracted folder. Run `python3 run_forecast.py --input history.json` on Linux and macOS or `py -3 run_forecast.py --input history.json` on Windows. Give the file a `task` of `force` or `waist` and a `history` with ten rows, starting with the oldest. For force, each row holds one average in newtons. For the waist watch, each row holds acceleration X, Y and Z in units of gravity followed by turning rate X, Y and Z in radians per second. Each row summarizes 20 milliseconds. [Technical instructions](TECHNICAL.md)
