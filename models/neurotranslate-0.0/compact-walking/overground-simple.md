# Heel forecasts for walking over a floor

[Technical edition](overground-technical.md) · [Download the offline example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip)

The Compact model forecast the heels of 55 adults who walked barefoot through a lab. The simplest useful forecast carried the last bit of heel movement forward. It missed by **67.54 mm** on average. Accounting for the person's travel through the room brought the Compact model's error down to **25.33 mm**. This lowered the error for all 55 people.

## The movement the model sees

On a treadmill, the walking surface moves under the person. Over a floor, the whole person moves past the cameras. The Compact model learned on a treadmill. Its earlier readings showed how the heels move as the person stays near one place.

Two markers on the pelvis, near the left and right sides of the waist, help estimate how fast the person moves across the floor. Find the midpoint between them at each of the ten earlier times. Fit a straight line to the positions of that midpoint over time. It gives an average speed in each horizontal direction. Take that steady travel out of the earlier heel positions. Predict from those adjusted positions, then add back the distance the pelvis would cover in a tenth of a second at that speed.

For both versions of the model, use the two released sets of saved weights with starting numbers 2731 and 4119. Those numbers identify separate training runs. Average their forecasts in each direction. The forecasts in this comparison use positions of markers. [Frozen weights and predictor](https://github.com/eliminatenoise/NeuroTranslation/tree/2e6e3e4ac3caf3bcc5adde13ca5a5f48a3a63f46/models/neurotranslate-0.0/compact-walking)

For each heel, subtract the first position from all ten positions before running the model. This makes the input a record of the heel's movement since that first reading. The simple comparison takes the movement in the last 20 milliseconds and multiplies it by five to cover the next 100 milliseconds. The error is the straight-line distance between the forecast and the later measured marker.

## How the cameras and clocks line up

The Mainz cameras recorded both heels and the pelvis at 250 pictures per second. That gives one picture every four milliseconds. Each forecast uses ten readings taken 20 milliseconds apart from a complete 200 ms stretch of recorded history. When the forecast starts, its latest heel point is already 10 milliseconds old. The target is 100 milliseconds after that point, or 90 milliseconds after the start. [Mainz walking recordings](https://data.mendeley.com/datasets/svx74xcrjr/2)

The forecast starts are 320 milliseconds apart. Each trial uses the first two bytes of a code made from its file name with SHA-256 to pick its starting point. The code fixes the timing independently of the movement in the file. Each forecast starts from measured positions in the same room frame. The model's three directions are left, backward, and up. In the Mainz files, those directions are the Y coordinate, the X coordinate with its sign reversed, and the Z coordinate.

The file includes an error estimate for each reconstructed point. The test uses a point when its coordinates are finite and that estimate is positive, the file format's sign of a directly reconstructed reading. The files omit the identities of the individual cameras that saw each point. [C3D point format](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm)

Of **4,142** planned starts, **43** came too early for a full history and **three** had an unusable heel reading. We saved the **4,096** forecasts that remained before reading any later heel points. Each forecast covers two heels, so there were 8,192 possible positions to check. One later heel point failed the same measurement rule. One start also lacked the earlier pelvis readings needed for the adjusted model, which removed two more heel points from that comparison.

## The results

The main comparison includes **8,191 heel forecasts** from **1,104 recordings**. The unchanged model averaged **88.62 mm** there, compared with **67.54 mm** for continuing the last heel movement. The unchanged model missed by 21.08 mm more on average. The paired 95% interval was 19.84 to 22.31 mm more.

The table uses the **8,189 heel forecasts** where the earlier pelvis readings were also available. Each person's accepted errors are averaged first, so every person counts equally.

| Method | Mean heel error |
| --- | ---: |
| Keep each heel at its last position | 155.40 mm |
| Carry the last 20 ms of heel movement forward | 67.54 mm |
| Use the unchanged Compact model | 88.62 mm |
| Move each heel along with the pelvis alone | 154.45 mm |
| Remove pelvis travel, forecast, and add it back | **25.33 mm** |

The last method lowered the average error by **42.21 mm** against carrying the last movement forward. To see how that difference varied across walkers, we drew groups of 55 from the study participants 10,000 times, allowing the same person to be drawn again. Each draw kept both methods' errors for every chosen person. The middle 95% of those differences ran from **40.56 to 43.76 mm lower**. Two other walkers helped check the camera files before testing began. The model weights stayed fixed throughout. These results apply to barefoot walking measured by physical markers in this lab.

The archive tells us when each picture was taken. The time a live system would need to turn a picture into a usable marker reading remains unmeasured.

Fabian Horst, Sebastian Lapuschkin, Wojciech Samek, Klaus-Robert Müller and Wolfgang I. Schöllhorn released the Mainz recordings under CC BY 4.0. The scores above are calculations from their recordings. [Dataset and licence](https://doi.org/10.17632/svx74xcrjr.2) · [Original study](https://doi.org/10.1038/s41598-019-38748-8)

## Run the example

1. Install Node.js 18 or later and extract the offline ZIP. Open the launcher for your computer in the extracted folder.
2. The program prints forecasts for an invented example. Read **target_ms** to see when the forecast ends. In **predictions_mm**, each method gives a left-foot triple followed by a right-foot triple. Each triple gives the movement in millimetres from that heel's last measured position.
3. To supply your own file, use the same three fields as **overground-example.json**. Put ten times in **time_ms**, exactly 20 milliseconds apart. Put the ten pairs of heel readings in **heel_mm** and the ten pairs of pelvis readings in **pelvis_mm**. For each row, give the left marker's three coordinates before the right marker's three. Measure positions in millimetres. Each triple gives distance to the left, backward, and upward in the same fixed room frame. Use direct marker readings throughout.

To run your file, open a terminal in the extracted folder and enter the following command with your file name.

```sh
node overground.mjs your-file.json
```
