# Heel forecasts across eight walking days

[Technical edition](multiday-technical.md) · [Download the offline example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip)

The Compact walking model missed by **27.11 mm** when it used recent pelvis movement to account for the person's travel across the room. The simple forecast that extended recent heel movement missed by **72.09 mm**. The adjusted forecast had lower average error than either simple movement rule for each of the seven people tested.

## What the forecasts use

Cameras tracked small reflective markers while people walked barefoot over a floor. The test used markers near both heels and two more near the front of the pelvis. The cameras recorded their positions 250 times per second. A heel position has three numbers that say where the marker sits in the room. This forecast estimates how far the heel will move left, back and up over a tenth of a second. [Walking data and recording methods](https://doi.org/10.17632/8kyv4jm759.1)

The Compact model learned from treadmill recordings. On a treadmill the walking surface moves beneath the person, who stays near one spot. Across a floor the body travels through the room as the foot swings. The two pelvis markers let us estimate that travel. For each of the ten earlier readings, we find the halfway point between those markers. A straight line through the ten halfway points gives the average travel speed in each horizontal direction. We take away that steady travel from the earlier heel movements, run the same trained model, then add the travel the pelvis would cover in a tenth of a second.

For each heel we used its first selected position as the starting point. Subtracting it from the later positions gives movement since that first reading. The simple heel forecast takes the movement in the last 20 milliseconds and multiplies it by five. It expects the heel to keep moving in the same direction at the same speed. The separate pelvis-only forecast gives both heels the same movement as the pelvis. That check tells us how far the steady travel alone can take us. We also tried leaving the heels where they last were and using the original Compact model directly. We ran both Compact methods using two saved versions trained from different starting numbers, 2731 and 4119, and averaged their forecasts direction by direction. The forecasts use recorded positions alone. [Frozen model and predictor](https://github.com/eliminatenoise/NeuroTranslation/tree/2e6e3e4ac3caf3bcc5adde13ca5a5f48a3a63f46/models/neurotranslate-0.0/compact-walking)

## How we checked each forecast

We used two walks from one person to check the file format and marker positions. We excluded all of that person's walks from the comparison. The other seven people had 829 recorded walks. Fifteen files lacked a unique label for each heel, so 814 walks contributed forecasts. We used the same saved model and adjustment as in the first study. The model received ten earlier readings 20 milliseconds apart, drawn from a full 200 milliseconds of recorded history. The target was 100 milliseconds after the last reading or 90 milliseconds after the scheduled start of the forecast.

In each walk we scheduled one forecast every 320 milliseconds. We computed the first start from a code based on the recording's file name, using SHA-256 to get the same schedule on every run. The schedule was set independently of the positions in that walk. Of 2,266 scheduled starts, 31 came too early for a full history and three had an unusable earlier heel reading.

The cameras' file includes a number that describes the reconstruction of each point. We used finite positions with a positive value for that number, the format's sign that the point was reconstructed from measurements. After checking the earlier heel readings, we saved 2,232 forecasts, then opened the later heel readings to check them. Each forecast gave two heel positions. All 4,464 later readings passed the check. The files leave individual camera identities unspecified on those points. Thirty-one forecasts lacked a complete earlier pelvis history, leaving 4,402 heel positions for comparing all five methods. [How C3D records marker quality](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm)

## How far the forecasts missed

For each heel, we measured the straight-line distance between the predicted and recorded position. We averaged those distances for each person and gave every person equal weight.

| Forecast on the same 4,402 heel positions | Average error |
| --- | ---: |
| Keep the heel in its last position | 173.97 mm |
| Continue the last bit of heel movement | 72.09 mm |
| Use Compact as released | 95.50 mm |
| Move both heels at the recent pelvis speed | 165.76 mm |
| Account for pelvis travel and use Compact | **27.11 mm** |

The adjustment lowered average error by **44.98 mm** compared with extending recent heel movement, and by **138.65 mm** compared with using pelvis travel alone. To see how sensitive these differences were to which people took part, we made 10,000 groups of seven from the same participants, allowing people to be picked again. Both forecasts always used the same group. The middle 95% of the differences ran from 43.00 to 47.14 mm lower against the heel rule and from 134.63 to 142.41 mm lower against pelvis alone. Seven people give limited evidence about other walkers.

The adjusted forecast also had lower average error than both rules on each of the eight recording days. Its daily error ranged from 26.19 to 27.85 mm. Five people contributed on the first day, and seven contributed on each later day. The people returned for more than one recording day. The two Mainz studies used separate releases from the same research site, and the published records leave participant overlap unresolved. This test measures heel movement from archived camera coordinates. Force and the time required to track points live were outside the comparison. [Daily scores and counts](multiday-results.json) · [Earlier overground study](overground-simple.md)

## Run the example

Install Node.js 18 or later, extract the offline download, and open the launcher for your computer. The example uses invented marker positions. The program prints how far the forecast moves each heel from its last position. To enter your own readings, use the three fields in `overground-example.json`. Supply ten times 20 milliseconds apart, followed by the matching heel and pelvis positions. Each position uses millimetres to the left, backward and up in the same room frame. For each paired reading, put the left marker first. [Offline download](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/neurotranslate-0.0/compact-walking/overground-preview.zip) · [Input instructions](overground-simple.md#run-the-example)

Fabian Horst, Franziska Kramer, Bastian Schäfer, Alexander Eekhoff, Patrick Hegen, Benno M. Nigg and Wolfgang I. Schöllhorn released the original measurements under CC BY 4.0. The errors and comparisons above are calculated from those recordings. [Dataset and licence](https://doi.org/10.17632/8kyv4jm759.1) · [Original paper](https://doi.org/10.1016/j.gaitpost.2016.07.073)
