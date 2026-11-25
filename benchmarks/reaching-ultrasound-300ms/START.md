# Run a reaching forecast

Extract the whole download into one folder. Install Python 3.10 or later and NumPy. In a terminal, run `python -m pip install numpy` if you already have Python and need NumPy. Use `python3` in that command if your computer uses that name.

Open a terminal in the extracted folder. Choose the launcher for your computer.

| Computer | Command |
| --- | --- |
| Windows, Command Prompt | `Launch-Windows.cmd` |
| macOS | `sh Launch-macOS.command` |
| Linux | `sh Launch-Linux.sh` |

The launcher uses the invented arm and muscle readings in `example.json`. It prints three estimates for the triceps and the brachialis, in that order. The values are the predicted spread of tracked points in an ultrasound image taken 300 milliseconds later. You will see a simple estimate, a linear estimate and a learned estimate.

For each muscle, the simple estimate follows the ultrasound trend if readings are available for five consecutive time slots. The full setting uses the latest five slots and the gap setting uses the oldest five. If any required reading is missing, the simple estimate uses a typical value from training. The blind setting always uses that typical value.

Add `--mode gap` to use only the older half of the ultrasound history. Add `--mode blind` to remove ultrasound entirely. For example, on Linux run `sh Launch-Linux.sh --mode gap`.

The command uses one of the two shared checkpoints. Both were trained to work with the available readings as the ultrasound input changes. Adding `--seed both` averages the two forecasts for comparison with the study. You can also add `--passes 1` to see what changes when the model makes one extra calculation after reading the history. The default uses three.

[Study results in plain language](SIMPLE.md) · [Technical study](TECHNICAL.md) · [Input file instructions](INPUT.md)
