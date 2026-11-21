# Can worm recordings help forecast a fish’s fluorescence?

A calcium-sensitive protein glows as calcium levels change in a cell. Take four readings of that glow, about 1.2 seconds apart. How close can you get to the next reading? The test gives a model examples from one zebrafish, substitutes worm recordings for one quarter of those examples, and checks both versions on seven other fish. The simplest forecast carries the latest reading forward.

Atanas, Kim and colleagues imaged freely moving *Caenorhabditis elegans*. This experiment uses eight of their baseline recordings. Haesemeyer and Balakrishnan imaged the forebrain of larval zebrafish during a changing temperature stimulus. We use the first imaging plane in the selected fish recordings. The fish strain expresses nuclear GCaMP6s, the worm strain nuclear GCaMP7f. These different calcium reporters and the archives’ signal extraction both affect the traces. [Worm study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10836760/) · [Worm archive](https://doi.org/10.5281/zenodo.19388374) · [Zebrafish archive](https://dandiarchive.org/dandiset/000235/0.230316.1600)

## What went into each forecast?

Each region of interest is a patch of the image with its own brightness trace. The first 30 seconds of that trace set its scale. We subtract its average over that interval and divide by its standard deviation. A forecast error of one unit then means one standard deviation of that region’s initial brightness. Every forecast starts after this calibration period. The four model weights stay fixed across regions and animals. The worm archive supplies a timestamp for each frame. The fish archive stores its starting time and sampling rate, from which frame times follow. The code locates frames within 0.36 seconds of each requested lag and horizon and drops a case if a value is missing. It never fills a gap between frames.

All four fits use the same four-weight regression and 1,024 equally weighted examples. They share 768 examples from the first fish, taken before 120 seconds from every second region in archive order. The remaining 256 examples come from one of four places.

| Training condition | Source of the last 256 examples |
| --- | --- |
| Fish only | Unused examples from that same fish, period and set of regions |
| Fish and worms | 32 examples from each of eight worms |
| New fish regions | Previously unused regions from that same fish and period |
| Later fish observations | The original set of regions from that same fish, from 120 seconds onward |

Each model makes one prediction for each eligible held-out fish, region and time. Within a fish, we average the squared errors for each region and give each region equal weight. We then give each fish equal weight. This keeps one recording with many eligible observations from dominating the result. The primary comparison subtracts fish-only mean squared error from fish-and-worm mean squared error. A negative difference favors the substitution. [Frozen comparison and scoring rules](protocol.json) · [Animal split](split.json)

## What happened on the seven fish?

Substituting worm examples lowered average squared error by **8.36%**, from **2.091 to 1.916** in squared calibration units. Four fish improved and three worsened. The largest gain came from Fish13. Leaving that fish out reduced the advantage to 0.072 units. Leaving out any one of the seven still gave the mixture a lower mean squared error. The independent review added a descriptive paired 95% *t* interval for the seven animal differences, from −0.554 to +0.205 units. With this few fish, the data remain consistent with a gain or a loss on further animals.

| Held fish | Fish only | Fish and worms | Difference |
| --- | ---: | ---: | ---: |
| Fish02 | 0.955 | 0.635 | -0.320 |
| Fish13 | 6.221 | 5.428 | -0.793 |
| Fish31 | 1.610 | 2.008 | +0.398 |
| Fish32 | 1.478 | 1.488 | +0.009 |
| Fish41 | 1.629 | 1.146 | -0.484 |
| Fish47 | 1.593 | 1.799 | +0.206 |
| Fish58 | 1.147 | 0.906 | -0.241 |

Carrying the last observation forward gave 2.385. Spending the replacement examples on new regions of the training fish gave 2.060, and spending them on later observations from that fish gave 2.196. Each held fish contributed 32 regions and 125 forecast times, for 4,000 forecasts per animal. The 28,000 forecasts come from seven animals.

On the fish clock, the first forecast used observations through 30.199 seconds to predict the reading at 31.457 seconds. Every fish forecast reached about 1.258 seconds ahead. During the first scored interval, from 30 to 60 seconds, the mixture’s squared error was slightly higher (1.235 versus 1.230). Its advantage was largest from 120 to 180 seconds (2.990 versus 3.370). The model weights were already fixed, so those differences describe the recording intervals. [Full per-fish scores, time ranges and controls](results.json) · [Fitted weights](fit.json)

## Reproduce the comparison

For a full replay, install NumPy from `requirements.txt` and the four extraction dependencies listed in the [recording sources](sources/README.md). From this directory run `python replay.py my-replay`, using a new directory name. It fetches the public training slices, fits the model, freezes its coefficients, then fetches the seven held fish and scores them. It verifies the selected input slices against the study digests. The fitted coefficients and individual fish results are saved as `my-replay/fit.json` and `my-replay/results.json`. The steps below also work separately with prepared inputs.

Use Python 3.12 or later with the NumPy version in `requirements.txt`. The reference run used Python 3.13.15. Each input directory contains one NumPy archive named for each animal in `split.json`, with numeric arrays `time_s` (seconds, one per frame) and `fluorescence` (frames by regions). Use the source-preparation materials distributed with this experiment for the archive versions, source paths, time crops and cell order. File hashes in `fit.json` and `results.json` identify the exact input packets.

```sh
python -m pip install -r requirements.txt
python forecast.py fit --split split.json --files train --out my-fit.json
```

For a new run, freeze the fit file and record its SHA-256 before opening the held fish. Pass its 64-character digest in place of `DIGEST` below. Different numerical libraries can differ in the final decimal places of the coefficients and therefore in the byte-level digest. The `fit_sha256` in the published results identifies the supplied reference fit.

```sh
python forecast.py evaluate --split split.json --files held --fit my-fit.json --fit-sha256 DIGEST --out my-results.json
```

The fit file records coefficients and hashes for the shared core and each replacement group. The results contain per-animal losses, calibration and timing checks, paired-row hashes, and descriptive scores by time and recent brightness change. Leaving out each fish in turn shows how much that animal influences the primary comparison.

## What the comparison can settle

The mixture changes the animal count from one to nine. It also changes species, indicator, laboratory, behavior and preprocessing together. The extra-region and later-time controls measure variation available within the one training fish. Separating the effect of species from the effect of additional animals would require more independent training fish. The causal input order applies to the archived traces. The worm archive includes retrospective registration, interpolation of missing traces and bleaching correction using the recording. A model using these traces in chronological order still needs a separate test on signals extracted in real time. These observations measure fluorescence. Claims about spikes, development, muscles or shared evolutionary mechanisms require different measurements.

Original forecast code is distributed under CC0. The worm archive uses CC BY 3.0 US and the fish archive uses CC BY 4.0. The source authors retain attribution. This analysis crops and standardizes the archived signals and reports derived forecasts. [Code dedication](LICENSE-CODE) · [Worm data license](https://creativecommons.org/licenses/by/3.0/us/) · [Fish data license](https://creativecommons.org/licenses/by/4.0/)
