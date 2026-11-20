# Move a cylinder to a target

A participant held a cylinder and carried it to one of nine assigned targets. Cameras tracked reflective markers on the cylinder. These models read 200 milliseconds of the optical path and predict three later positions of the object. The left- and right-hand trials are separate recordings.

## Try a different destination

Open the launcher for your operating system, or open `reader/index.html`. Choose a hand and a starting recording, then type a target number. The browser runs the fitted model. When the destination changes, the forecast shows what the model predicts for the new request. A measured outcome exists only for the destination used in the recording. [Online reader](https://eliminatenoise.github.io/NeuroTranslation/target-reach/) · [3D recording](https://eliminatenoise.github.io/Interoceptomics/target-reach/)

Two clocks answer different questions. One starts at the first usable optical frame. The other starts after the tracked marker centre has travelled at least 15 millimetres from its initial position for three consecutive frames. This displacement crossing is reproducible from past observations. Neither clock establishes when the person saw the target, heard the sound or intended to move.

At 600 milliseconds on the acquisition clock, the measured mean displacement from the input cutoff was about 0.12 millimetres. Once the cylinder crossed 15 millimetres, the full model missed by **12.13 mm** on average, compared with **66.85 mm** for a stationary forecast. Giving the model the real destination beat supplying a wrong one at that later clock. Its improvement over using the same motion history alone remained uncertain. The test involved seven people who contributed no training data. [Findings and uncertainty](https://eliminatenoise.github.io/NeuroTranslation/papers/target-reach/)

## Run one forecast

The package includes the measured development and test arrays, all 24 fits across the two clocks, per-person errors and paired intervals. Python 3.11+ and NumPy suffice to run a saved fit from this folder.

    python model/kernel.py weights/crossing/full-17.json example.json

The JSON result gives three predicted X, Y, Z displacements in metres, measured from the last input position. The three rows refer to 400, 600 and 800 milliseconds from the selected clock origin. The same object, hand and early optical history can be used with the other eight target IDs.

## Reproduce the study

1. The [source guide](source/README.md) identifies the original file version, checksums, frame rate, exclusions and units. The four `.npz` source arrays supplied here are ready to use. To rebuild from original measurements use the scripts in that guide. No video is required.
2. The [fitting methods](METHODS.md) describe the three model inputs and comparators. Fit on development participants and evaluate the untouched people with the commands below. A CPU build of PyTorch is sufficient. Use one BLAS, OpenMP and Torch thread for reproducibility.
3. For the first-frame analysis, replace `train-crossing.npz` and `test-crossing.npz` below with `train.npz` and `test.npz`. Fit each clock on a separate development array and keep the output folders distinct.

    python model/fit.py source/train-crossing.npz rebuilt/crossing --threads 1 --device cpu
    python model/assess.py source/test-crossing.npz rebuilt/crossing source/train-crossing.npz rebuilt/results
    python model/native_check.py source/test-crossing.npz rebuilt/crossing rebuilt/results

[Acquisition results](results/acquisition/summary.json) · [Displacement-crossing results](results/crossing/summary.json) · [Source data](https://doi.org/10.17605/OSF.IO/J3QC8) · [Original experiment](https://doi.org/10.1038/s41597-025-05576-7)

## Attribution

Tim Sziburis, Susanne Blex, Tobias Glasmachers and Ioannis Iossifidis created the Ruhr Hand Motion Catalog (2025). The deposit is licensed under CC BY 4.0. We selected the first two recorded assignments per participant, hand and target before applying the authors’ optical exclusions. We derived a consistent marker centre, relative sample times, displacement windows, fitted models and numerical comparisons. The measurements, derived model parameters and data visualizations distributed here carry CC BY 4.0 attribution. Original project code and explanatory text are dedicated to the public domain under CC0 1.0. [CC BY 4.0](CC-BY-4.0.txt) · [CC0](LICENSE)
