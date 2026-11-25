# Forecasting changes in muscle point spread during a reach

[Technical report](TECHNICAL.md) · [Reaching forecast preview](../)

Points tracked inside the upper arm move closer together or farther apart during a reach. This experiment tested whether earlier arm motion and muscle electrical readings could predict those changes in an ultrasound image. A linear forecast using motion alone had the lowest average error. Predicting no change was close behind.

## What the forecast measures

The recordings contain points tracked inside two upper arm muscles, the triceps and the brachialis. For each muscle, the spread measures how far four points sit from their centre in the ultrasound image. The earlier browser preview forecasts how much spread there will be. This study forecasts how much that spread will change from the last measured value to the measurement around 300 milliseconds after the forecast starts. A positive change means the points spread farther apart. A negative change means they moved closer to their centre.

The main forecasts used the previous 200 milliseconds of arm movement. Some also received muscle voltages recorded at the skin, called EMG. Ultrasound supplied the measurements used to define the change they predict and to check their answers. A separate reference forecast continues the earlier ultrasound trend.

## How the study kept people separate

We used the 24 people from the original training pool. We divided them into six groups of four. A model learned from 20 people at a time and forecast for the group of four it had never seen. We repeated that process until everyone had forecasts. The comparison covered 29,664 forecast times. Each muscle had measurements from 23 people because two recordings each lacked a different muscle's measurements. Within each muscle, every method was scored on the same people and observations. Each person's average error counted equally.

## Selected comparisons

| Method | Average error across the two muscles |
| --- | ---: |
| Linear forecast using motion | 0.1377 mm |
| Forecast that the spread stays the same | 0.1389 mm |
| Best recurrent model using motion | 0.1418 mm |

The linear forecast had a small lead over predicting no change. For each muscle, the uncertainty range includes a tie. Carrying the ultrasound trend forward gave an average error of 0.1436 mm. The recurrent model learned to read the history and then repeat an update to its internal state. Its lowest error came after 800 training updates with one such refinement. For that same model, 1,600 and 3,200 training updates raised the average error to 0.1457 and 0.1495 mm when run with one refinement.

For the recurrent models that used motion and EMG, we also compared original shoulder-relative positions with positions measured from where each marker started within its recent history. Measuring from each marker's starting position lowered the average error from 0.1602 to 0.1464 mm in the matched comparison. Adding EMG to that relative motion helped on average at the matched settings, with enough variation across people that the uncertainty intervals included zero.

These same internal groups supplied the model choices. The [reserved comparison](reserved/) reports the test on the six people set aside before training. The target is a change in tracked point spread in a two-dimensional image. The recordings are by Pallarès-López and colleagues and carry a CC BY 4.0 licence. [Original study](https://doi.org/10.1038/s41597-026-07019-3) · [Recordings](https://doi.org/10.6084/m9.figshare.31030252.v1)

[Download the aggregate scores](RESULTS.json)
