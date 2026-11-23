# Stand and sit force forecast — Simple edition

The preview uses the last 200 milliseconds of force on two floor plates to estimate the force impulse on each plate over the next 100 milliseconds. The browser opens with invented readings, so you can try it without a force plate or a recording. The sections below explain how to use it, how it makes a forecast, and how the forecasts matched three sets of recorded chair trials.

## Open the preview and read the screen

1. Extract the ZIP into a folder. Keep the files in that folder together.
2. Open `Open on Linux.sh` on Linux, `Open on macOS.command` on macOS or `Open on Windows.cmd` on Windows. You can also open `index.html` in a desktop browser. The browser runs offline.
3. In **Force history**, choose **Steady load**, **Rising load** or **Falling load**. Each is an invented set of ten force averages for each plate. Choosing a preset replaces all ten rows.
4. Read the chart from left to right. The left edge is 200 milliseconds before the forecast. Zero is when the forecast starts. The chart draws one point in the middle of each 20-millisecond interval. The label **Force (N)** means the chart shows newtons, the unit of force.
5. Read **Impulse over the next 100 ms** below or beside the history. It has one row per forecast method and columns for Plate 2, Plate 3 and their sum. The units here are newton-seconds (N·s). The status line states how much the average force changed and whether the learned correction is active.

Edit the force boxes to try your own prepared readings. Enter a finite number in every box. Leaving a box blank removes the forecasts until the history is complete again. Select a preset to restore a full set of values. If the browser reports that the scripts did not load, keep `weights.js` and `predict.js` in the same folder as `index.html` and reopen the page.

Keep the time and units separate as you read. The graph shows force that the model receives as input. The table shows how much future force each method expects to add up on each plate. The recorded scores later in this guide measure the size of past forecast errors. They do not supply a measured answer for an invented browser history.

## Run the same released predictor in Python

Use Python with NumPy, PyTorch and safetensors installed. The `model/` folder contains the predictor and the two files of learned weights. From the extracted folder, run the supplied example.

```sh
python model/predict.py example-rising.json
```

To use your own prepared readings, give the command the name of your file. The file is plain text in the JSON format. It contains a list of ten pairs, starting with the oldest. Each pair lists Plate 2 first and Plate 3 second. Both values are force in newtons, with upward force written as positive. The program needs all ten pairs and all values must be finite.

The result is a small JSON object. Read `persistence` for the recent-force forecast, `dampedTrend` for the forecast that lets the recent trend level off, and `attention` for the trend with the learned correction. Each of these contains two values in newton-seconds in the original column order. Add them for the combined value shown by the browser. Read `loadChangeN` for the signed difference between the last and first 40 milliseconds of average total force. Read `rising` for the correction rule. It is true when that difference is greater than 50 N.

The included `example-rising.json` starts with pairs `[180, 220]` and `[182, 224]`. Their combined readings are 400 and 406 N, so the average for the first 40 milliseconds is 403 N. The final two pairs sum to 651 and 675 N, with an average of 663 N. The rise is 260 N, so the learned correction is active. The browser’s presets provide other invented examples.

The last pair in that file is `[300, 375]` N. Holding those forces for 100 milliseconds gives 30.00 N·s for Plate 2 and 37.50 N·s for Plate 3. The total is 67.50 N·s. If you enter all ten pairs from the file in the browser, the damped-trend total is 73.93 N·s and the corrected total is 66.37 N·s, rounded to two places. The lower forecast here simply means the correction reduced the estimated impulse. This invented history has no measured outcome to decide which forecast came closer.

## Prepare the force readings and the measured answer

A floor plate uses sensors to measure the force between a foot and the floor. The measurement here is vertical force. A positive value points upward. If you want to compare a prediction against real measurements, use calibrated readings. Calibration puts the sensor output in known units so the same number means the same amount of force.

Start by choosing a forecast time and calling it zero. Use only force readings from before it to make the history. For each plate, divide the preceding 200 milliseconds into ten consecutive intervals of 20 milliseconds and average the readings in each interval. The first interval starts at −200 and stops before −180 milliseconds. The last starts at −20 and stops before zero. Include a sample on the start of an interval and exclude a sample on its end. That puts samples on a boundary into just one interval. At 1,000 samples per second, 20 readings go into each average.

The measured answer uses an interval that starts at zero and stops just before 100 milliseconds. Force is a push at a moment. Impulse measures how much force adds up over time. To measure it from a recording, multiply each of the later force readings by its duration, then add the products. If the sensor records 1,000 samples each second, each reading covers 0.001 seconds and 100 readings make up the outcome. A force of 300 N held for 0.1 seconds gives an impulse of 30 N·s. A reading that changes over this time gives a different sum.

Work out the measured impulse separately for each plate. Their sum is the combined outcome. The prediction target covers only upward force on those two plates. A person can also put weight on a chair or handrail. Those forces require their own measurements. The future readings are used to score a forecast after it is made.

## Two reference forecasts

A reference forecast is a simple rule for comparison. The two references here use the same earlier force readings as the compact model. They need no learned model weights.

### Recent force

Take the most recent average on each plate, which covers −20 to 0 milliseconds. Hold that force level through the next tenth of a second. Multiply each plate’s number in newtons by 0.1 seconds. This gives the impulse forecast in N·s. The Python output calls this row `persistence` because it carries the recent level forward.

### Damped trend

The latest force alone misses the direction of a recent change. The trend uses five averages per plate. Their middle times are −90, −70, −50, −30 and −10 milliseconds. It fits a straight line to those five points to estimate how many newtons the force was gaining or losing per second. For the calculation, turn the times into seconds and measure each time from the average of the five times. Multiply each centred time by its matching force and add the products. Divide that sum by the sum of the centred times squared. The result is the slope, or rate of change. This rule chooses the line whose squared differences from the five readings add up to the smallest value.

Begin with the last measured average at the midpoint of its bin, 10 milliseconds before the forecast starts. Use the fitted slope to change that value forward in time. The rule gradually reduces the slope. It uses a 50-millisecond time constant, which means the rate falls to about 37% of its starting size after each additional 50 milliseconds. The force approaches a level from below when the slope is positive and from above when it is negative. The rule uses the fitted slope from the last five readings and the actual last average as its starting force.

To convert that curve into an impulse, divide the next 100 milliseconds into 100 one-millisecond intervals. Estimate the force at each midpoint, starting at 0.5 ms and ending at 99.5 ms. Multiply each estimate by 0.001 seconds and add them. Do this for each plate. The Python output calls the pair `dampedTrend`.

## Compact model and the rising-load rule

The **Trend with attention correction** row starts with the damped trend. The model estimates how far that forecast might miss on each plate. It adds that estimate only when the two plates’ combined force rose enough during the input history.

1. Add Plate 2 and Plate 3 in each of the first two rows, then average those totals. That is the mean combined force in the first 40 milliseconds.
2. Do the same with the final two rows. Subtract the first mean from the last mean. That gives the signed change `Δ` in newtons.
3. A value greater than +50 N counts as rising load and turns the compact correction on. A value below −50 N counts as falling load. The range from −50 to +50 N, including either exact boundary, is called low-change. In both of those groups, the compact forecast is exactly the damped trend.

These labels describe what the force was doing before the forecast. They differ from the direction of the whole movement. For example, a person rising from a chair can press harder at one moment and ease off at another. The rising and falling groups in the score tables are based on the earlier force readings, whatever the person’s overall chair movement.

### How the compact model uses the ten pairs

Two copies of the same model were fitted with different starting seeds, 2731 and 4119. A seed is a number that fixes a run’s starting randomness. The downloaded weight files use 32-bit floating-point numbers, called FP32. Both copies use the same way of preparing the inputs.

- For each Plate 2 reading, subtract a centre of about 297.91076 N and divide by a scale of 230.35035 N. For Plate 3, use a centre of about 159.76071 N and a scale of 131.79498 N. Subtracting the centre sets a reference level. Dividing by the scale puts the differences into a range the model was fitted to read. The stored files keep more digits than shown here.
- Turn each pair of prepared numbers into a list of 32 values. To make each value, multiply the two input numbers by weights that the model learned, add the products, and add a learned offset. An offset is a number added after the multiplication. Add a pattern made from sine and cosine waves to identify its place in time. That keeps the oldest and most recent lists distinguishable to the model.
- In one attention block, use the most recent list to compare all ten lists. Include an extra learned list, called the null vector. This is a stored set of values the model can choose to give weight to. It does not come from a plate. The comparisons turn their results into shares. Each share is zero or more, and the shares add up to one. The model changes each list through another multiply-and-add calculation, multiplies the result by its share, then adds the results together. A higher share lets one list contribute more to the sum. There are four comparisons at the same time, each using eight of the 32 values. These groups are called attention heads.
- The model adds the result to the values that were already there and then adjusts the new list. It subtracts the average from each number. To find how spread out the numbers are, it squares their differences from the average, averages those squares, adds a small positive number, and takes the square root. It divides the centred numbers by this spread. It then multiplies each number by a learned value and adds a learned offset. This series of steps is called layer normalization. The added positive number keeps the rule usable if the values have no spread.
- The model sends the adjusted values through a layer 64 values wide that replaces negative intermediate values with zero, then converts the result back to 32 values. It adds the values that went into this step and normalizes again. This lets the model represent changes that a straight-line trend alone cannot express. The final calculation gives two numbers, one per plate.

Each full saved fit contains 11,618 adjustable values called parameters. It includes a branch for six markers, or points on the body that could be tracked by a camera. The preview marks them all missing. That branch adds zero, so the released forecast uses the force readings only. The browser performs that force-only calculation using the same two fits. The browser and Python use different arithmetic implementations for the same forecast rules.

Each fit estimates a correction to the trend for each plate. The correction is the model’s estimate of measured impulse minus the trend forecast. Average the two models’ output numbers for the same plate. Multiply the average by 25 N·s to restore the unit of impulse, then add it to the trend forecast. Do this only when the rise rule applies.

## The separate Research Edition comparison

The offline preview runs the compact NeuroTranslate 0.0 predictor. The Notre Dame replay also tested two ways of adding corrections with the separate Research Edition. The larger model is a transformer. It uses attention to combine readings. In these combinations the model can give some readings more weight than others. The model’s learned settings stayed fixed during the comparison. It converted the earlier force readings into a list of 2,304 numbers in three passes using 32-bit floating point. The same fixed list-making calculation was used for both correction methods. A list that summarizes the input in this way is often called a representation.

A small calculation called a linear readout turns that list into an impulse correction. It multiplies each of the 2,304 prepared values by a learned weight, adds them up and adds a fitted constant. It does this for each plate. The number it tries to match during fitting is the measured impulse minus the damped-trend estimate for that plate. Training those small calculations leaves the large model’s weights fixed.

Both readouts were fitted on the same four earlier Utah development participants. Each person counts equally within each fit. The preparation step subtracts the weighted average of every feature and divides by its spread across the fitting examples. The spread is the population standard deviation with those same weights. A spread of `1e-12` or less is replaced with 1 to keep it from multiplying tiny changes. Divide the prepared values by 48, the square root of 2,304. The fit adds a penalty of 0.25 to discourage large weights. This is called ridge regression. The added constant is exempt from that penalty.

- **Changing-load correction.** Fit the readout on the 647 earlier windows where the total combined force changed by more than 50 N in either direction. Use it at a rise above +50 N or a drop below −50 N. Use the damped trend alone for everything from −50 to +50 N, including both endpoints.
- **Correction at every forecast.** Fit a second readout on all 2,822 earlier development windows. Add this correction in every force group, including low-change windows.

The Research Edition rows in the Notre Dame tables come from those two readouts. The browser’s learned-correction row comes from the smaller predictor and applies only to rising load.

## Read the error tables

1. For one case, add the two forecasts. Separately add the two measured impulses. Subtract the totals and take the size of the difference. For example, a prediction of 60 N·s and a measurement of 63 N·s give an error of 3 N·s. So do a prediction of 66 N·s and the same measurement.
2. Average all the errors for one person in the group being reported. Then give each person equal weight when averaging those personal averages. If one person contributed more cases, that person still counts once. That is the **equal-person mean absolute error**. Here it is always measured in N·s.
3. Compare smaller errors with larger ones in the same column. Each method uses the same eligible cases in a comparison. The all-window and force-group columns answer different comparisons. The force groups use the past readings and the outcomes use the later measured force.

The three recordings below come from different sites. Each table shows what happened in its own test. The sites differ in the recordings they supplied, what was qualified for scoring, and how the force had been exported.

## Utah test on reserved people

Four people supplied recordings used to fit the models. Three other people were assigned to the test and kept out of the fit. The first 30 seconds of each reserved recording were used for a fixed force-calibration check on the shared recording clock. Two people passed. The third person’s recording had too few loaded readings on one plate during that check.

After the prefix, make a forecast every 300 milliseconds. Each uses 200 milliseconds of earlier samples and the next 100 milliseconds of later samples. The input and outcome samples are separate, and each case has its own samples. The researchers saved and verified the forecasts before opening the later outcomes for scoring. This left 230 paired cases from the two eligible people, including 24 rising-load cases.

| Forecast | All 230 cases (N·s) | 24 rising-load cases (N·s) |
| --- | ---: | ---: |
| Recent force | 2.86 | 7.59 |
| Damped trend | 2.69 | 6.82 |
| Damped trend plus attention correction | 2.36 | 3.65 |

The compact correction gave lower overall error for both people. It reduced the all-case mean error from 2.69 to 2.36 N·s relative to the damped trend. The difference is concentrated in the 24 rising-load cases. The other 206 cases give exactly the same forecasts with the learned correction listed and with the damped trend listed. These are results from two people who passed the fixed check in one archive.

## Leeds replay of saved chair trials

This comparison ran the compact model saved from Utah on a different archive. The weights stayed fixed. It used 402 chair trials from 134 people. Forecasts were 300 milliseconds apart on the stored force clock. Each history used the preceding 200 milliseconds and each outcome used the next 100 milliseconds, with separate samples for each case. The replay scored 6,739 windows, including 892 in the rising group.

The compact model expects plate readings in a fixed order. The Leeds record has numbered plates. The lab documentation did not establish which Leeds number matches each Utah column. The researchers fixed both orders before running the comparison, Plate 1 then Plate 2 and the reverse. They returned each prediction to the Leeds plate numbers before scoring. Both orders appear in the table as separate results.

| Forecast | All 6,739 windows (N·s) | 892 rising-load windows (N·s) |
| --- | ---: | ---: |
| Recent force | 2.837 | 6.835 |
| Damped trend | 2.099 | 4.567 |
| Damped trend plus correction, plate 1 then 2 | 2.105 | 4.749 |
| Damped trend plus correction, plate 2 then 1 | 2.117 | 4.853 |

Look at the damped-trend row and the two rows beneath it. Across all cases, the trend’s 2.099 N·s is lower than 2.105 and 2.117 N·s. The same ordering holds in the rising-load column when comparing the trend with either correction. Count each person separately and the story is mixed. In each plate order, the correction gave lower overall error for 60 people and higher error for 74. It gave lower error under both orders for 53 people. Another 14 had lower error in one order and higher error in the other.

The archive makers filtered the exported force readings to reduce rapid changes. The replay follows the time order of that file. A filter can use readings from either side of a time, so whether the filtered values could have been available at the time of a live forecast depends on how the filter ran. Its direction in time and availability of the original readings on live hardware remain unverified. These results describe the Leeds replay. [Acquisition and export methods](https://www.nature.com/articles/s41597-026-06925-w) · [University of Leeds dataset](https://doi.org/10.5518/1701)

## Notre Dame replay of chair rises and descents

Nine people each supplied three chair rises and three descents. A different person supplied the engineering check. The replay used all 54 available short recordings from the nine scored people. Each foot was on a separate Kistler force plate. The archive gives 1,000 calibrated readings per second. The replay uses signed upward force in newtons and the time saved with the force samples. It uses the force exported before the study’s later software filter. It leaves out the cameras and the chair plates. Part of the chair sat outside the instrumented area.

### Build the same set of cases for every method

1. In each clip, use the 200 force samples before the forecast and the 100 samples following it. The earlier samples make ten force pairs for the forecast. The later samples give the impulse to score it against.
2. Move forward in steps of 300 milliseconds while enough samples remain. This yielded 146 paired forecasts across the nine people. Seventy occurred during chair rises and 76 during descents.
3. Sort the windows by the change in combined force over the earlier 200 milliseconds. There were 23 rising, 38 falling and 85 low-change windows. There were separate checks by chair direction because either force group can occur in either movement.
4. Run the compact and Research Edition methods on the same windows. The recorded order of the input columns influences the models. Fix left-first and right-first input orders before scoring. After each run, put the output values back in the order of the actual feet.
5. Save the forecasts and reproduce them from earlier samples before decoding the outcomes. This let the later measurements serve as answers to score the already saved forecasts.

### Forecasts averaged across plate orders

For the main table, average the two left-foot forecasts, then average the two right-foot forecasts. Add those foot averages to get a combined forecast for the case. Then compute its error. The two forecasts are averaged before measuring the size of the miss. This can give a different answer from separately scoring the two orders and averaging their errors. The first two rows are the recent-force and damped-trend rules, which are computed for each foot independently.

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Recent force | 2.130 | 1.521 | 2.770 | 2.115 |
| Damped trend | 1.731 | 1.282 | 2.260 | 1.761 |
| Compact correction, average of both orders | 1.805 | 1.610 | 2.260 | 1.761 |
| Research Edition, correction during changing loads | 1.679 | 1.501 | 1.938 | 1.761 |
| Research Edition, correction at every forecast | 1.709 | 1.262 | 2.193 | 1.745 |

The changing-load Research Edition correction had the lowest overall error at 1.679 N·s. The damped trend had 1.731 N·s. The difference is an improvement of 0.052 N·s in this replay. Overall error was lower for five of the nine people. In falling-load cases it was lower for eight. In rising-load cases the corrected average was higher than the trend’s 1.282 N·s. The all-case result and individual groups describe different parts of the same recordings.

### Forecasts kept separate for each plate order

The next table gives the scores when each order is used on its own. The baseline scores in the first table apply to these comparisons as well. The compact correction gave higher mean overall error than the trend in either order. Keeping the order rows lets a reader see how much the numbers depend on the arrangement of the inputs. It also keeps the interpretation tied to the two orders chosen before the scores were available.

| Forecast | All 146 windows (N·s) | 23 rising-load windows (N·s) | 38 falling-load windows (N·s) | 85 low-change windows (N·s) |
| --- | ---: | ---: | ---: | ---: |
| Compact correction, left first | 1.796 | 1.551 | 2.260 | 1.761 |
| Compact correction, right first | 1.816 | 1.681 | 2.260 | 1.761 |
| Research Edition during changing loads, left first | 1.703 | 1.337 | 2.169 | 1.761 |
| Research Edition during changing loads, right first | 1.694 | 1.711 | 1.864 | 1.761 |
| Research Edition at every forecast, left first | 1.700 | 1.232 | 2.219 | 1.735 |
| Research Edition at every forecast, right first | 1.724 | 1.314 | 2.171 | 1.760 |

### Size and uncertainty of the difference

The comparison of the changing-load Research Edition correction with the damped trend uses the nine people’s paired differences in error. Each pair has two scores from the same person. To examine variation across people, the researchers repeatedly drew nine such pairs from the original nine, allowing a pair to appear more than once in a draw. They did this 20,000 times. The resulting 95% interval was 0.006 to 0.106 N·s of improvement. It describes uncertainty across the people in this archive. The force-phase and plate-order results reuse the same recordings.

The changing-load Research correction and the trend gave errors of 1.496 and 1.584 N·s during chair rises. During descents they gave 1.858 and 1.878 N·s. Those are comparisons by direction of the chair movement. They are separate from the force-phase columns, which depend on the earlier force in each window.

The 54 clips are short recordings from one archive. The replay uses the stored timing and the exported force measured at the feet. Timing inside the devices, calibration when the plates were unloaded, and original availability of the readings in a live setup remain unverified. [Recording methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/) · [Dataset version 1](https://doi.org/10.7274/28689221.v1)

## Recording credits and reuse

The examples that come with the browser are invented. The comparisons used averages of calibrated upward force and report group scores. To find the actual research recordings, use the dataset links below. The recording releases use Creative Commons Attribution 4.0 International, which asks people who reuse them to credit the source. The project’s code, fitted weights and documentation are dedicated to the public domain under CC0 1.0. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)

- **Utah stand-up and sit-down recordings.** Grace Hunt, K. Bo Foreman, Tommaso Lenzi, Lukas Gabert and Colby Hansen published the dataset in 2024. The comparison takes averages of upward force from the two floor plates and reports forecast errors for the two people who qualified. [Figshare dataset, version 2](https://doi.org/10.6084/m9.figshare.26282872.v2)
- **Leeds chair trials.** David Lunn, Enrico de Pieri, Graham Chapman, Stephen Ferguson and Anthony Redmond published the dataset in 2025. David E. Lunn, Enrico De Pieri, Graham J. Chapman, Morten E. Lund, Stephen J. Ferguson and Anthony C. Redmond describe how the measurements were taken and processed in a 2026 paper. The replay averages the released vertical force and reports group errors. [University of Leeds dataset](https://doi.org/10.5518/1701) · [Scientific Data methods article](https://www.nature.com/articles/s41597-026-06925-w)
- **Notre Dame chair recordings.** Mohsen Alizadeh Noghani, Sebastian Green and Edgar Bolivar Nieto released the data. The replay averages calibrated foot-force readings from before the study’s software filter and reports summary forecast errors. [Dataset version 1](https://doi.org/10.7274/28689221.v1) · [Recording and processing methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12717423/)
