# NeuroTranslate 0.1

Will the plate under a walker’s foot begin to carry load in the next tenth of a second? Give NeuroTranslate the last 200 milliseconds of muscle activity and force on one plate. It returns a score for a new load and an estimate of the force added up over the next 100 milliseconds.

Inkling 2 Mini does the middle of the work. This checkpoint supplies the small set of fitted layers that turn the measurements into numbers Inkling can use, then turn its output into the two forecasts. Those layers and their input scales fit in a file smaller than half a megabyte. Get the frozen Inkling weights from Thinking Machines Lab. [Pinned Inkling 2 Mini release](https://huggingface.co/thinkingmachines/Inkling-2-Mini/tree/ed40e7da625f594fc9c4990f5f66be24873c22d7)

## Run the example

The verified setup is Linux x86-64 with Python 3.13 and the CPU build of PyTorch. Set aside about 20 GB of disk space for the base files. The loader expands the packed weights and the process takes about 50 GiB of resident memory on the verified route. Start with at least 64 GiB of available system memory. The example uses four CPU threads by default.

Open a terminal in this folder and install the software in a separate Python environment.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1+cpu
python -m pip install -r requirements.txt
```

Download the four base files from the exact release listed in [checkpoint.json](checkpoint.json). The same folder can serve later runs. Use an existing copy if its checksums match.

```bash
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 hf download thinkingmachines/Inkling-2-Mini \
  config.json hf_quant_config.json model.safetensors.index.json model-00001-of-00001.safetensors \
  --revision ed40e7da625f594fc9c4990f5f66be24873c22d7 \
  --local-dir ./inkling2mini-base --max-workers 1

python demo.py --base-dir ./inkling2mini-base --check-mask
```

The program checks file sizes and SHA-256 checksums, restores the adapter, and runs an invented example on the local CPU. The optional check repeats the example. It also verifies that changing the value of a missing or late measurement leaves the forecast exactly the same. To check your files without loading the model, run `python demo.py --base-dir ./inkling2mini-base --check-only`. [Verified example output](VERIFICATION.json)

With the Python environment and base files in place, open `launch-linux.sh`, `launch-macos.command` or `launch-windows.cmd` from a terminal. Each launcher checks for `inkling2mini-base` beside itself. Use `--base-dir PATH` or set `NEUROTRANSLATE_BASE_DIR` to point it at another local folder. The full model run was verified on Linux. The macOS and Windows launchers need a compatible Python and PyTorch setup.

## Read the numbers

- **New load score** is the model’s logit. The example also displays the same score on a zero-to-one scale. That number has not been calibrated against unseen walking data.
- **Signed vertical impulse** is the sum of the measured upward force samples, each multiplied by one millisecond. Its unit is the newton-second (N·s). The output estimates this quantity over the 100 samples immediately after the last input sample.
- **New load** is the first upward crossing of 20 N after 20 samples in the unloaded band from −10 N to +10 N. The force must stay at or above 20 N for at least 20 samples, including the crossing. A crossing counts only if it starts in the next 100 milliseconds.

## Supply the same measurements

Each input has a shared 1,000 Hz clock. Every row represents one plate. Use the ten consecutive 20-sample bins ending at the forecast issue. For each muscle channel, take the square root of the mean of the squared voltages in the bin. For the plate, take the mean signed vertical force in newtons, with upward positive. A bin becomes available when its final sample is available. `invented_history()` in [demo.py](demo.py) shows how to pass the bin values, their acquisition and arrival times, and the Boolean masks. Run `load_model()` once in a Python process, then reuse the returned model for later histories.

The muscle channel order is `LBF, LERS, LGAS, LRF, LST, LTA, LVL, RBF, RERS, RGAS, RRF, RST, RTA, RVL`. L and R mark the two sides. These are the channel names in the source recordings. The training code admitted plates 1 and 2. Each forecast receives the history of the plate it is predicting. [Recording methods and channel source](https://doi.org/10.1038/s41597-023-02767-y)

## What has been measured

Six training updates used twelve labelled examples drawn from five walks by two people. Each update saw a measured new load and a measured example where no new load occurred. Of the twelve people and thirty-six walks assigned to fitting, only those two people and five walks supplied all required muscle names in the released files. The test establishes that the adapter can update on these recorded measurements while the Inkling weights stay frozen. Accuracy on unseen people and on other force-plate setups remains unmeasured. [Van Criekinge and colleagues’ healthy walking dataset](https://doi.org/10.6084/m9.figshare.24192480.v1)

## Sources and permissions

The NeuroTranslate adapter, Python source and documentation in this folder are released under [CC0 1.0](LICENSE). The healthy walking dataset is CC0 1.0 and the associated article is CC BY 4.0. [Dataset](https://doi.org/10.6084/m9.figshare.24192480.v1) · [Article](https://doi.org/10.1038/s41597-023-02767-y)

Thinking Machines Lab distributes the separately downloaded Inkling 2 Mini weights under Apache 2.0. The loader uses the official Transformers release and the separately installed Python packages retain the license notices included in their distributions. [Inkling 2 Mini model card](https://huggingface.co/thinkingmachines/Inkling-2-Mini) · [Transformers 5.24.0](https://github.com/huggingface/transformers/releases/tag/v5.24.0)
