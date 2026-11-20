# Recorded movement on a W-shaped track

A camera followed one rat, JS14, as it moved between three reward wells. Electrodes in two brain regions recorded brief electrical signals called spikes. The researchers sorted the spikes according to which neuron they likely came from. These files put the camera and spike times on the same recording clock. A model can use earlier samples to predict where the camera will find the rat a quarter of a second later.

The data come from the third of eight W-track runs that day. The archive labels the file session `01` and the run epoch `5`. The subject was a male Long–Evans rat. The camera positions are estimates of the rat’s location in centimetres, relative to the centre well. The archive gives 30 frames per second as the nominal camera rate. In this excerpt, the gap between actual samples ranges from 19.2 to 120.1 milliseconds. Each original timestamp is retained. Limb positions, muscle activity and forces are outside the measurement.

| Trips in time order | Use | Camera positions | Recorded spikes |
| --- | --- | ---: | ---: |
| 55–78 | Train | 13,175 | 61,550 |
| 79 | Gap between training and test | — | — |
| 80–89 | Test | 8,312 | 36,978 |
| 90 | Gap before the reserve | — | — |
| 91–95 | Reserved for future work | — | — |

Trip numbers are the archive’s original trial IDs. They also equal their zero-based row numbers. The gaps leave 20.79 seconds between the training and test intervals and 24.72 seconds between the test and reserve intervals. All times and positions in the files lie strictly inside a trip. This avoids counting a sample at a shared endpoint twice. Earlier work displayed trip 0 and explored trips 0–3 in a different run. All those trips fall outside this collection. The other animals in the archive also fall outside it. [Frozen split](split.json)

## Which neurons were recorded?

The archive lists 72 sorted units. A unit is a group of electrical spikes the researchers attributed to an individual neuron. The electrode records associate 41 with the prefrontal cortex and 31 with CA1, a region of the hippocampus. For each unit, the electrode row and its linked electrode group agree on the region. The files preserve the archive’s original unit IDs, the electrode labels and the group references. [Unit table](evidence/units.json)

Thirteen unit IDs have no recorded events in these 34 trips. For the other units, an empty interval also means zero spikes appeared there in the file. The archive supplies no times marking when each unit could be detected reliably. Silence, a missed event and loss of a recording cannot be distinguished from an empty interval alone. Keep each ID tied to this rat and recording. The archive supplies no basis for matching that ID to a neuron in another rat.

## Read a trip

Each `.npz` opens with Python and NumPy. This example reads the first training trip.

```python
import numpy as np

with np.load("pairs/train/trial-055.npz", allow_pickle=False) as trip:
    seconds = trip["tracking_time_s"]
    xy = trip["xy_cm"]
    ids = trip["unit_id"]
    ends = trip["spike_end"]
    row = np.flatnonzero(ids == 21).item()
    begin = int(ends[row - 1]) if row else 0
    unit_spikes = trip["spike_time_s"][begin:int(ends[row])]
```

| Array | Meaning |
| --- | --- |
| `trial_id`, `start_s`, `stop_s` | Original trial ID and its two boundaries in seconds on the file’s clock |
| `tracking_time_s`, `xy_cm`, `camera_row` | One time, X/Y pair and original zero-based camera-series row for each position |
| `unit_id`, `spike_time_s`, `spike_end` | Unit IDs in the source order, their spike times joined end to end, and the exclusive end offset of each unit’s slice within this trip |

The source stores a third camera column for velocity. This excerpt copies only X and Y. All 21,487 pairs have finite coordinates. Camera visibility, the delay between an event and a usable measurement, and any smoothing or interpolation in the original tracking pipeline remain unknown. Predictions made from this archive concern recorded positions during this run. Establishing a causal effect or a live controller would require different evidence.

## Reproduce the files

Use Python 3.12 and the packages in `requirements.txt`. From this directory, run `python build.py --check`. The program requests small byte ranges from the public archive, checks the object identity on each request and caches them locally. To start with an empty cache, give `--cache` a new directory. Running `python build.py` rebuilds the trip files in place. A manifest gives each file’s SHA-256 digest and its row bounds in the original NWB data. The archive supplies the digest for the full 28,291,364,968-byte object. The local check verifies the ranges used here. [Source manifest](manifest.json)

A range request can carry neighbouring bytes, and a timestamp search reads values on either side of its interval to locate an endpoint. The extractor supplies only the 34 selected trips. It assembles no position or spike series for either gap or the five reserved trips. Raw camera images, position-confidence scores and per-unit observation intervals are absent from the selected data. Continuous voltages were outside this extraction.

## Credit and terms

Justin Shin and Shantanu Jadhav (2024), *Single Day W-Track Learning*, DANDI Archive, version 0.240511.0307. The authors released these data under Creative Commons Attribution 4.0 International. This excerpt has the same licence. It selects one run and copies positions and spike times into separate trip files. It changes the storage format and retains the original measurement values. When reusing the data, credit the authors, cite this version, link the licence and identify further changes. [Dataset and DOI](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [Archive asset](https://api.dandiarchive.org/api/assets/4b7c7959-04b3-4817-8f96-1af6f41888c1/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
