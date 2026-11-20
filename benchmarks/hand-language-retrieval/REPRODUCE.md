# Reproduce the fitted study

For the example search, use the weights already in `bundle/fit`. The gallery in `bundle/gallery.npz` contains 24-by-16 distance sequences for the five eligible intervals of R031-12July-SmallPrinter. Their order and interval IDs are in `bundle/gallery.json`. Each filename in the fitted seal has a SHA-256 digest. The ranker verifies those digests before it uses the files. The same candidates are supplied as normalized 64-value ridge and 32-value attention vectors in [embeddings](embeddings/candidates.json). To regenerate them, run `python gallery_embeddings.py --output recovered-embeddings`.

## Rebuild from the included distance measurements

The compact feature edition contains the same 146 training and 60 assessment sequences, calibrated in metres, the independently written descriptions, the original interval IDs, and the timing fields needed by the comparison models. Its 24-by-16 arrays preserve missing values and their original single-precision representation. A round-trip check compared every finite value, every missing position and every metadata field with the source-derived model inputs. The compact route verifies the published manifest digest and runs the same fitting and scoring functions. A separately prepared feature edition requires the explicit `--allow-custom-features` option. No video, audio or account access is required.

```sh
python features.py fit --output recovered-features
python features.py assess --output recovered-features
python rank.py "check the printer tray" --bundle recovered-features
```

The assembly step read the source recordings once more to check that the recovered features had identical values. The dedicated software test fitted and scored an artificial compact edition and compared its weights and outputs with the original-input route. Runtime and hardware versions can affect the last floating-point digits. [Feature edition and source seals](features/manifest.json)

## Rebuild from the official data

Use a clean copy of this directory and install `requirements.txt` in a Python environment. The source reader fetches exact public byte ranges from the 235 GB hand archive. It checks the remote object size, ETag and each selected TAR header before parsing the rows. The annotation reader checks SHA-256 for each selected source record. The frozen split and indexes restrict this study to 29 training and eleven review recordings. The ten reserve recordings have no acquisition route in these commands. The original record-level partitions came from the split the dataset publishers label v1.2. [Data and schema](https://holoassist.github.io/data_links/README.html) · [Official split](https://holoassist.github.io/label_files/data-splits-v1_2.zip)

```sh
python source/index_source.py labels
python source/read_hands.py --roles train --workers 2
python fit.py --data source --split source/SPLIT.json --output recovered --threads 1
python source/read_hands.py --roles review --workers 2
python score.py --data source --split source/SPLIT.json --output recovered --threads 1
python rank.py "check the printer tray" --bundle recovered
```

The fit command requires a fresh destination. It refuses a changed real split. The score command verifies the training ledger, code, design and model digests before opening the selected review streams; it refuses to overwrite a previous assessment. A re-run on another computer or library build can differ in floating-point arithmetic. The original run used CPython 3.13, NumPy 2.5.3 and PyTorch 2.14.1+cpu. It used one numerical worker and one inter-op thread. Dataset indexing and inference require no GPU.

The ridge model keeps up to 512 words from training descriptions, weighted by inverse document frequency. It fits the phase-wise mean, standard deviation, average absolute step and endpoint change for each of 16 standardized geometric channels. Multi-output ridge uses penalty 2 with an unpenalized intercept. Prediction and candidate are compared by cosine after training-only descriptor scaling. The attention model uses two one-block encoders, width 32, four attention heads, a learned position for each word or phase, and normalized projections. It fits within-recording pairings for 30 epochs. Each wrong-pair model uses a fixed derangement within each training recording.

Frozen recipes live in [design.json](design.json), [the source addendum](source-addendum.json) and [the sensor-time addendum](time-addendum.json). The result file includes all per-family values and bootstrap comparisons. For each paired interval of uncertainty the script draws 10,000 samples, with replacement, of the same six family differences. These intervals are descriptive of this small sample.

## Exercise the pipeline with invented inputs

```sh
python fixture.py toy
python fit.py --data toy --split toy/SPLIT.json --output toy-result --threads 1 --fixture
python score.py --data toy --split toy/SPLIT.json --output toy-result --threads 1 --fixture
```

The artificial data exercise repeated descriptions, tied ranks, missing joints, repeated sensor timestamps and overlapping time intervals. Their scores are software test results. The measured evaluation appears in [results.json](results/results.json).
