# Prepare the fingertip touch recordings

This recipe forecasts the number of spikes in one human sensory afferent over a 20 ms interval. A robot loads a supported fingertip while a median-nerve electrode records a single afferent. The inputs are plate force, previous spikes and elapsed trial time. The source makes no simultaneous measurement of voluntary movement. Optical strain requires separate spatial and temporal registration.

**Source and licence.** Benoit P. Delhaye, Ewa Jarocka, Allan Barrea, Jean-Louis Thonnard, Benoni B. Edin and Philippe Lefèvre (2021), *High-resolution imaging of skin deformation shows that afferents from human fingertips signal slip onset*. The recording identifiers, catalogue checksums and experimental descriptors in `touch-roster.json` derive from their CC BY 4.0 deposit. This recipe groups the records by participant, averages raw force, counts spikes and constructs a matched previous-repeat control. The original measurement files are obtained separately. [Paper](https://doi.org/10.7554/eLife.64679) · [Data deposit](https://doi.org/10.5281/zenodo.4818439) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Local preparation

Place `prepare_touch.py` and `touch-roster.json` together. Supply `data_summary.mat` and the individual `.mat` files for the desired split in one directory, named exactly as in the deposit. The large image ZIP files are unnecessary. The roster records the published size and MD5 for each file. The program checks both before decoding, and checks the summary's SHA256. Use a new output filename for each invocation.

Use Python 3.12 or later with NumPy and SciPy. The reference implementation was checked with NumPy 2.5.5 and SciPy 1.18.1. It uses SciPy's MAT-v5 workspace reader to recover the named MATLAB table columns. Run one process on CPU. On systems with multithreaded BLAS, set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` before running.

```sh
python -m pip install numpy==2.5.5 scipy==1.18.1
python prepare_touch.py train recordings train.npz
python prepare_touch.py development_validation recordings development_validation.npz
```

All sessions from a person stay together. The roster fixes 21 recording files from seven training participants, four from two development-validation participants, seven from three test participants and three from one reserve participant. Reserve identifiers document the partition. Reserve measurement files are unnecessary for each command.

The output is a NumPy archive readable with `np.load(path, allow_pickle=False)`. Each row contains:

| Array | Meaning |
| --- | --- |
| `X[N,10,5]` | Ten 20 ms bins. Channels are mean raw force X, Y and Z (N), the observed spike count, and elapsed seconds at the end of the bin. |
| `y[N,1]` | Number of deposited single-afferent spikes 21 through 40 ms after the cutoff, inclusive. Present in the training and validation files. |
| `previous_repeat_force[N,10,3]` | Raw force means at identical elapsed times in the immediately preceding source trial, from the same recording, direction and material. Substituting this array for the first three input channels preserves the row and all non-force observations. |
| `baseline[N,1]` | Last observed 20 ms spike count, a persistence reference. |
| `group`, `unit`, `recording` | Source participant, afferent and acquisition. The training and validation files retain the native filename with extension. |
| `trial`, `previous_trial`, `cutoff_ms` | The 1-based deposited trial column, preceding trial column, and zero-based 1 kHz sample index at forecast issue. |
| `material`, `direction`, `receptor_class`, `field_vs_contact` | Deposited condition, stimulation direction, afferent class and receptive field location relative to the imaged contact. These identify strata for analysis. |

The first cutoff is row 200, then every 20 ms that leaves room for the full outcome interval. At index t the history spans t−199 through t. Source milliseconds t+1 through t+20 provide the gap. The outcome spans t+21 through t+40. Spikes are the original investigators' discriminated impulses on the deposited 1 kHz grid.

Both adjacent trials must be nonvoid with `isInvalid == 0`. The source flag bits mean missing nerve data (1), missing robot data (2), missing camera data (4), poor images (8) and excessive robot speed (16). This analysis applies the source's strict all-modalities validity rule even though its inputs omit images. Each donor is the immediately preceding source trial, with the same direction and material. All raw force means from both histories must be finite and the current spike history must contain only 0 and 1. Training and validation require binary future events for every counted millisecond. Retrospective source validity limits live-use claims.

## Frozen predictions and later test labels

```sh
python prepare_touch.py test-features recordings held-features.npz
```

This command checks the original source file, decodes its serialized MATLAB table, and computes features using the history through each cutoff. A later bin can use spikes observed since an earlier prediction. The command never builds future target counts and does not select rows using future spike completeness. Held outputs also include `person`, equal to `group`, and use recording stems without the file extension to match the held prediction keys.

Use previously fitted models and controls to predict every held feature row. Save a private `predictions.npz` containing the original `recording`, `trial` and `cutoff_ms` arrays in order and `predicted_rate` with one finite, nonnegative expected count per row per model (shape N or N × models). Record the model ordering and the predictions archive's SHA256 separately before revealing outcomes. To print the digest portably:

```sh
python -c "import hashlib; print(hashlib.sha256(open('predictions.npz','rb').read()).hexdigest())"
python prepare_touch.py test-labels recordings held-labels.npz --features held-features.npz --predictions predictions.npz --prediction-sha256 RECORDED_DIGEST
```

The label command verifies that the supplied features match the original files, the prediction bytes match the supplied digest, and every source row key matches in order. An external dated commitment to the digest is needed to establish when the predictions were frozen. The separate output contains each row key, the bound digest, `y` and `observed`. Missing or nonbinary future spikes yield NaN and a false support flag. Compare all predictions on that same observed subset. Count independent participants when stating generalization; numbers of windows, trials, protocols and afferents describe repeated measurements.
