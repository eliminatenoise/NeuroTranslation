# Run a private wrist forecast

To reproduce the experiment on AJILE12, obtain the published source and follow its data-selection and fit instructions on your computer. The study source prepares earlier inputs and fits the model from the versioned recording. The browser needs only one numeric JSON file after fitting. [Study source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/human-wrist) · [Download source ZIP](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/refs/heads/main/models/human-wrist.zip) · [Dataset and download](https://doi.org/10.48324/dandi.000055/0.220127.0436)

With a trusted weights archive and matching input archive in the study format, run the following in a Python environment with NumPy. The output path must be new. Row numbers start at zero.

```sh
python export_case.py weights.npz train.npz private-case.json --row 0
```

For a scored training example with both reference positions available, add `--with-reference`. Without this option the exporter reads only earlier inputs. Select a row with finite values in both arms. This particular two-wrist reader requires complete bilateral input. The research experiment evaluates each arm with its own eligibility mask, so its full denominators can differ.

Open the reader, choose **Model and case (.json)** and select the file. The numbers stay in browser memory until you replace the package or close the page. A private file can contain identifiable motion patterns and individual-fitted coefficients. Keep the weights, JSON, recordings and screenshots in your private workspace.

The accepted format is `wrist-forecast-v1`, with a 2 MiB size limit and one to eight examples. The mandatory fields are `format`, `weights` and `cases`. The file contains numbers and fixed schema keys. It cannot supply code, chart labels, URLs or markup.

For each case, `ecog_uv` is 250 × 8 earlier voltage samples in microvolts. Columns follow the eight fixed contacts in study order. The `pose_px` array is 15 frames × 2 arms (right, left) × 3 joints (wrist, elbow, shoulder) × 2 image axes (x, y). Optional `future_px` is 2 horizons (+8, +15) × 2 arms × 2 axes, in the original camera frame. All wrist and reference values must use the same camera origin. The reader subtracts each wrist’s last position when drawing or reporting displacement. The comparison remains descriptive in pixels. Physical distance needs independent camera calibration.

The `weights` keys and array shapes are listed in `export_case.py`. This reader uses training seed 17 throughout. Each side has a separate learned branch for each treatment and input condition. Choosing **Earlier pose alone** selects a separately trained pose model. The anchored model adds its bounded learned correction to the fitted camera-velocity prior. The direct model learns the whole displacement. The bounded-zero model fits a small correction to a stationary wrist. Earlier voltage gain multiplies all eight traces before their per-window mean and log root-mean-square features are computed.

## Rebuild the simulated example

The generator has its own artificial arm and voltage equations. It uses 64 generated examples for fitting and four separately generated examples for the reader. A pair of oscillating joints moves each artificial wrist. Three underlying oscillations drive the joints and synthetic voltage, with noise added to both. Public (x, y) values and weights originate entirely in these equations.

Install Python, NumPy and CPU PyTorch. In this directory run the command below to make a new file. Place the result beside the reader's `index.html` as `simulation.js` to use it. Open an existing example to use the reader without a Python installation.

```sh
python simulate.py simulation-rebuilt.js --threads 1
```

The fixed data seeds are 19037 (fit) and 33117 (examples). Each of twelve branch fits uses model seed 17, 48 full-batch AdamW updates, learning rate 0.003, weight decay 0.02 and double precision. Software versions and floating-point libraries can affect final rounding. See `demo_math.py` for the causal attention layer, fitted prior and loss function.
