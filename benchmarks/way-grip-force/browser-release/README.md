# Open the grip-force forecast offline

Extract the full ZIP. Open `Run-Windows.cmd`, `Run-macOS.command` or `Run-Linux.sh`, or open `index.html` directly in a browser with JavaScript enabled. Follow your operating system's normal opening prompts. The Linux launcher was tested after extraction. The Windows and macOS launcher files received a source check.

Move the cutoff to pick the most recent sample the models may use. Compare the four +120 ms forecasts. The built-in window is invented, and it has no measured future value. Open a compatible local JSON window to use your own recordings. The program reads the file in your browser.

For all 29 cutoffs from one recorded lift, extract its windowed-series MATLAB file from WAY-EEG-GAL. Install NumPy and SciPy for Python 3 and run the included converter, substituting your file name and one-based trial number:

```sh
python convert_lift.py WS_file.mat --trial 1 --out lift.json
```

Open the new JSON in the browser. It contains sensor samples and later plate forces from the selected lift. The forecasters receive only the preceding window. Choose **Reveal recorded grip at +120 ms** to compare predictions with the plate reading. Signed errors are forecast minus recorded force. **Replay an invented lift** demonstrates the same controls with artificial numbers.

The reported study errors come from original instrumented pinch lifts by healthy volunteers. The frozen experiment did not find an aligned scalp EEG improvement over the phase-matched EEG control. The development group contained three people. The final test group remains reserved. The stored-clock horizon leaves live acquisition and instrument-filter delays unverified.

The archive carries project-owned code under CC0, shared model parameters and study-wide summaries. The original data were recorded by Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin. The WAY project (FP7-ICT-288551) supported the original recordings. Their v1 publisher records carry CC0 1.0. The descriptor credits the source data under CC BY 4.0. The models use past aligned force, movement, EEG and surface EMG windows with a compression-positive grip target. [Study and aggregate results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/way-grip-force/) · [Data descriptor](https://doi.org/10.1038/sdata.2014.47) · [Deposited recordings and terms](https://doi.org/10.6084/m9.figshare.c.988376.v2)
