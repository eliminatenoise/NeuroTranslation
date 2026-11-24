# Run the NeuroTranslate 0.1 walking-force forecast

The model reads the last 200 milliseconds of muscle activity and force on one plate in the floor. It forecasts whether the plate will start carrying load in the next 100 milliseconds and estimates the vertical force accumulated over those 100 milliseconds.

The file in this package is the *adapter*. It contains the small layers that convert the measurements into inputs for Inkling 2 Mini and turn Inkling's output into the two forecasts. Download the exact Inkling 2 Mini release to run them. [Required base release](https://huggingface.co/thinkingmachines/Inkling-2-Mini/tree/ed40e7da625f594fc9c4990f5f66be24873c22d7)

## Run the example on Linux

The full test used Linux x86-64, Python 3.13 and CPU PyTorch. Allow about 20 GB of disk space for the original model files. The process used about 50 GiB of resident memory in the verified run. Start with at least 64 GiB of available system memory. The example uses four CPU threads unless you choose a different count.

**1. Install the loader.** Open a terminal in the extracted folder and run these commands.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1+cpu
python -m pip install -r requirements.txt
```

**2. Get the base files.** This command saves the four files to `inkling2mini-base/`. If you already have the files, point the next command at their folder. The version, sizes and checksums are in [`checkpoint.json`](checkpoint.json).

```sh
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 hf download thinkingmachines/Inkling-2-Mini \
  config.json hf_quant_config.json model.safetensors.index.json model-00001-of-00001.safetensors \
  --revision ed40e7da625f594fc9c4990f5f66be24873c22d7 \
  --local-dir ./inkling2mini-base --max-workers 1
```

**3. Try the forecast.** The program checks the files, loads the model and runs invented readings. The additional check repeats the forecast and verifies that changing a missing or late value has no effect.

```sh
python demo.py --base-dir ./inkling2mini-base --check-mask
```

Replace `--check-mask` with `--check-only` to verify the files without loading the model. Once Python and the weights are in place, the package's Linux, macOS and Windows launchers can look for `inkling2mini-base/` next to themselves. Pass `--base-dir PATH` or set `NEUROTRANSLATE_BASE_DIR` to use another folder. The full run has been verified on Linux. The macOS and Windows launchers still require a compatible Python and PyTorch environment. [Verified example output](VERIFICATION.json)

## Read the two forecasts

- **New-load score** estimates whether the plate will start carrying load. The program shows the model's raw score (its logit) and its zero-to-one conversion. The conversion has yet to be checked against how often a new load occurs on unseen walks.
- **Signed vertical impulse** is the sum of the vertical force readings from the next 100 samples, each multiplied by one millisecond. The unit is the newton-second. Upward force is positive.

The study counts a new load at the first upward crossing of 20 N after 20 samples between −10 N and +10 N. Force must then stay at or above 20 N for 20 samples, including the crossing. The crossing must begin in the next 100 milliseconds.

Six fitting updates used 12 labelled examples from five walks by two people. Each update included a measured new load and a measured example without one. Of the 12 people and 36 walks assigned to fitting, those were the only people and walks whose admitted files named all the required muscles. The adapter learned from those examples while the Inkling weights stayed fixed. Accuracy on new people and other sets of plates remains unmeasured. [Walking data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Recording study](https://doi.org/10.1038/s41597-023-02767-y)

## Use your own readings

Use one plate per input row, with muscle voltages and force on the same 1,000 Hz clock. Group the 200 samples ending at the issue tick into ten consecutive groups of 20. For each muscle, square the voltages in a group, average the squares, and take the square root. Supply that result in volts. For the plate, supply the average signed upward force in newtons. The model can use a group once all its samples have arrived. The walking files record sample times. They do not measure the delay from each sensor to a live model.

Use the muscle names in this order: `LBF, LERS, LGAS, LRF, LST, LTA, LVL, RBF, RERS, RGAS, RRF, RST, RTA, RVL`. L and R identify left and right. The fitting run used plates 1 and 2, and each prediction receives the past force of the very plate it predicts. In [`demo.py`](demo.py), `invented_history()` shows how to pass values, measurement times, arrival times and flags for missing data. Call `load_model()` once per Python process and reuse the returned model for later histories.

## Sources and licenses

The NeuroTranslate adapter, source and documentation here use [CC0 1.0](LICENSE). The walking data use CC0 1.0 and the article uses CC BY 4.0. Thinking Machines Lab distributes the base model separately under Apache 2.0. Separately installed software keeps its own license notices. [Walking data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Study methods](https://doi.org/10.1038/s41597-023-02767-y) · [Inkling model card](https://huggingface.co/thinkingmachines/Inkling-2-Mini) · [Transformers 5.24.0](https://github.com/huggingface/transformers/releases/tag/v5.24.0)
