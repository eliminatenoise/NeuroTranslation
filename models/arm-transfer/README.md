# A cue, four motion bins, three forecasts

A person sees an instruction to bend an elbow, turn a forearm, close or open a hand, or rest. At a quarter-second after the cue, the model has four short bins of instrument readings. It predicts the change half a second, one second and one and a half seconds later. Each forecast has three values, in the order elbow, forearm rotation, proximal index finger. The measurements came from a supported right arm and a glove. The cue and past movements are known inputs. The model has no access to the original words, EEG, future movement or a new participant's calibration. [Recording](https://doi.org/10.5281/zenodo.834976) · [Study](https://doi.org/10.1371/journal.pone.0182578)

[Development and assessment results](RESULTS.md) · [Interactive movement reader](https://eliminatenoise.github.io/NeuroTranslation/arm-transfer/) · [Research supplement](https://eliminatenoise.github.io/NeuroTranslation/papers/arm-transfer/)

## Try a forecast

Extract the entire folder. Open the launcher for Windows, macOS or Linux. It uses Node.js when available, or Python 3.10 or newer with NumPy. Each runs the invented stationary example and prints nine signed changes. From a terminal, run the following to use a different input file.

```sh
python predict.py example.json
```

Use one of the seven entries in the model's `cues` list. Enter four rows, oldest first. Each row starts with the median elbow, forearm and glove readings from eight consecutive 64 Hz samples. The last three values describe the change within that same bin, the median of its last four samples minus the median of its first four. Use the same instruments and event alignment as the original recordings. Each reading has a native instrument scale. Calibrated degrees, anatomical signs and cross-person gain are unknown. [Exact sample indices and study rules](PROTOCOL.md)

The default method is `transformer`. Set `method` to `cue`, `still`, `ridge`, `mlp`, `transformer_no_cue`, `mlp_no_cue`, `ridge_no_cue` or `unconditional` to compare the other forecasts. All accept the same cue and history. Errors in input shape, numeric type, finite values or cue identity stop the calculation. A raw feature beyond the fitting range sets `outside_fit_range` to true. The flag compares each of the 24 raw input coordinates with its observed minimum and maximum in fitting. A forecast inside that box can still describe an unfamiliar movement.

For JavaScript, load `predict.js` and pass the parsed `model.json` and input object to `CuedArmTransfer.predict(model, request)`. Node also supports `require("./predict.js").predict`. The numerical weights and training scalers are stored in JSON. Both implementations run offline. The two example histories in `parity.json` are synthetic and include expected outputs for all methods and cues.

## What learned from the seven people?

The 805-parameter Transformer learns how to combine the cue and each history bin. The cue and cutoff levels form one token. Four others describe the measured movement. Two attention heads combine them before the final layer projects the cue token to nine instrument changes. The 801-parameter MLP receives the same cue and movement coordinates. Both were initialized afresh for every person-held-out fold. In the final 80-update Transformer fit, mean squared standardized training error fell from 1.4492 to 0.7136. The query, key and value matrices, cue embeddings, positional embeddings and output projection all changed during training. Performance on new people is reported separately. [Training diagnostics](training-diagnostics.json) · [Assessment results](RESULTS.md)

## Reproduce the experiment

The original GDF files are available from Ofner and colleagues. Use the supplied downloader to place the exact motor-execution files from version 1 in a private directory. The fitting and assessment groups have separate commands. [Source and download instructions](SOURCE.md) The local source reader verifies file size, publisher MD5, channels and sample layout, and reports the recomputed SHA-256 for each file. Model fitting needs NumPy and PyTorch. Use one OpenBLAS thread, four PyTorch CPU threads and one inter-op thread for the reference configuration. The seven whole-person development folds each learn independent weights and scalers. A final fit includes S1–S7, 21 planned recordings. The freeze digest binds the code, weights, development results and participant roles. Assessment uses the separately retained digest and never updates weights. [Dataset and file list](https://zenodo.org/records/834976) · [Trial and scoring rules](PROTOCOL.md)

```sh
python study.py train /path/to/private-gdfs /path/to/new-fit /path/to/private-folds --threads 4
python study.py assess /path/to/private-gdfs /path/to/private-results.json /path/to/new-fit/freeze.json ACCEPTED_SHA256
python project_reports.py /path/to/new-fit /path/to/public-summaries --assessment-original /path/to/private-results.json
```

All participants came from one experiment at one site and used the same task design. The held-person comparison tests participant transfer within those recording conditions. The software checks whether a short history and an assigned cue predict three recorded channels under these tasks. A flat glove reading can occur with a still finger, a sensor fault or both. Judging the forecast against that flat trace can reward zero change without telling us how the finger moved. Execution-trial readings give no evidence of a biological write operation or a general-purpose interpretation of a person's words.

## Credit

Patrick Ofner, Andreas Schwarz, Joana Pereira and Gernot R. Müller-Putz released the recordings in 2017 under CC BY 4.0. This reanalysis selects the first three motor-execution runs per person, computes causal history bins and later instrument changes, fits new models and derives the reported errors. The data-derived weights and numerical results retain CC BY 4.0. The original analysis code and invented example are available under CC0. [Original data](https://doi.org/10.5281/zenodo.834976) · [Data licence](CC-BY-4.0.txt) · [Code dedication](CC0.txt)

The distributed freeze record also carries a detached Ed25519 signature from an experiment-specific key. The freeze records the exact files before the assessment data were opened. The signature covers those bytes. Keep the key fingerprint and freeze digest from the independent witness to verify their identity.

```sh
openssl pkeyutl -verify -pubin -inkey freeze-public.pem -rawin -in freeze.json -sigfile freeze.sig
```

The signed freeze identifies the original local training outputs by hash. The downloadable reports summarize people together, including cue-specific errors and paired differences sorted independently for each comparison. The public projection manifest links every summary to its original hash. To reproduce the detailed reports, generate the fitting outputs in a fresh local folder, assess from that folder and apply the supplied projection script. Individual sensor ranges and participant-linked forecast profiles remain outside this download. [Public report identities](projection-manifest.json)
