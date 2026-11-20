# Run the six-landmark forecast

## Run the example

Python 3 and NumPy run every released model on CPU. The launchers open the combined Transformer result for Windows, macOS or Linux. On Linux or macOS a shell can also run `sh Run-Linux.sh` or `sh Run-macOS.command`. Linux execution was checked. The Windows and macOS launchers have not been exercised on their native operating systems.

```sh
python -m pip install numpy
python predict.py
python predict.py example.json --model ridge_markers
python check_example.py
```

Make an input JSON with two fields. The forty-by-eight-by-three `markers_mm` array contains consecutive 100 Hz laboratory coordinates, Z up, in the order left/right lateral ankle, left/right lateral knee, left/right radial wrist and left/right anterior pelvis (FAL, FLE, RSP, IAS). The first dimension runs from oldest to newest. Each frame has eight XYZ points. A missing point may be represented by three nulls.

The optional eight-by-eight `emg_rms_uv` array describes the right tibialis anterior, soleus, medial gastrocnemius, vastus medialis, rectus femoris, semitendinosus, gluteus maximus and gluteus medius in that order. Each entry is a root-mean-square voltage in microvolts, or null. Eight tokens are 50 ms apart. For the token ending at zero-based camera frame f in the original C3D, take the 60 analog samples from 15f−52 through 15f+7, inclusive. The last sample is the middle of the frame's 15-sample block. Omit EMG and select `ridge_markers` or `transformer_markers` to use the marker-only fit. The combined model also accepts missing electrical data using its training means and validity flags.

`predict(markers_mm, emg_rms_uv=None, model="transformer_combined")` in predict.py returns six XYZ displacements in mm. Their order matches the first six input markers. All four statistical models use the exact arrays in weights.npz. The browser-format weights.json contains the same arrays.

## Repeat the study

Use a private working directory. Download the C3D archive and the paper's Supplementary Tables document. The preparation script verifies their SHA-256 and extracts only the admitted partition's recordings. The supplement supplies forceplate codes, which this forecast ignores. Muscle availability is taken from the labelled volt channels actually present in each C3D, requiring all 60 samples to be finite. All eight channels were finite and had positive RMS at every assessment token. [Walking archive](https://ndownloader.figshare.com/files/22295019) · [Supplementary tables](https://static-content.springer-cdn.net/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx) · [Source clarification](source-clarification.json)

The original decoder used Python 3.12 with ezc3d 1.7.2 and NumPy 2.5.5. Fitting used Python 3.13 with NumPy 2.4.6 and PyTorch 2.14.1+cpu. Portable inference uses only NumPy. Use the decoder environment for the two extract.py calls and the fitting environment for fit.py. The commands below use a POSIX shell. On Windows, set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS and MKL_NUM_THREADS in your shell and supply the computed SHA-256 in place of the shell variable.

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=1
python prepare_source.py walking.zip supplement.docx work train
python extract.py work train work/train.npz
python fit.py work/train.npz work/sealed --threads 2
seal=$(python -c "from pathlib import Path; import hashlib; print(hashlib.sha256(Path('work/sealed/fit-seal.json').read_bytes()).hexdigest())")
python prepare_source.py walking.zip supplement.docx work assessment --fit-seal work/sealed/fit-seal.json --fit-seal-sha256 "$seal"
python extract.py work assessment work/assessment.npz --fit-seal work/sealed/fit-seal.json --fit-seal-sha256 "$seal"
python assess.py work/assessment.npz work/sealed work/scores-private.json
python aggregate.py work/scores-private.json work/scores.json
python direction_check.py work/train.npz work/assessment.npz work/sealed work/direction-private.json
python aggregate.py work/direction-private.json work/direction.json
```

The fit seal includes a measured runtime, so a new fit produces its own seal digest. Compare parameter arrays with the released weights and compare the resulting scientific scores. A different numerical-library build can change floating-point results slightly. Full scores contain local ordinal-level results. Keep those, the C3Ds, the complete phase tables and the intermediate arrays in the private working directory.

The marker model has eight steps of 64 features. Each step gives pelvis-relative positions, within-step movements and validity bits. Muscle tokens add eight RMS values and eight presence bits. Ridge regression uses all eight steps. The residual Transformer adds a learned correction to the matched ridge forecast. It has one block, width 32, four attention heads, a 64-unit feedforward layer and one linear output for the last token. Both fits ran for 24 epochs, 720 updates apiece. The fixed [protocol](protocol.json) specifies all baselines and scoring. [Fit record](fit-seal.json) · [Source and reuse](NOTICE.md)
