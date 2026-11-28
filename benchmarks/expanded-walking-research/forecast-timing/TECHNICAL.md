# CPU timing for the 547-update walking checkpoint

The model forecasts the next **100 ms** of force-plate activity. From an already available invented history, all **176 timed requests** took longer than that interval. A three-pass request on four pinned logical CPUs took **679.32 ms at the median** and **687.24 ms at the 95th percentile**. These are elapsed times for one simultaneous two-plate forecast on a shared workstation. [Plain-language report](SIMPLE.md) · [Recorded request timings and reference outputs](results.json)

## Checkpoint and timing boundary

The released NeuroTranslate 0.1 Research Edition model trained for one epoch, 547 updates, on 4,793 simultaneous plate pairs from 36 walks by 12 people. It uses the preceding 200 ms of vertical force and six muscle-electrode channels. It estimates the chance of a new load and the signed vertical force impulse over the next 100 ms, in newton-seconds (N·s). At each pass it reuses the same 12 middle layers of a 24-layer decoder. The standard fitting depth was three passes. [Training and participant evaluation](../TECHNICAL.md) · [Released checkpoint and setup](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

The two runs used the same AMD Ryzen AI Max+ 395 CPU (16 physical cores, 32 logical CPUs), CPU PyTorch 2.14.1+cpu, deterministic evaluation, the released BF16/FP32 tensors and one inter-operation thread. A fresh process in the first run spent **72.534 s** importing the package, checking the release and separate base files and loading the verified model. The operating system’s file-cache state was uncontrolled. Whole-process elapsed time was 132.924 s for the first trial and 522.671 s for the thread trial, including startup, warm-up and measured calls. The thread trial has no separate load measurement. All request times below start with a resident model. Each includes constructing history tensors and availability masks, forward computation, converting both plates’ outputs to numbers and serializing them to JSON. These steps were timed together. There was no sensor acquisition, network delivery, actuation or live participant accuracy test.

## Repeated passes on four pinned logical CPUs

Twenty blocks each contained the same four cases. Case order rotated, reversing after each group of four blocks. Each depth had an untimed instrumented reference and an untimed direct check. The public example path also reread the example file and installed and removed counters for layer visits. Every timed request matched the numerical JSON for its own depth exactly. The three fields were the new-load logit (log-odds), uncalibrated new-load probability and signed force impulse, each for two plates.

| Case | Calls | Median (ms) | p95 (ms) | At or below 100 ms | Exact matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 pass | 20 | 317.93 | 323.86 | 0 | 20 |
| 3 passes | 20 | 679.32 | 687.24 | 0 | 20 |
| 5 passes | 20 | 1,029.73 | 1,049.33 | 0 | 20 |
| 3 passes, public example with layer counts | 20 | 680.22 | 695.37 | 0 | 20 |

The process could use only logical CPUs 20–23, on four different physical cores. The four compute threads worked within that set. The median is the mean of the two central times. The reported p95 is the nearest-rank value, the 19th of 20 sorted observations here.

## Thread count on the wider CPU set

A separate process loaded the same checkpoint once. All configurations could use logical CPUs 16–31, one on each of 16 physical cores. Three passes and the two-row batch stayed fixed. Three invented histories scaled the observed values in the packaged example by 1.00, 0.75 and 1.15 while retaining timestamps, missing values and masks. In each of four rotations, all four thread counts received one untimed warm-up and six timed calls. Each input appeared eight times at each width. The four-thread row here has a wider affinity and a different input and scheduling workload from the four-thread pass trial.

| Compute threads | Calls | Median (ms) | p95 (ms) | Maximum (ms) | At or below 100 ms | Exact four-thread matches |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 24 | 690.22 | 753.83 | 759.52 | 0 | 24 |
| 8 | 24 | 625.55 | 790.21 | 1,169.29 | 0 | 24 |
| 12 | 24 | 545.40 | 768.70 | 772.70 | 0 | 24 |
| 16 | 24 | 539.26 | 87,046.61 | 122,914.97 | 0 | 24 |

Here p95 is the 23rd of 24 times. Six calls at 16 threads exceeded a second. Its median was the lowest of the four, and its p95 and maximum were the highest. The workstation was shared, and elapsed time includes any time the process waited. The trial did not isolate the causes of those delays. At every width the maximum absolute difference from the matching four-thread reference was zero in all three output fields. The unchanged example also matched the four-CPU trial’s three-pass reference. Exact agreement on these invented histories does not measure forecasting accuracy on people. [Pass count and walking accuracy](../pass-count/TECHNICAL.md)

## Reproduce the checks

From this directory, run the first command with Python 3.10 or later. It reconstructs both timing tables and checks the archived output comparisons using only the standard library. The second command checks the extracted release and its invented input without loading the base.

```sh
python -B timing.py verify-results
python -B timing.py check-package --package /path/to/extracted-checkpoint
```

For a new timing run, follow the checkpoint’s Linux x86-64, Python 3.13 setup, including its pinned dependencies, four base files and at least 64 GiB of available RAM. With that environment active, use the commands below on a machine with the indicated CPU topology. On another Linux host use `lscpu -e=CPU,CORE` to choose comparable, available CPU sets. Each command starts a fresh process. Its JSON includes individual times, summaries and the visible logical CPU set. The example and benchmark require no participant data.

```sh
taskset -c 20-23 nice -n 5 python -B timing.py depths --package /path/to/extracted-checkpoint --base-dir /path/to/base
taskset -c 16-31 nice -n 5 python -B timing.py threads --package /path/to/extracted-checkpoint --base-dir /path/to/base
```

The benchmark calls the package’s own verification, loader, history conversion and instrumented example functions. It uses the original checkpoint manifest and base SHA-256 recorded in the results. The package instructions identify the separate base release and its license. [Timing script](timing.py) · [Checkpoint release](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24) · [Pinned Research Edition base](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/tree/657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2)
