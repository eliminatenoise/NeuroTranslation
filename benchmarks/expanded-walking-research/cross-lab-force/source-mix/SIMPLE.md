# Short force forecasts from one lab or two

The same models were also tested on 29 people walking at a separate lab in Dijon. [Dijon walking results](dijon/SIMPLE.md)

Adding recordings from a second lab lowered error on three people measured by that lab. On a treadmill at a third lab, the same change raised the average error slightly. The best average there came from a small model trained only on overground walking. [Technical edition](TECHNICAL.md) · [Exact scores](results.json)

## What the models predict

A force plate measures how hard a person pushes against it. Each forecast receives the last fifth of a second of readings from one plate. We average those readings in ten equal chunks. The forecast adds up the vertical force expected over the next tenth of a second. That sum over time is called impulse. It is measured in newton-seconds. For example, a constant push of 500 newtons for a tenth of a second gives 50 newton-seconds.

One simple rule assumes the most recent average force will continue. Another extends its recent rise or fall. The small learned model reads the ten chunks in order and carries a short summary from each chunk to the next. We trained two versions to correct the hold-steady rule. One learned from 12 people walking across a floor with plates set into it. The other also learned from six people whose recordings included jogging, running and landing from a drop. A third version learned to give the answer directly from the same two sources. [Overground walking](https://doi.org/10.1038/s41597-023-02767-y) · [Mixed activities](https://doi.org/10.1038/s41597-026-07183-6)

## What changed on new people

All eight people in the treadmill comparison came from a lab absent from both training sets. The walking-only correction missed by **8.72 newton-seconds** on average. The recent-trend rule missed by **9.64**, and the previously trained Research Edition missed by **10.69**. The walking-only correction beat the trend for four of the eight people. The estimated range of the average gain includes a loss. Adding the second training set raised the correction’s average error to **8.92**. [Treadmill recordings](https://doi.org/10.1038/s41597-026-07445-3) · [Earlier Research Edition comparison](https://github.com/eliminatenoise/NeuroTranslation/blob/e84c8aab07f4234e7f561fbbd77a2aa47cd2bc5c/benchmarks/expanded-walking-research/cross-lab-force/SIMPLE.md)

On three other people recorded in the lab that supplied the mixed activities, adding that lab’s training data lowered the correction’s average error from **3.28 to 2.95** and helped all three. The direct forecast trained on the mixture averaged **2.84**. It beat the hold-steady rule for two of the three people. The rule’s overall average was **2.98**. All the readings came from force plates.

We also tested a simpler learned correction. It gives each of the ten readings a fixed weight and adds them up. For that method, adding the second lab moved the treadmill error from **9.27 to 10.72**. On the three people from the mixed-activity lab, the errors were **4.15 and 4.16**.

We estimated the variation in the gain by drawing groups of the same size from the people in each comparison, with repeats allowed. For the recurrent correction, the middle 95% of draws gave results from **0.56 worse to 0.22 better** on the treadmill when the second archive was added. The range on the other three people was **0.19 to 0.58 better**. Those estimates describe the recordings tested. The added archive changes the activity mix, number of training examples and measuring equipment together.

These are new forecasts against two previously scored archives. The weighted corrections, recurrent corrections and direct forecast are available as research downloads. The original Research Edition and its reserved final tests are separate.

## Run an example

The browser exercise puts the seven forecasts side by side. Choose a generated loading, unloading or quiet example, then edit any of the ten earlier readings. The recorded test table stays fixed when the example changes. We used Node.js to run the page’s forecast code outside the browser on 22,767 recorded inputs. Its forecasts differed from the original predictions by at most 0.000024 newton-seconds. Choose **Download this page** to save one HTML file. Open that file in your browser for offline use. [Open the browser exercise](https://eliminatenoise.github.io/NeuroTranslation/force-forecast/)

Download and extract the bundle. The runner needs Python 3 and NumPy in the same Python environment. Open `run-macos.command` on macOS or `run-windows.cmd` on Windows, or run `./run-linux.sh` in the extracted folder on Linux. Each launcher runs the generated example. Install NumPy with `python3 -m pip install numpy` on Linux or macOS, or `py -3 -m pip install numpy` on Windows.

To enter your own readings, pass ten consecutive 20-millisecond averages in newtons, oldest first. Use positive values for upward force. In a terminal in the extracted folder, use `python3` on Linux or macOS and `py -3` on Windows.

```text
python3 forecast.py --force-n 0 0 0 20 105 280 510 640 700 680
```

The example’s numbers are generated. The test scores above come from recorded force. The extracted runner and launcher were tested on Linux. [Download the models and runner](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/expanded-walking-research/cross-lab-force/source-mix/Force-Source-Mix.zip)
