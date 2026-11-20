# How far ahead should an arm sensor look?

A sensor on a walker’s right arm measures acceleration in three directions. Give the model 16 readings from that sensor. What will it read just under half a second from now? One model can answer that question directly. Another can predict the next 40 milliseconds, feed its answer back in and repeat the exercise twelve times. Both start with the same measurements. By the last step, the recursive model has filled most of its input with its own guesses.

**For this walking forecast, use one equation for each time you want to predict.** The equation learns how much weight to give each earlier reading, with a penalty that keeps the weights from becoming too large. This is called *direct ridge regression*. It made smaller errors than feeding each guess into the next (recursive ridge), using an existing sequence model with its trained weights fixed (a pretrained Transformer), or repeating the last reading, on each of two development participants at 120, 240 and 480 milliseconds. At 40 milliseconds the two ridge methods share the same fitted equation. The four direct forecasts together use 588 fitted coefficients and intercepts. [Results by person, condition and axis](results.json)

| Time after the last reading | Direct ridge | Recursive ridge | Chronos-Bolt tiny, median | Repeat the last reading |
| --- | ---: | ---: | ---: | ---: |
| 40 ms | **0.549** | **0.549** | 0.654 | 0.647 |
| 120 ms | **0.781** | 0.807 | 1.096 | 1.182 |
| 240 ms | **0.880** | 0.913 | 1.487 | 1.685 |
| 480 ms | **0.918** | 1.001 | 1.415 | 1.412 |

Each number is the average size of a miss, ignoring whether the prediction was high or low. This measure, called *mean absolute error*, uses the same 1,680 histories and three sensor axes, in the instrument’s stored acceleration units. Four people supplied the training data. Two others, both already assessed in an earlier study, supplied repeated windows from parking-lot and treadmill walks. The two remaining people stayed in reserve. Neither the error nor its growth measures how far a hand moved in space. The instrument rotated with the arm and retained gravity. [Study protocol](protocol.json) · [UCI recordings and licence](https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities)

## What did the Transformer buy?

At 120 ms we could also compare two locally fitted Transformers on these same people. The dedicated arm model scored 0.855 and the broader hand/arm model scored 0.869. Ridge scored 0.781. A newer shared Transformer handles five placements, including both legs and the torso. Its five-placement results come from training participants, so its scores answer a different question. [Dedicated arm study](../README.md) · [Five-placement study](../../daily-sports-limbs/README.md) · [Earlier arm comparisons](earlier-results.json)

Chronos-Bolt answers a different part of the question. Can we download a general time-series model and get a useful arm forecast with no local training? We ran the tiny checkpoint intact, offline. It gives nine predicted levels for each future reading. For example, its middle level is the median: half of comparable readings should fall below it. These levels are called quantiles. It processes each axis separately, whereas the ridge models can use relationships across all three axes. Bolt groups consecutive readings into blocks. Sixteen readings fill one block. A longer history, adaptation on training people, or a model trained to use all three axes could change the order. The comparison tests these actual choices together. [Pinned model card](https://huggingface.co/amazon/chronos-bolt-tiny/blob/a0e552de83495b5c28c14c71c374f3e33280b340/README.md) · [Pinned configuration](https://huggingface.co/amazon/chronos-bolt-tiny/blob/a0e552de83495b5c28c14c71c374f3e33280b340/config.json)

The quoted probability also needs a check. At 240 ms, Bolt’s central 80% intervals contained 67.0% of X readings, 89.6% of Y readings and 76.8% of Z readings. Four neighbouring pairs of predicted levels appeared in the wrong order somewhere in the comparison. The outer bounds stayed in order. The direct ridge runner gives a point estimate. A stated probability of covering the next observation would require a separate calibration sample and a check on new participants. [Interval widths, coverage and quantile losses](results.json)

| Local inference | Parameters | Median | 95th percentile |
| --- | ---: | ---: | ---: |
| Direct ridge, four horizons | 588 | 0.021 ms | 0.077 ms |
| Recursive ridge, twelve steps, four reported | 147 | 0.123 ms | 0.166 ms |
| Bolt, nine quantiles on each axis | 8,652,672 | 11.799 ms | 14.220 ms |
| Earlier arm Transformer, 120 ms only | 17,891 | 1.022 ms | 1.341 ms |

These are 64 warm single-history calls on a Ryzen AI MAX+ 395 workstation. We used two CPU cores, one BLAS thread and CPU PyTorch. The measurements start with the 16 readings in memory and end with the numerical output. Acquisition, packet delay, the user interface and startup take additional time. The complete study process, including imports, took 12.17 seconds and peaked at 510 MiB of resident memory. This run uses the CPU. Radeon throughput, power consumption and end-to-end live timing remain unmeasured. [Runtime and full scores](results.json)

## What should NeuroTranslate build?

Keep the compact direct head for this sensor. Keep the locally editable temporal Transformer for a harder question. Can the earlier wrist angle, the cue on the screen, scalp EEG and forearm EMG together tell us more about the *next measured wrist angle* than motion history alone? On a separate pointing dataset, adding scalp EEG to the temporal motion-and-cue model raised development error from 4.053° to 4.523°. In a separate comparison a fitted correction using forearm EMG reduced error from 3.957° to 3.853°. Those are different comparisons against different baselines. The sensors supply voltages, the encoders supply angles, and the words describing the experiment come from its protocol. [Wrist temporal comparison](../../wrist-pointing-temporal/README.md) · [Forearm correction](../../wrist-forearm-transfer/README.md)

For that work, reuse the existing source-specific input layers, timestamps, missing-input masks and directly scored outputs. Fit a small residual head on the paired data first. Compare ridge, a shallow temporal convolution and the current Transformer on the same people, channels and forecast horizons. Assess each additional channel against removing it and substituting a different trial. Try a frozen pretrained encoder plus the same head only if the gain survives that comparison and the local latency budget. This keeps every weight, unit conversion and output available for inspection.

“Raise your right arm” asks for a different kind of answer. Several movements can satisfy the instruction. Start by retrieving a rights-cleared, annotated movement clip and reporting its source and body coverage. That gives a command, an observable response and a reference against which a generator can earn its place. A Transformer is a way to combine inputs across time. Autoregression specifies the order in which new steps are generated. Diffusion specifies how a model iteratively refines a noisy candidate. Either generation method can use a Transformer. The representation could be continuous joint angles or learned discrete motion tokens. A sensor-frame acceleration history supplies neither a full skeleton nor a language annotation. [Text-to-motion retrieval](https://openaccess.thecvf.com/content/ICCV2023/papers/Petrovich_TMR_Text-to-Motion_Retrieval_Using_Contrastive_3D_Human_Motion_Synthesis_ICCV_2023_paper.pdf) · [Autoregressive motion tokens](https://arxiv.org/abs/2301.06052) · [Motion Diffusion Model](https://guytevet.github.io/mdm-page/)

For streaming commands with fresh observations, test short autoregressive chunks that can be corrected when the next observation arrives. For offline generation of several plausible motions per prompt, compare a conditional diffusion model against retrieval and an autoregressive model. Split clips by performer and source before fitting. Measure prompt success, time to the first useful motion, missed contacts, foot sliding against a known floor, trajectory error where a matched reference exists, and diversity over a fixed number of samples. Report failures and individual samples alongside averages. An animation that satisfies the words still needs simultaneous independently measured physiology to support claims about brain, nerves or muscle.

## Which parts can we reuse?

The Chronos 2.3.2 code and the pinned Bolt tiny model card specify Apache 2.0. The weight file is 34,622,352 bytes. We used it in place and kept its original identity. The associated Chronos data collection lists component licences separately. The pinned card does not give enough provenance to rule out overlap between its pretraining mixture and these walking recordings. [Code licence](https://github.com/amazon-science/chronos-forecasting/blob/0aba28e9360b6355d5a919596c90b16c25939f02/LICENSE) · [Model terms](https://huggingface.co/amazon/chronos-bolt-tiny/blob/a0e552de83495b5c28c14c71c374f3e33280b340/README.md) · [Data collection terms](https://huggingface.co/datasets/autogluon/chronos_datasets/blob/eeecad0b82a8c237e212ce6f8d1abecb513e2cec/README.md)

Tevet and colleagues’ Motion Diffusion Model provides MIT-licensed code and lists a 50-step HumanML3D checkpoint. Its pinned release describes the MIT grant for the code. We could not verify a separate unrestricted redistribution grant for those learned weights. HumanML3D draws from AMASS and HumanAct12. The published AMASS terms limit use to specified non-commercial purposes and restrict redistribution and commercial training. We reviewed the method and kept its weights, motion files and body-model assets outside this preview. For a freely distributable generator, start with cleared clips and annotations and preserve each component’s terms through adaptation and export. [MDM code licence](https://github.com/GuyTevet/motion-diffusion-model/blob/ef8edce6a53c6ab19e53b4d4dcf15bc0bc60a778/LICENSE) · [Checkpoint listing](https://github.com/GuyTevet/motion-diffusion-model/blob/ef8edce6a53c6ab19e53b4d4dcf15bc0bc60a778/README.md) · [HumanML3D sources](https://github.com/EricGuo5513/HumanML3D/blob/9176e8fb446b71c7d2a725eb5cf6fec1ae3b3c23/README.md) · [AMASS terms](https://amass.is.tue.mpg.de/license.html)

## Run a forecast

Install Python 3 and NumPy. Open the launcher for your system or run the command below. The default input contains 16 invented readings. Replace it with a matching recorded history in the same JSON format to forecast that sensor.

```sh
python predict.py example.json
```

[Linux launcher](<Open Forecast on Linux.sh>) · [macOS launcher](<Open Forecast on macOS.command>) · [Windows launcher](<Open Forecast on Windows.cmd>) · [Reproduce the study](REPRODUCE.md) · [Pinned files and credits](sources.json)
