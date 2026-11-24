# Walking and brain-signal forecasts

[Technical edition](TECHNICAL.md) · [Results data](results.json) · [Download both walking checkpoints](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/walking-neural-scaling/Walking-Forecasts.zip)

The two walking models estimate what a force plate will measure over the next tenth of a second. One model uses a sequence of small decision trees. The other goes through the same calculation three times, updating its estimate each time. A separate experiment used brain recordings to estimate where a hand would be a tenth of a second later.

## Open a walking model

1. Download and extract the ZIP. Open a terminal in the extracted folder. The three-pass model was tested on Linux with Python 3.13, and the trees with Python 3.12.
2. To run the three-pass model, enter `python -m pip install -r requirements-recurrent.txt`. Then enter `python predict.py --model three-pass`.
3. To try the trees, enter `python -m pip install -r requirements.txt`. Then enter `python predict.py --model trees`.
4. The first run uses a generated walking window. It prints the predicted force impulse and the chance that the plate begins carrying a new load. Force impulse adds up force over time. For example, 100 newtons applied for a tenth of a second produces 10 newton-seconds.

After installing the packages, use `Open on Linux.sh`, `Open on macOS.command` or `Open on Windows.cmd` to run the three-pass example. To use a launcher for the trees, run it from the terminal with `--model trees`.

To use your own recorded window, add `--input window.json` to either command. The program needs ten values from the plate you want to forecast, one for each 20 ms part of the last 200 ms. List the oldest value first. Give average vertical force in newtons under `measured_plate_force_n`. Supply a real number for every force value. Each of the ten rows under `emg_rms_volts` contains one voltage for each muscle sensor. The voltage is a measure of the size of the electrical signal in that 20 ms period, called root mean square. Use `null` if a muscle reading is absent.

The tree model needs a second force history under `other_plate_force_n`. It expects six muscle columns in the order LBF, LERS, LGAS, LRF, LST and RERS, matching the Belgian recordings. The three-pass model uses the measured plate and either four or six muscle columns. It compares each muscle reading with earlier readings from that same sensor, so its calculation uses the change in the voltage and combines those changes across sensors.

The force forecast covers the next 100 ms. A new load starts when the recorded force reaches at least 20 newtons and stays at or above 20 for 20 milliseconds. The plate is considered unloaded after 20 milliseconds between −10 and +10 newtons. The force and probability outputs have different units, so read the two numbers separately. The probability part of the three-pass model learned from the Belgian recordings. The package provides the research checkpoints and setup files.

## The first walking comparison

During a recorded walk, electrodes on the skin measure voltage over muscles. At the same time each instrumented floor plate measures how hard the person pushes against it. We used 36 walks from 12 people to fit the two new methods. Six other people were assigned to assess forecasts. We used the nine previously scored walks from the three people whose recordings included the required common sensors. Each person's results count equally, so a longer recording cannot decide the result on its own.

The physical reference extends the latest measured force through the next tenth of a second. The previous Research Edition adds a learned correction. The small convolution and LSTM first look for short patterns in the readings and then carry a memory of the past through the window. The tree model learns a sequence of decision rules from the same fitting recordings. Both of the two new methods can see the other plate's past readings. The comparison includes the benefit of an extra input.

| Forecast | Average force-impulse error (N·s) | Squared probability error |
| --- | ---: | ---: |
| Physical reference | 3.237 | 0.03995 |
| Research Edition, three passes | 2.895 | 0.03863 |
| Short pattern detector with memory | 1.933 | 0.03512 |
| Boosted trees | 1.609 | 0.02941 |

Lower values are better. The force comparison used 432 forecasts. The probability comparison used 427 cases where the measurements supported a label, including 18 rows representing eight separate new loads. The trees gave the lowest errors on these nine walks. The downloadable tree graphs repeated those predictions within 0.000017 newton-seconds and 0.00000026 probability. Forecasting all 432 histories took a median of 1.53 milliseconds with the portable runtime after it had started, versus 3.15 milliseconds with the training software on the same CPU. Opening the portable runtime took 18.66 milliseconds.

## Extra people and missing muscle readings

We added open recordings from İzmir to test a new set of people and a different laboratory. The archive had 48 additional fitting walks from 16 people and sampled one force plate 2,000 times per second. Two different programs read the recording and agreed on the raw electrical values and the calibrated force. We measured how well models from the same family worked when given recordings from 0, 4, 8 and 16 more people. The original 12 Belgian fitting people stayed in all four runs. Force error gives each lab an equal say and averages the results of three separate fits.

The three-pass error went from **3.196** to **2.442**, then **2.306** and **2.464 N·s**. The reference that extended the last force scored 5.000 N·s. More recordings helped across this series, and the eight-person addition gave the lowest error. The development comparison includes six İzmir people and eighteen walks whose data were kept outside those fits. Those recordings provide a force comparison. We used the Belgian records to score new-load probability because the imported İzmir fitting windows contained zero new loads. Six other İzmir people remain reserved. The separate Belgian final-test group also remains unopened.

The next test deliberately delayed the muscle readings by one 20 ms block or hid their latest three blocks, totaling 60 ms. It left the force readings and the measured outcomes alone. This let us measure what happens when a user's muscle signal arrives late or becomes unavailable.

We took the same saved weights and gave two models another 900 updates using 32-bit calculations. Both saw the same draws of the real fitting windows. For one model, each draw had a 15 in 100 chance of delayed muscle input and a 20 in 100 chance of a gap. We repeated this for three starting states, using fitting sets with eight or sixteen added people. The eight-person results are below. The aggregate results file also includes sixteen.

| Training | Complete readings (N·s) | 20 ms delay (N·s) | 60 ms gap (N·s) |
| --- | ---: | ---: | ---: |
| Original saved model | 2.306 | 2.886 | 8.192 |
| More training with complete readings | 1.924 | 2.800 | 7.790 |
| More training with simulated delays and gaps | 1.816 | 1.840 | 1.808 |

The drops and delays were created for the test. The force outcomes were measured in the lab. Training with generated disruptions helped in those conditions for all nine development people. With complete inputs it improved results over the clean-only continuation for seven of nine people and two of three starting states. The packaged version uses the first starting state chosen before these comparisons. The table gives the average across the three.

## Hand position from cortical recordings

The hand experiment used a direct recording from 142 units in the motor and premotor areas of one macaque's brain. A unit here is a recorded stream of grouped electrical spikes. Each forecast sees the previous 200 ms of spikes. It counts them in ten parts and marks when a recording is available. We compared the result with the two hand coordinates measured 100 ms after the forecast. The position timestamps sit on the archive's 1 ms grid. The coordinate conversion stored in the file gives the error in millimetres. For each forecast we measure the straight-line distance from the predicted point to the measured point.

With 25 fitting trials, the eight-pass model's error was **28.922 mm**. With 50 it was **23.105 mm**. With 75 it was **21.121 mm**. The best-performing linear reference with 75 trials averaged **42.707 mm**. A fixed guess based on the average fitting position scored **51.575 mm**. Adding a generated 40 ms delay to the stored spike history raised the eight-pass error to **25.047 mm**. Scores average over 991 forecasts from 15 separate development trials, with each trial counting equally.

The recordings come from one animal in one session. The ten other confirmation trials and the official benchmark's test file remain unopened. This experiment uses all 142 observed unit streams in the public fitting file, including streams that the original benchmark would hold out for a different task. The result measures forecasting across trials from this recording. The downward error curve gives a reason to continue testing with more trials and other sessions.

## The recordings and tools

The Belgian recordings are from Van Criekinge and colleagues under CC0. The İzmir recordings are from Mihcin and colleagues under Creative Commons Attribution 4.0. The macaque recording comes from the Neural Latents Benchmark under the same attribution license. The package contains weight files, the forecast program and aggregate scores. The source links provide the complete recording collections. [Belgian gait data](https://doi.org/10.6084/m9.figshare.24192480.v1) · [İzmir gait data](https://doi.org/10.48623/aperta.286865) · [MC Maze Small](https://doi.org/10.48324/dandi.000140/0.220113.0408)

The software is open source. We used c3d and EZC3D to extract the walking recordings, PyNWB to read the archived brain recordings, scikit-learn and PyTorch to fit the models, and SafeTensors and ONNX Runtime to make the saved weights reusable. Both downloads in the ZIP are walking models. The brain-signal findings are in the report and results file, where you can follow the effect of adding more trials. The available studies show both gains and dips as the fitting group changes. They leave a lasting plateau open. [EZC3D](https://github.com/pyomeca/ezc3d) · [PyNWB](https://github.com/NeurodataWithoutBorders/pynwb) · [ONNX Runtime](https://github.com/microsoft/onnxruntime)
