# Muscle & motion

Extract the complete ZIP into one folder. Open **index.html** in a current browser, or use the launcher for Windows, macOS or Linux. Each launcher opens the same local file in your default browser. On systems that restrict a downloaded launcher, open **index.html** directly. The models, input editor and recorded-result tables work offline. Links to the paper, recording atlas and other companion pages use the internet.

Choose whether the invented person stands or walks, then set the imposed visual rotation. Scale the recent signed leg voltages or the three-dimensional pelvis motion. To change any of the 160 samples, open **Edit individual samples**, edit the JSON and choose **Apply edited input**. The file `synthetic-event.json` contains the original invented example. Each signed-voltage row lists tibialis anterior, soleus, medial gastrocnemius and peroneus longus for the left leg, followed by the same four for the right. Each marker row gives ML, SI and AP in millimetres.

The joint Transformer forecasts the RMS voltage of each muscle over the next 125 ms and the full 32-position sacrum path over the same period. Each position is relative to the cutoff. The two specialists each forecast their own outcome. Choose a comparison, inspect a time point and expand the tables for the numerical outputs. Standing, walking and the direction of the scene rotation form part of the input to both model types.

The practical references carry forward the eight RMS values from the last 32 observed samples. One repeats the previous path, a second holds the marker at zero and two more continue its average movement per sample over the last 16 or 32 steps. A study table compares these references, the fitted models, a posture-and-cue average and a regularized linear predictor with the human recordings. The measured and forecast group-average tables have separate columns for each quantity. The JSON file `results.json` gives the full displayed results before rounding.

With Node.js installed you can also run `node predict.cjs synthetic-event.json joint` or `node predict.cjs synthetic-event.json specialists`. Additional comparison names are `repeat`, `stationary`, `velocity16` and `velocity32`. The output contains eight future RMS values in µV and 32 triples in mm.

See [sources and reuse](NOTICE.md) for the versioned dataset and the authors’ research. The file `SHA256SUMS` lists the checksums of the package contents.
