# Reproduce the stride forecast

The ready-to-run weights need Python and NumPy. To repeat the study from C3Ds, install NumPy, ezc3d and CPU PyTorch in a suitable Python environment. Keep raw recordings and fitted-study output outside this package. Source downloads fetch only the individually listed trial URLs. Each original is checked against the published SHA-256. [Original recordings](cohort.json) · [Fresh-source checksums](fresh-hashes.json) · [Terms](RIGHTS.md)

```sh
python -m pip install numpy torch ezc3d
python test_forecast.py
python acquire.py train study/raw-train study
python prepare.py train study/raw-train study
python fit.py study --threads 2
python seal.py study
python acquire.py fresh study/raw-fresh study
python prepare.py fresh study/raw-fresh study --extra-hashes study/fresh-hashes.json
python assess.py study fresh
python acquire.py previous study/raw-previous study
python prepare.py previous study/raw-previous study
python assess.py study previous
```

The archived run used ezc3d 1.7.2 and NumPy 2.5.5 for frame preparation and assessment, PyTorch 2.14.1+cpu and NumPy 2.5.3 for fitting. Library versions and serialization can affect byte hashes in a new run. The public study lock identifies the files used for the reported scores. Each new fit creates its own lock before assessment. The gallery in that lock is calculated from the training originals. [Recorded fit and evaluation hashes](study-lock.json)

The frozen protocol specifies the architecture, normalized coordinate system, two seeds, optimizer, baseline definitions and exact grouping. Both models trained from scratch for 850 batches of 48. Sampling equally weighted the six source group numbers, then recordings, then windows. A forecast can put the foot in the right place relative to the waist while moving the waist too far across the room. The results report the first two separately over all twelve times. [Protocol](protocol.md) · [Training source](fit.py) · [Scoring source](assess.py)

| Source role | Recordings scored / chosen | Scorable / past eligible / scheduled windows | Source group numbers scored |
|---|---:|---:|---:|
| Fit | 29 / 31 | 1,524 / 1,710 / 1,712 | 6 |
| Fresh assessment | 12 / 12 | 351 / 423 / 423 | 6 |
| Previously inspected assessment | 8 / 8 | 830 / 878 / 878 | 3 |

Training trials 09_02 and 09_03 ended before a complete 600 ms target followed a complete 500 ms history. They contributed no fitted windows. In each test set every scheduled history was usable, while some had no complete future. The historical reserve groups 08 and 141 were excluded throughout. The public coverage files retain each actual native frame rate, first and last source frames, input hash and window counts. [Training](train-coverage.json) · [Fresh](fresh-coverage.json) · [Previously inspected](previous-coverage.json)

The package ships the tagged and movement-only network weights plus weighted ridge. The ridge coefficient matrix has 627 rows (eleven 57-coordinate poses) and 684 columns (twelve future residual vectors). Apply the bias after matrix multiplication. Restore coordinates with the reference decoder. The retrieval control uses the training gallery produced by preparation. On four training prefixes the two NumPy exports matched the corresponding PyTorch residual coordinates within 0.00022 mm. That checks the numerical export. Held-out motion error is reported in the main results. [Reference code](forecast.py) · [Results](README.md)
