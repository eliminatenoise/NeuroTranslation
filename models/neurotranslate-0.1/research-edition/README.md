# NeuroTranslate 0.1 Research Edition force preview

Check the files before you download any model weights. Extract the entire ZIP, open a terminal in that folder, and use Python 3.10 or later.

```sh
python -B launch.py --self-test
```

This checks the checkpoint manifest and 12 core files, including the fitted tensor files and the invented example. It also checks the stored tensor names and shapes. For all distributed files, verify the full list in [SHA256SUMS](SHA256SUMS). On Linux, run `sha256sum -c SHA256SUMS` from the extracted folder.

Use `launch-linux.sh` on Linux or `launch-macos.command` on macOS to run the same check. On Windows, `launch-windows.cmd` uses the Python environment in the extracted folder if you have set one up. Otherwise it calls `py -3.13`. If you have a different Python 3.10 or later on Windows, run the command above directly with that interpreter. The macOS and Windows launchers are for the file and example checks here. Neither has been run on its native system. The full forecast command requires Linux x86-64, a CPU runtime, and Python 3.13.

## What goes into a forecast

A force plate is a part of the floor that measures the push on it. The model reads the latest 200 milliseconds of muscle signals and vertical force for one plate. It sees ten 20-millisecond summaries, each with six muscle-voltage magnitudes and the mean signed vertical force in newtons. The example contains two separate invented cases with one plate each. Their muscle readings differ. The example has no measured future to compare with the output.

The two forecasts ask whether a new load starts in the next 100 milliseconds and how much signed vertical force adds up over that time. In the recordings, a new load starts at the first upward crossing of +20 newtons after 20 samples in the unloaded range, −10 to +10 newtons. The force must stay at or above +20 newtons for 20 samples, including the crossing. That extra check can extend past the forecast window when a load starts near its end.

For the second target, add the next 100 signed force samples, each multiplied by one millisecond. That gives **signed vertical impulse**, measured in newton-seconds (N·s). Upward force is positive. The program also prints the load-event score and converts it to a number from zero to one. That number has no demonstrated probability calibration.

## Get the base and run the example

Use Linux x86-64 with Python 3.13, the CPU build of PyTorch and the versions in the commands below. Have at least 64 GiB of available RAM and room on disk for the 19.53 GB weight file, the Python environment and any partial download. Get the exact four base files from the publisher or point to a copy that already matches [checkpoint.json](checkpoint.json).

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1+cpu
python -m pip install -r requirements.txt
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 hf download thinkingmachines/TML-d24-varloop-research \
  config.json hf_quant_config.json model.safetensors.index.json model-00001-of-00001.safetensors \
  --revision 657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2 \
  --local-dir ./research-edition-base --max-workers 1
```

Check the four base files without loading the model, then choose the two-case example explicitly.

```sh
python -B launch.py --check-only --base-dir ./research-edition-base
python -B launch.py --forecast --batch-layout two-invented-rows \
  --base-dir ./research-edition-base --passes 3 --check-mask
```

You can give another folder with `--base-dir PATH` or set `NEUROTRANSLATE_RESEARCH_BASE_DIR`. The checksum check reads the full weight file and can take time. The optional mask check compares the example output with an exact repeat and with a third run in which it changes three unavailable values. The extracted three-pass example ran on Linux x86-64 with four CPU threads and the separately fetched weights. It took about 76 seconds including the weight checks and loading, and all three outputs matched bit for bit.

`--passes` controls how many times the middle 12 layers run for one forecast. Thinking Machines Lab trained this part of the model with one to five passes during the later phase of its training, then used three for post-training. The local checkpoint was also fitted at three. The program takes other positive pass counts for experiments. Reliable behavior at other counts remains unverified. The publisher advises against production or user-facing deployment of this research model. Its acceptable-use policy covers the model materials and modified versions. [Publisher model card](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/blob/657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2/README.md) · [Acceptable-use policy](https://thinkingmachines.ai/model-acceptable-use-policy/)

The local fit trained the sensor input and forecast output layers, the sensor messages passed between repeats of the middle layers, and two tensors from the original model. It used six updates on twelve examples from twelve fitting people.

## Why the program makes you choose a layout

The earlier replay ran 48 plate rows from a walk as one group. Taking the same first two rows out of that group changed this checkpoint’s outputs by up to 0.368 on the load-event score before conversion and 0.331 N·s on impulse.

A second check held the group at exactly 48 rows. It kept the first two inputs fixed and changed measurement values in the 46 later rows. Those unchanged first two inputs yielded different outputs, by up to **9.114 percentage points** on the zero-to-one load scale and **0.330953 N·s** on impulse. The 48-row fitting and validation results describe offline whole-walk calculations. They cannot establish what the model would have predicted from the information available at the earlier time alone.

## What happened when only the same time was sent together

In the validation comparison, the model received both plates for one time at once. Each call used histories from that time alone. Only three of the six assigned people and nine of the 18 assigned walks had all six required muscle names. The other walks lacked a required label and stayed out of the comparison. The qualifying set supplied **216 issue times and 432 plate forecasts per method**. The recordings supplied 427 usable labels for whether a load started and all 432 measurements of impulse.

| Method at the same issue times | Load-event Brier error | Impulse mean absolute error |
| --- | ---: | ---: |
| Joint Research Edition, three passes | 0.462322 | 11.47217 N·s |
| Extend the latest mean force, predict no new load | 0.041667 | 3.23650 N·s |

Brier error is the mean squared difference between the zero-to-one forecast and the measured zero-or-one outcome. Impulse error is the mean absolute gap from the measured impulse. Lower is better for both. The simple force comparison did better on both outcomes in this qualified subset. This limited validation did not select a candidate. The separate test cohort remains unopened. [Source and reuse](NOTICE.md)
