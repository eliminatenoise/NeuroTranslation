# Downhill treadmill force forecasts

[Run the browser model](https://eliminatenoise.github.io/NeuroTranslation/walking-force/decline/) · [Simple edition](README.md) · [Download the offline comparison and checkpoints](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/emg-floor-load/decline-treadmill/Decline-Treadmill.zip)

On a held 10° decline, the nine-pass compact forecast had a total impulse mean absolute error of **9.579 N·s**, against **16.325 N·s** for the static reference. The measured body mass and nominal slope determine that reference and scale the compact forecast. The compact forecast improved for all four people. Its 0.053 N·s lead over seven passes held for two. With muscle readings alone, a linear fit led at **21.875 N·s**, with lower error than the 23.063 N·s fixed reference for two of four people. [All 22 forecasts and individual-plate scores](TRANSFER-RESULTS.json)

## Held 10° protocol

Six people supplied 1,060 fitting windows from the authors' 5° decline. Four different people supplied 708 windows at 1.2 m/s from a separately annotated 10° decline in the same lab. Earlier studies used other recordings from some of these people. The methods, 22 forecasts and matched scoring coordinates were fixed before opening the held numerical force values. An independent calculation re-read 283,200 distinct force values and reproduced the scores.

For each plate, sum negative local vertical force `−Fz` across the next 200 rows on the stored 2,000 Hz clock and divide by 2,000. Positive impulse represents compression. The primary comparison adds the two signed impulses before taking absolute error. Average windows within each person before giving the people equal weight. Both plates had observations during all 708 windows. Separate-plate reporting required each plate to exceed 10 N·s and to have a window above 1 N·s while the other was at or below 1 N·s. One person's 174 windows support the primary total alone. The individual-plate results cover 534 windows from three people. Plate labels follow recording order.

The six ordered surface electromyography channels are left and right biceps femoris, tibialis anterior and rectus femoris. They occupy 400 stored rows ending at sample `t−21`, inclusive, for issue tick `t`. Each 40-row bin gives a mean squared voltage deviation. Bins 4–10 take the natural logarithm of one plus the square root of that energy divided by the mean energy of all earlier bins. The first three bins supply a reference. The original instruments use different sampling rates. The stored timing test establishes an archive margin of 10 ms. Physical device delays and availability during acquisition are unresolved. [Original recording methods](https://doi.org/10.1038/s41597-023-02840-6)

## Matched models

The models read muscle features in either condition. With mass `m` and nominal slope `θ` supplied, the fixed total is `m × 9.80665 × cos(θ) × 0.1`. The fitted models in this condition learn recorded impulse divided by that static impulse and rescale their outputs. The muscle-only models train in physical units and use the fitting median as their fixed reference. The two contexts use different fitted models and target scales.

The compact forecast has width 32, four attention heads, feed-forward width 64 and one block reused 1, 3, 5, 7 or 9 times. Fitting uses FP32, AdamW, 48 epochs, batches of 128, learning rate 0.001 and weight decay 0.0001. Each person has equal weight. The loss averages the absolute error on individual plates and the absolute error on the total. Each variant averages two runs fitted from different starting weights. In a warm CPU replay of 708 prepared windows, five, seven and nine passes took about 22, 29 and 35 ms respectively. This measures the warmed model calculation.

The full Research Edition supplies a frozen three-pass representation with 2,304 values per window. The calculation uses FP32 with the upstream packed weight values. Regularized linear readouts fitted in FP64 use either the same 42 relative muscle features, the full representation, or both. A separate fit averages the two output forecasts. It gives the full forecast zero weight in both contexts. Each average equals the relative-muscle output for its own condition, including mass and slope scaling when supplied.

| Total impulse error in N·s | Muscle alone | Muscle, mass and slope |
| --- | ---: | ---: |
| Fixed reference | 23.063 | 16.325 |
| Linear fit | 21.875 | 11.009 |
| Compact, five passes | 23.775 | 9.715 |
| Compact, seven passes | 24.387 | 9.633 |
| Compact, nine passes | 25.521 | 9.579 |
| Full Research Edition readout | 22.935 | 14.769 |
| Joint Research Edition and muscle readout | 22.168 | 10.969 |
| Weighted average of the two forecasts | 21.877 | 11.322 |

## Separate 5° comparisons

Movement inputs were studied using one-person-out development fits among the same six fitting participants and 1,060 windows. Every method received measured mass and slope. The static reference scored 16.204 N·s and the muscle readout 10.362. Eight body-worn acceleration magnitudes scored 6.558. Combining muscle and wearable readings scored 6.218, lower than muscle alone for all six people. A fitted trajectory from the midpoint of the two anterior pelvis markers scored 3.727. A mechanical estimate based on projecting pelvis acceleration scored 25.816. We used the same anterior pair for all six and checked wearable units against the authors' export. The optical midpoint is a geometrical proxy. The exact optical preprocessing and real-time availability of its positions remain uncertain. The 10° experiment used neither the wearable nor camera readings. [Movement scores](MOVEMENT-RESULTS.json)

The earlier 5° held comparison uses 16 absolute voltage channels with a different summary. Its main 539-window comparison covers three people, with a separate 712-window sensitivity check for all four. Three short passes scored 21.97 versus 26.79 N·s for mean plate error. Five passes over one second scored 19.30 versus 30.32 N·s for combined impulse. The one-second linear model scored 0.1326 versus 0.2192 for the average squared error of predicted load probabilities. Including the fourth participant changed some rankings. [Earlier complete methods and setup](https://github.com/eliminatenoise/NeuroTranslation/blob/3766e5263f4f62cb5c2e8a80b27e8622f2dc03f3/benchmarks/emg-floor-load/decline-treadmill/TECHNICAL.md) · [Earlier result tables](RESULTS.json)

## Run the browser forecast

Use the hosted runner or open **Run Forecasts.html** after extracting the ZIP. The three **Open Forecast on** launchers open that file in the system browser under Linux, macOS and Windows. The page contains its runtime and 479 unquantized FP32 or FP64 arrays from the published checkpoint. It reads local CSV files and needs no browser permissions or network services for prediction. It was exercised offline on Linux Chromium. The macOS and Windows launchers were checked as source.

The example starts with invented voltages, 72 kg, a slope of −10° and nine passes. The voltage control scales the selected channel at raw input rows 120–399, the latest 140 ms. Choose any of the five depths and either output-scaling condition. A local file uses 400 rows of readings in volts at 2,000 Hz, with the history ending 10 ms before the forecast starts. Convert microvolts to volts by multiplying by 10⁻⁶. Enter one sample per line and decimal fields with optional quotes. Import clears mass and slope and starts with five passes and muscle input alone. Fitted methods report both plates and their total. The reference reports the total. The browser shows the compact, linear and relative-muscle forecasts, with the late blend equal to the relative-muscle fit. The Python runner below also accepts a matching external Research Edition representation.

The browser stores checkpoint arrays at their original precision and uses JavaScript number operations with 32-bit layer buffers. The Gaussian error linear unit uses an error-function approximation. The frozen Python comparison ran the browser model code in Node.js on the same 708 prepared histories. It covered 18 method and scaling combinations and 35,400 values, including individual plates and totals. Maximum absolute difference was below **0.00008 N·s**. The earlier accuracy results retain the original predictions. To rebuild the page from the saved weights and the invented CSV, run `python3 docs/walking-force/decline/build_browser.py` with NumPy installed from the repository root. [Handbook formula 7.1.26](https://digital.library.unt.edu/ark:/67531/metadc40302/m1/315/)

## Run the Python forecasts and recorded comparison

1. Extract the ZIP and open **Compare Results.html** offline. Select the study, the 10° scaling condition or an earlier 5° error measure. For inference, install Python, NumPy and the CPU build of PyTorch for the same interpreter. [PyTorch installation](https://pytorch.org/get-started/locally/)
2. In the extracted folder run `sh "./Run Transfer Linux.sh"`, `sh "./Run Transfer macOS.command"`, or `".\Run Transfer Windows.cmd"` in Windows Command Prompt. The command prints plate and total impulse forecasts in JSON for invented voltages. It defaults to five compact passes. Add measured `--mass-kg` and `--slope-deg` together for the second condition. For an invented example use `--mass-kg 72 --slope-deg -10`. This condition defaults to nine passes. Select any released depth with `--passes 1`, `3`, `5`, `7` or `9`.
3. Pass a CSV filename with 400 finite rows in volts after the exact header `LBF,LTA,LRF,RBF,RTA,RRF`, using archive timing and nonzero variation in each channel's first three bins. For prepared NumPy inputs use the keys `relative` with shape `[windows,7,6]` and `muscles` with those six labels in order. The older `Launch` scripts still run `predict.py` with the earlier example and input schema.
4. For the two full-model readouts, `--research-state` accepts a NumPy file with `representation` shaped `[windows,2304]` in the same row order. Supply scalars `base_checkpoint_sha256`, `relative_projection_sha256` and `passes` from the model manifest. The base, input projection and representation export are separate from this download. The compact, linear, relative-muscle and weighted-average forecasts run directly. [Model manifest and weight identities](TRANSFER-MODEL.json)

The extracted Linux commands were executed. The macOS and Windows wrappers were checked as source. The test concerns recorded treadmill load in one lab. Performance in other labs, on other movements, on live inputs and in a feedback loop requires separate evaluation.

Original project code and coefficients use CC0 to the extent of project rights. Scherpereel and colleagues supply the recordings under CC BY 4.0. The separate Thinking Machines Lab base retains its publisher's terms. [Dataset and licence](https://repository.gatech.edu/entities/publication/20860ffb-71fd-4049-a033-cd0ff308339e) · [Original project licence](LICENSE) · [Pinned base model card](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/blob/657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2/README.md) · [Base model acceptable-use policy](https://thinkingmachines.ai/model-acceptable-use-policy/)
