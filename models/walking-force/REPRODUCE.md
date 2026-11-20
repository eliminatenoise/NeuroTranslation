# Run the forecast

On Windows, open `Run-Windows.cmd`. On macOS, open `Run-macOS.command`. On Linux, run `./Run-Linux.sh` in a terminal. If archive extraction removed a Unix launcher’s execute bit, run it with `sh`. Install Python 3 and NumPy first. Linux shell execution was verified. Native Windows and macOS execution remains untested.

Python 3 with NumPy can run the two-plate forecast on the invented eight-token history. The package includes six fitted predictors and a test input containing one missing marker and one missing electrode reading.

```sh
python predict.py
```

The combined Transformer returns approximately 620.937 N for that invented input. This number describes a model response to a constructed history. It has no measured target.

## Reproduce the study

The analysis used Python 3.13, NumPy 2.4.6 and PyTorch 2.14.1+cpu for fitting. C3D extraction used Python 3.12, ezc3d 1.7.2 and NumPy 2.5.5. Obtain the walking archive from the authors’ figshare version 8 and the DOCX containing Supplementary Tables 1 and 2 from the paper. Keep both in a private working directory. The expected SHA-256 values are fixed in `prepare.py`. Ordinary ZIP transport includes all participants in compressed form. The preparation command opens only the selected partition's trial entries. [Original recordings](https://doi.org/10.6084/m9.figshare.7734767.v8) · [Supplementary tables](https://static-content.springer-cdn.net/esm/art%3A10.1038%2Fs41597-019-0124-4/MediaObjects/41597_2019_124_MOESM2_ESM.docx)

Run from the extracted study directory. Substitute the paths to the original archive and supplement for the first two filenames. On Linux and macOS the environment variables below bound numerical thread pools to one. Windows users may set the same variables in their shell.

```sh
python -m pip install numpy torch ezc3d
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python prepare.py original.zip supplement.docx work train
python extract.py train work/train work/split.json work/train.npz --availability work/train/contact-codes.json
python fit.py work/train.npz work/models work/private-fit --threads 1
python prepare.py original.zip supplement.docx work assessment --fit-seal work/private-fit/fit-seal.json
python extract.py assessment work/assessment work/split.json work/assessment.npz --availability work/assessment/contact-codes.json --fit-seal work/private-fit/fit-seal.json
python assess.py work/assessment.npz work/models work/private-fit work/results.json
```

Keep the recreated `work` directory private. The nonlinear kinematic baseline uses 256 time windows from training recordings as its landmarks. The distribution includes its model specification and training code. The original plate traces, landmark windows, participant contact tables and individual model outputs stay with the local reproduction. The paper reports aggregate errors.

`protocol.json` fixes the history, endpoint, models, comparators and decision rule. `qualification.json` records the source-based eligibility rule added before fitting. The supplement assigns two distinct reliable contacts to the included trials. The dataset’s stored zeros combine suppression of small forces and possible missing raw samples. Reproduction may give tiny floating-point changes across numerical-library builds.
