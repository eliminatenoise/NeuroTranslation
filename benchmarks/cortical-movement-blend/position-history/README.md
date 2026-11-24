# Hand position from recent movement and brain activity

[Simple edition and interactive comparison](https://eliminatenoise.github.io/NeuroTranslation/hand-position-forecast/) · [Technical edition](https://eliminatenoise.github.io/NeuroTranslation/hand-position-forecast/technical.html) · [Offline browser ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cortical-movement-blend/position-history/Hand-Position-Forecast-offline.zip)

The equal blend takes the midpoint between a forecast from recent hand motion and an earlier NeuroTranslate forecast from recorded brain activity. On three previously evaluated recordings from one macaque, this fixed blend reduced the average ending-position error by 1.07, 0.30 and 1.74 mm compared with extending the recent speed and direction. Predicting how far the hand moved is a separate test. On 19 August the blend increased that error by 0.08 mm.

## Open offline

Extract the ZIP into one folder. Open the launcher for Linux, macOS or Windows. You can also open `index.html` from the extracted folder in a browser. The comparison and coordinate editor run from the local files. The editor starts with invented numbers. [Download the ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/cortical-movement-blend/position-history/Hand-Position-Forecast-offline.zip)

## Recalculate the archived scores

Download `replay.py`, `requirements.txt`, `results.json` and `issued-forecasts.npz` from this folder. The forecast packet contains the original and previously blended forecasts from three fixed models and exact row identifiers. Supply the original recordings separately for about 18.7 GB in total. Keep these filenames.

| Day | Original NWB file |
| --- | --- |
| 12 August 2010 | [sub-Nitschke_ses-20100812_behavior+ecephys.nwb](https://api.dandiarchive.org/api/assets/bceb8ef2-13b0-42b1-9d18-086876f603e1/download/) |
| 19 August 2010 | [sub-Nitschke_ses-20100819_behavior+ecephys.nwb](https://api.dandiarchive.org/api/assets/4fad0016-9d12-48df-8cbc-beb198d78528/download/) |
| 10 September 2010 | [sub-Nitschke_ses-20100910_behavior+ecephys.nwb](https://api.dandiarchive.org/api/assets/fd725c07-6804-4954-a6c4-e03af015a057/download/) |

Use Python 3.11 or later. Open a terminal in the folder containing `replay.py`.

```sh
python3 -m pip install -r requirements.txt
python3 replay.py /path/to/recordings
```

On Windows, use `py -3` in place of `python3`. Append `--day 2010-08-12` to verify just the first recording. The script checks the original bytes, the coordinate frame and the recorded time for each forecast. It recalculates the two mean errors and the paired ranges for all six movement groups. It prints the source counts and the maximum difference from the published numbers.

The source recordings are Churchland, Cunningham, Kaufman, Foster, Nuyujukian, Ryu and Shenoy, *Neural population dynamics during reaching*, DANDI 000070 version 0.261122.2046, CC BY 4.0. This folder distributes derived forecast outputs and the row identifiers for recomputing the result. Project-authored code is CC0. [Dataset and citation](https://doi.org/10.48324/dandi.000070/0.261122.2046) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Project licence](../LICENSE) · [Earlier fitted model](../)
