# Where will one body marker move?

A camera tracks a reflective dot on someone walking. Give the model nine positions of that dot, one every 50 milliseconds, and it forecasts how far the dot will move along each laboratory axis in the next 200 milliseconds. It needs neither the marker’s name nor another part of the body. [Try the forecast](https://eliminatenoise.github.io/NeuroTranslation/shared-motion/#point-motion)

We fitted the rule using the outer ankle, outer knee and thumb side of the wrist on each side of the body. Ten other walkers then supplied 30 walks. We asked how the rule performed on those same six locations, and separately on the 46 locations it had never used for fitting. Those 46 include the heels, toes, pelvis, trunk, elbows and hands. Each walker counts equally, as do the different locations within that walker. The test participants also contributed to earlier walking studies.

| Forecast from a single marker’s history | 46 locations withheld from fitting | Six locations used in fitting |
| --- | ---: | ---: |
| Keep the dot still | 127.64 mm | 129.71 mm |
| Continue the latest velocity | 43.29 mm | 54.90 mm |
| Repeat its last 200 ms of travel | 60.83 mm | 76.72 mm |
| Linear fit to recent motion | 30.64 mm | 34.67 mm |
| Compare with examples of recent motion | **28.73 mm** | **30.82 mm** |
| Use the trained movement encoder | 31.00 mm | 32.98 mm |
| Shuffle that encoder’s weights before fitting | 30.20 mm | 31.59 mm |

Each number is the average distance between the forecast point and the observed point. The rule using the shared encoder beat simple velocity by about 12 mm at the withheld locations. It missed by 2.28 mm more than the example-based comparison, with a 95% interval across walkers of 1.85 to 2.77 mm more. Shuffling the encoder weights also gave smaller average errors. Neither test set met the prespecified requirement for an advantage from the trained encoder. The 28,152 marker windows at the withheld locations came from ten people, and the uncertainty calculation uses people as its independent units. [Errors by location and uncertainty](results.json) · [Fixed study design](PROTOCOL.md)

Schreiber and Moissenet recorded the motion of markers attached to the skin. Before releasing the files, the authors reconstructed missing trajectories using information from other markers and smoothed positions with a filter that uses samples before and after each time point. Our forecast reads only one stored marker’s past positions. Reproducing a 200 ms lead on a live camera would require a separate test of the camera and its processing. The walking figures also give no estimate of the force from a muscle or the activity of a nerve. [Original study](https://doi.org/10.1038/s41597-019-0124-4) · [Version 8 walking measurements](https://doi.org/10.6084/m9.figshare.7734767.v8)

## Try a point

From the parent model folder, with Python and NumPy installed, run the command below. The built-in example uses invented positions. Its forecast is **65.04 mm on X, −3.13 mm on Y and −4.61 mm on Z**. Use the same coordinate system and units throughout. Negative values simply mean the marker is predicted to move in the decreasing direction of that axis.

```sh
python predict.py point-motion/example.json
```

You can choose `stationary`, `velocity`, `previous`, `linear`, `shared` or `shuffled` in the example. The radial comparison uses 64 individual training windows as centres. Its published score is included in the table. To run it, obtain the original data and reproduce the full fit below. The downloadable checkpoint contains the six methods that can run without those individual training windows. [All six example outputs](example-results.json)

## Reproduce the full comparison

Download the DOI’s version 8 ZIP and the data paper’s Supplementary Table 2 Word file. Obtain the preceding shared checkpoint. Set the environment variable `OPENBLAS_NUM_THREADS=1` for the reproduction and install NumPy and ezc3d. The study uses the existing verifiable preparation tool. Run the commands below from the parent model folder. Replace the example paths with your own paths and keep the raw recordings outside the public project. [Parent checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/bb06ce34bf2f06e5af3857c1964147fd53747593/models/neurotranslate-0.0/movement-weights.npz) · [Original supplementary table](https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx)

```sh
python right-plate/prepare_source.py source.zip supplement.docx walking-data train
python point-motion/study.py fit walking-data/train parent.npz complete-fit.npz
python right-plate/prepare_source.py source.zip supplement.docx walking-data assessment --fit-seal complete-fit.npz --fit-seal-sha256 9d129c87833b768536bd74dd8a88fe1f0b3703a22e59b1e54316d824e619be79
python point-motion/study.py assess walking-data/assessment complete-fit.npz results-rebuilt.json
python point-motion/public_checkpoint.py complete-fit.npz public-model.npz
```

The fit uses 11,310 marker windows across 90 walks from 30 people. The public export retains every earlier numerical tensor and adds 14 trained arrays. The source fingerprints, fitted model fingerprint and site names accompany the code. The six public outputs use the same calculations as their counterparts in the full fit. [Fit receipt](fit.json) · [Landmark names](landmarks.json)

Céline Schreiber and Florent Moissenet released the Rehazenter walking measurements under Creative Commons Attribution 4.0. This analysis selects one walking condition, builds position histories, fits readouts and compares their errors. Retain the authors’ attribution with the data-derived weights and results and identify any further changes. Project-authored software and invented examples carry the project’s CC0 dedication. [Original licence and citation](DATA-LICENCE.txt) · [Shared checkpoint notices](../NOTICE.md)
