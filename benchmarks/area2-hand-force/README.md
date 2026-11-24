# Hand movement from motion, force and sensory cortex

The [separate-day test](separate-day/) compares fixed and adaptive blends of the motion and force forecast and the forecast that also uses Area 2.

We tested how much these three measurements help forecast where the hand will move over the next tenth of a second. The forecast starts when we know the current hand position. It is scored against the position recorded a tenth of a second later.

The recording comes from one macaque moving a handle. Some trials included a push from the handle. The archive includes position, the force between the hand and handle, and electrical activity from part of the brain that receives sensory signals from the arm. The archive lists a hand position and a set of handle-force readings every millisecond on the same recorded clock. All six forecasts below were scored on the same 624 times from 74 later trials. Each trial counted equally. [Recorded data](https://dandiarchive.org/dandiset/000127/0.220113.0359) · [Original experiment](https://doi.org/10.7554/eLife.48198)

## How the comparison worked

The forecaster started with the measured hand position and worked back over the previous fifth of a second. It divided that history into ten periods of 20 milliseconds. Each period started with a hand position relative to the current one and, where applicable, three handle-force readings in newtons. The handle also measured twisting effects, which were kept out of the force inputs. Where brain activity was included, the model counted electrical events from each of the 65 recorded units in Area 2, an arm-sensing region, in each of the ten periods. Every result uses the same starting times, so each comparison isolates the effect of changing the inputs on the same test movements.

We put the trials in order. The first 218 taught the model how to turn those measurements into a forecast. The next 72 helped choose how tightly the model should fit the earlier examples. Each fitted model selected the smallest tested setting, 0.0001. This setting limits how large the fitted numbers can become. The final 74 were kept for testing. We made forecasts 20 milliseconds apart in the first two groups and 320 milliseconds apart in the final group. The larger spacing in the test kept each forecast's future hand position out of the inputs for other forecasts. We made and saved all six sets of predictions for that final group before looking up the later hand positions to score them.

The stay-put prediction simply says that the hand will still be at its current position. The constant-speed prediction measures how far and in which direction the hand moved over the last 20 milliseconds, then assumes it will keep moving at that speed and direction. The other four predictions learn how to combine the available readings from the earlier trials.

| Information used | Average endpoint error | Average error in distance alone |
| --- | ---: | ---: |
| Last position, kept unchanged | 8.018 mm | 8.018 mm |
| Direction and speed measured over the previous 20 ms, kept unchanged | 4.159 mm | 3.185 mm |
| Recent hand positions | 2.396 mm | 1.818 mm |
| Recent hand positions and handle force | 2.276 mm | 1.695 mm |
| Recent hand positions and sensory cortex activity | 2.453 mm | 1.824 mm |
| All three measurements | 2.328 mm | 1.716 mm |

Adding force to recent positions reduced the average error by 0.121 mm. A range estimated by resampling whole trials puts the gain at 0.041 to 0.203 mm for this recording.

Adding sensory cortex activity to motion and force increased average error by 0.052 mm. The resampling range runs from a 0.003 mm gain to a 0.107 mm loss. The averages hide a difference between kinds of movement. When the hand moved under 2 mm, adding the sensory signal raised the error from 0.881 to 1.221 mm. For movements from 2 mm up to 10 mm, the average error rose by 0.064 mm. From 10 mm up to 20 mm, the error fell by 0.300 mm. When the hand moved at least 20 mm, it fell from 6.237 to 5.674 mm. The resampling range for the gain in that largest group was 0.324 to 0.804 mm. These four groups came from the later measurements, after the forecasts were frozen. They contained 239 forecast times from 73 trials, 225 from 73, 77 from 48 and 83 from 62, respectively. One trial can have forecast times in more than one group. A forecast-time rule for using the brain signal on larger movements would need to identify those movements from information already available and then pass a separate test.

## Reading the errors

The main error measures the straight-line distance between the forecast's endpoint and the recorded endpoint. It counts getting the direction wrong as well as guessing the wrong distance. The results file also shows an error for distance alone. In that second measure, a prediction can get the distance of a move right while pointing in the wrong direction.

The force measurement comes from the handle where it touches the hand. A change in that force gives the model another clue about the movement already underway. The extra measurements do not have to improve every guess to help on average. To compare two forecasts we work out how much their errors differ on each original trial. We repeat the average 4,000 times by drawing whole trials from the same group, with some drawn more than once. The middle 95% of those averages gives the range shown above for the kinds of trials in this recording.

A bump flag applies to a whole trial. Some forecasts in a trial with a bump were made before or after the push itself.

The study uses one recording and a linear prediction model. The original archive smoothed the recorded hand position with a filter set at 100 hertz. The file leaves the filter's timing effects and any delay between instruments unknown, so these results describe predictions made from the stored data. This study measures the value of adding force or brain activity under those test conditions.

## Run the comparison on prepared inputs

Use Python with NumPy. Save [infer.py](infer.py) and [linear-weights.npz](linear-weights.npz) in the same folder. The second file contains the fitted numbers used by the program. Make a file called `inputs.npz`. An NPZ holds several named tables of numbers. Give the program these three tables, with one set of readings per forecast time.

| Table name | Readings for one forecast time |
| --- | --- |
| `motion` | Ten pairs of hand coordinates in millimetres relative to the hand position at the forecast time |
| `force` | Ten sets of three force readings in newtons |
| `counts` | Sixty-five units in the archive's order, with ten counts of electrical events for each unit |

Put the ten samples or counts in time order, starting with the oldest. Use the same coordinate axes and neural unit order as the archive. Open a terminal in the folder and run `python infer.py inputs.npz forecasts.npz`. The program writes one `forecasts.npz` file with six named tables, one for each forecast method. Each row gives the predicted x and y movement in millimetres. The oldest hand and force readings are from 200 milliseconds before the forecast time, and the last are from 20 milliseconds before it.

The original recording is available under the Creative Commons Attribution 4.0 licence. [Technical edition](TECHNICAL.md) · [Numerical results](results.json)
