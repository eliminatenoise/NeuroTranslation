# Pinch and hook forecast methods

The target is the change in each of four optically measured finger-base joint angles eight frames after the last input. The browser adds the last angle to each predicted change and displays the resulting angle in degrees. At the archive's nominal 25 Hz, 101 consecutive past frames span four seconds and the lead is 320 ms.

## Input and execution

Open the browser forecast or extract the ZIP, run the desktop launcher and choose **Pinch and hook forecasts**. Import a JSON object with one `history` array of 101 rows in chronological order. Use four finite values per row for index, middle, ring and pinky angles in degrees. The optional twenty-value format appends sixteen logged ultrasound tile means. For each 636 × 256 ultrasound frame, apply its stored amplitude scale, average each rectangle in a 4 × 4 grid and take `log1p` of each mean. Supply the tiles in row-major order. The predictor subtracts each tile's first value in the input history before applying its fitting mean and standard deviation.

For native inference, open `pinch-and-hook/checkpoint` in the extracted ZIP. From that directory install the dependencies with `python -m pip install -r requirements.txt`. Run `python predict.py --example` for an invented input or `python predict.py readings.json` for a compatible file. The output gives absolute later angles in index, middle, ring and pinky order for the trend and the applicable learned models. `MODEL.json` identifies the saved calibration and recurrent tensors.

## Models

The hold rule carries forward the last angle. The trend extrapolates a least-squares line fitted to the last five angles. Replay compares the latest ten angles of each finger with ten earlier angles ending 8–75 frames before the current issue. Its cost is the mean squared angle difference plus half the mean squared difference between the two sequences' first differences. The shortest delay wins a tie. At the chosen match, replay reads the angle eight frames later. That value is already in the input history. The adaptive rule compares replay with hold at the nine earlier issues from 16 to 8 frames before the current issue. It selects replay only when its mean absolute error was lower on those nine completed forecasts.

The fitted comparisons use angles, ultrasound, or both. Each linear model uses ridge regression with a penalty of 0.01 on coefficient size. Each recurrent model filters the current and two earlier samples, updates a 24-value state with a gated recurrent unit, then applies three shared refinement passes and a four-value output. Training used 160 AdamW updates of 64 windows under each of two seeds. Predictions average the two seeds. Each of the six exported networks has 8,764 FP32 parameters. The export preserves the FP64 ridge coefficients and calibration. Browser inference rounds normalized inputs and recurrent states to FP32. Across 27 invented histories, the largest absolute difference from the frozen Python learned forecasts was 0.0000221°.

## Development comparison

Each of eight test splits excluded one participant and every recording of the scored gesture from training. Within each split, the models trained on 21 recordings from the other three participants and predicted the three speeds for the excluded person and gesture. All methods received the same eligible forecast times and 101 frames of their respective inputs. Of 33,192 candidate times in 24 recordings, 2,184 occurred during history warm-up and 31,008 remained. The windows overlap. Errors are averaged within recording and across the balanced speeds, participants, gestures and four fingers. The runnable models come from a separate fit on 51,680 windows in 40 development recordings. The table combines the predictions from the eight test splits for each method.

Mean absolute errors in degrees were **4.03** for replay, **5.67** for angle-only ridge and **6.70** for hold. Adding centered ultrasound raised ridge error to **9.61** and recurrent error from **9.75** to **10.08**. The later adaptive diagnostic averaged **4.00** on the same cases. At Fast speed its **3.94** lay between hold at **3.81** and replay at **4.25**. Each result describes repeated movements under a single archive protocol. Live sensor timing and transfer to additional people require separate measurements. [Aggregate scores](RESULTS.json)

Keshav Bimbraw's dataset is available under CC BY 4.0. The browser examples are invented. [Source recordings](https://doi.org/10.5281/zenodo.21825018) · [Recording methods](https://doi.org/10.1109/TMRB.2023.3237774)
