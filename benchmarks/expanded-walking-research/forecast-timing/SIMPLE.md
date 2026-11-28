# Time to return a walking forecast

This model predicts what will happen under two force plates in the next **100 milliseconds**, one tenth of a second. On the tested computer, **none of 176 timed calls finished within those 100 milliseconds**. The usual three-pass calculation took about **679 milliseconds** in the middle of the first set of measurements, even with the model already open and its inputs ready. If a live system started its calculation at the forecast cutoff, the answer would arrive after the interval it describes. [Technical report](TECHNICAL.md) · [All recorded times](results.json)

## The two predictions

A force plate measures how hard someone presses on it. The model takes the last 200 milliseconds of vertical force from each plate and electrical readings from six muscle channels. For each plate it predicts the chance of a new load and how much vertical force will accumulate in the next tenth of a second. The second quantity is called impulse. Holding one newton of force for one second contributes one newton-second (N·s). Its sign preserves the direction of force. The two plates refer to the same instant, so the timer counts one call when it produces both answers for both plates.

This was the released NeuroTranslate 0.1 Research Edition walking checkpoint, a saved set of fitted weights. It had been trained on 4,793 pairs of plate histories from 36 walks by 12 people, updating its weights 547 times in one sweep through the training data. Here the inputs came from an invented example supplied with the checkpoint. Keeping that example known made it possible to compare repeated answers exactly. The participant study measured forecast errors separately. [Original walking evaluation](../SIMPLE.md) · [Released model](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)

## Opening the model and using it

One fresh program took **72.534 seconds** to import the model software, check the files and load the weights. The computer may already have had some file contents in its operating-system cache. A person opening the program has to allow for this startup step. Once open, the model can stay in memory for many requests. The 72 seconds were measured once and are separate from every time in the tables. Including setup, warm-up and all calls, the first process ran for 132.924 seconds and the second for 522.671 seconds. The second trial did not time its model load separately.

For each timed request the program already had the earlier readings. It converted their numbers, timestamps and flags for missing readings into the model’s input, ran the prediction and wrote its numerical fields into JSON, a text format programs can exchange. The clock ran across those steps together. The fields contained the chance of a new load, its score before conversion to a probability (the logit), and the signed force impulse. The probability had no separate calibration against new people. The timer stopped when the result was encoded. Collecting an electrical signal, waiting for a force plate, sending a message across a network or moving a device would add steps outside this measurement.

## Repeating the middle of the model

The model has 24 layers of calculation. Twelve middle layers can run again on the same forecast. Each trip through those twelve is called a pass. Three passes were used during training. The first trial allowed the running program to use four logical CPUs, each on a different physical core, and set the software to four compute threads. Those threads divide the work of a calculation. The machine was an AMD Ryzen AI Max+ 395 with 16 physical cores and 32 logical CPUs, running the CPU edition of PyTorch 2.14.1. It kept one thread for coordinating separate operations and used the stored model weights at their released precision.

| Way of making the forecast | Calls | Middle time (ms) | 95th-percentile time (ms) | Calls within 100 ms |
| --- | ---: | ---: | ---: | ---: |
| One pass | 20 | 317.93 | 323.86 | 0 |
| Three passes | 20 | 679.32 | 687.24 | 0 |
| Five passes | 20 | 1,029.73 | 1,049.33 | 0 |
| Three passes using the package’s example command path | 20 | 680.22 | 695.37 | 0 |

Read a row from left to right. For three passes, there were 20 returns. Sorting them by time and averaging the two middle values gives 679.32 ms, the median or p50. To calculate p95, count up the ordered list to the first position that covers at least 95% of its entries. Here that is the 19th time. The slowest of these 20 calls may be longer still. These figures describe the measured calls on this machine.

The fourth row used the package’s example routine. It read the example file again and counted which layers ran. The other three rows started with that same example already in memory and skipped the counters. Before timing, the program obtained a reference answer for each pass count from the package routine and checked one direct forecast against it. It then varied the order of the four cases across 20 blocks. Within every row, all 20 timed answers matched the corresponding reference numbers exactly. Different numbers of passes can produce different predictions. The walking evaluation separately compares their accuracy. [Pass count and walking accuracy](../pass-count/SIMPLE.md)

## Sharing one calculation across more threads

A second trial opened the same model once and kept the number of passes fixed at three. All settings could use one logical CPU on each of the machine’s 16 physical cores. That is a wider choice of where to run than in the first trial, even when the program used only four threads. There were also three different invented inputs. One kept the original readings. One multiplied the observed values by 0.75, and another multiplied them by 1.15. Their clocks and missing readings stayed the same. These changes exercised the calculation without adding a recording from a person.

| Compute threads | Calls | Middle time (ms) | 95th-percentile time (ms) | Longest time (ms) | Exact matches to four threads |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 24 | 690.22 | 753.83 | 759.52 | 24 of 24 |
| 8 | 24 | 625.55 | 790.21 | 1,169.29 | 24 of 24 |
| 12 | 24 | 545.40 | 768.70 | 772.70 | 24 of 24 |
| 16 | 24 | 539.26 | 87,046.61 | 122,914.97 | 24 of 24 |

Each setting received six timed calls in each of four rounds, after one untimed warm-up in that round. The starting thread count rotated. Each of the three examples appeared eight times per setting. The four-thread calculation supplied a reference for each example, and the unchanged example also reproduced the three-pass answer from the first trial. The largest difference in any returned number across thread settings was zero. None of the 96 timed calls finished within 100 ms.

At 16 threads the middle time was about half a second. Six of its 24 calls took over a second. Its second-slowest call took **87.047 seconds** and its slowest took **122.915 seconds**. With 24 measurements, p95 is the 23rd time in order, so it includes one of these long waits. Twelve threads had a similar median on the same trial, with a p95 below one second. The workstation was shared and a timer also runs while a program waits. The measurements show how widely the return times varied under this workload. They do not tell us what caused any particular delay, or how another computer, input or workload will behave.

## Read the measurements or repeat the experiment

To check the published numbers, save this folder, open a terminal in it and run the following with Python 3.10 or later. It reads the individual recorded times, checks the archived comparisons and calculates the table values. This takes no model download.

```sh
python -B timing.py verify-results
```

If you have extracted the checkpoint, you can also check the packaged files and the invented input. Replace the example directory below with your extraction folder. This check leaves the large base model unloaded.

```sh
python -B timing.py check-package --package /path/to/extracted-checkpoint
```

Timing a new prediction on this version requires its full Linux x86-64 environment, Python 3.13, the versions listed by the package, the four separate base files and at least 64 GiB of available memory. The technical instructions give the commands to run the pass and thread trials separately on suitable CPU sets. The new output contains a record for each request. A live feedback test would also have to measure when real sensor readings become available and when the receiving system can use the answer. [Reproduction commands](TECHNICAL.md#reproduce-the-checks) · [Checkpoint setup and base model terms](https://github.com/eliminatenoise/NeuroTranslation/releases/tag/expanded-walking-2026-11-24)
