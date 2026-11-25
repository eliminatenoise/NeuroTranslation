# Reaching forecasts on the six reserved recordings

The motion-only linear forecast had the lowest average error on the six people set aside before training. It estimated how much the spread of tracked points inside two arm muscles would change about 300 milliseconds later. Its average error was about 4% lower than predicting that the spread would stay the same. The uncertainty range for each muscle still includes a tie.

## What changed between the two images

The recordings follow people reaching with an arm. The research team tracked points in ultrasound images of the triceps and brachialis. For each muscle, spread measures how far four tracked points sit from their centre in the image. The forecast predicts the difference between the newest measured spread before the forecast starts and the spread in a later image. A positive answer means more spread. A negative answer means less.

The earlier browser preview estimates the amount of spread at the later time. The methods in this comparison estimate the change. They use the previous 200 milliseconds of motion and, for two methods, voltages recorded at the skin from muscle activity. Ultrasound supplies the measurements that define the answer.

## How the recordings were used

The methods were chosen on the original 24 training people. The six reserved people came from the same study. The final weights, starting rules and comparisons were set before retrieving their recordings. Preparing the archive produced two separate files, one with the earlier histories and one with the measured changes. The forecast program read the earlier histories and saved its estimates. Scoring then opened the measurement file and compared those estimates with what happened.

Both muscles had measurements from all six people across 7,503 forecast times. Each person's average counted equally. The errors below give the average distance between the predicted and measured changes in millimetres. Lower values are closer to the measurements.

| Method | Triceps | Brachialis | Average |
| --- | ---: | ---: | ---: |
| Predict no change | 0.1766 | 0.1419 | 0.1592 |
| Linear forecast using motion | 0.1738 | 0.1318 | 0.1528 |
| Recurrent forecast using relative motion | 0.1787 | 0.1358 | 0.1572 |
| Recurrent forecast using positions and muscle readings | 0.2062 | 0.1535 | 0.1799 |
| Recurrent forecast using relative motion and muscle readings | 0.1998 | 0.1653 | 0.1825 |

The linear method reduced error for four of the six people on each muscle compared with predicting no change. For the pair of recurrent methods that used muscle readings, measuring from each marker's recent starting position lowered triceps error and raised brachialis error. The uncertainty range includes a tie for triceps. The range for brachialis stays on the side of higher error.

The results apply to one reaching task and measurements in a two-dimensional ultrasound image. The timing check used the timestamps in the recording files. Some motion readings and ultrasound measurements are so close to the forecast start that the gap is within the precision of those stored numbers. A live forecast would need a separate check of when the sensors delivered each reading. All five tested methods are available in the download. [Technical report](TECHNICAL.md)

The reaching dataset is by Pallarès-López and colleagues under CC BY 4.0. [Original study](https://doi.org/10.1038/s41597-026-07019-3) · [Recordings](https://doi.org/10.6084/m9.figshare.31030252.v1)
