# Rebuild the paired handle, cue and area 2 windows

Raeed Chowdhury, Joshua Glaser and Lee Miller recorded sorted neural activity and a macaque’s handle and arm movement. Use the single selected MAT session from their public release. The downloader requests only its original stored archive member (179 MB). A verified local copy can be supplied directly. The importer uses Python, NumPy and SciPy. Its SHA-256 check covers the MAT file and the frozen chronological partition. [Data](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original paper](https://doi.org/10.7554/eLife.48198) · [Authors’ analysis](https://github.com/raeedcho/s1-kinematics)

From this folder run the following commands. The reader will write NPZ arrays, source audits and the single illustrated held-trial excerpt in the destination directory. Keep both events from each original trial together. The test flag is explicit so reproducing the completed study is a deliberate step.

```sh
python fetch.py raw
python reader.py raw/C_20170912_COactpas_TD.mat trial-split.json . --stage train
python reader.py raw/C_20170912_COactpas_TD.mat trial-split.json . --stage validation
python reader.py raw/C_20170912_COactpas_TD.mat trial-split.json . --stage test --release-test
```

The task stages were 324 original trials for training, 108 for validation and 108 for the later test. Four originals across the full partition failed the event-order or direction checks. Look at each stage audit for the exact window and donor support. The reader takes positions in the handle encoder frame (cm), counts from positive-sort-code units on the prior bins, and event information strictly before each token endpoint. The optional tracked landmarks use another frame (shoulder-relative metres). These are processed, retrospectively synchronized measurements. [Full input schema](SCHEMA.md)
