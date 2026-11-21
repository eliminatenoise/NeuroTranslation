# Forecast how a hand-held cylinder turns

A volunteer carried a cylinder to a target. A small instrument attached to the cylinder recorded how fast it turned and the acceleration it experienced. The models take the previous 200 milliseconds of those readings and estimate their average over the next 100 milliseconds. The display lets you alter an earlier sensor reading and see how the forecast changes. A measured outcome belongs to the original recording.

Open the launcher for your operating system or open `reader/index.html`. The reader works offline. [Try the model](https://eliminatenoise.github.io/NeuroTranslation/cylinder-rotation/) · [Rotate the instrument in 3D](https://eliminatenoise.github.io/Interoceptomics/cylinder-rotation/)

## What the repetitions showed

On 2,653 matched windows from 379 later trials in the same 24 people, the full Transformer’s average miss in angular velocity was **0.1584 radians per second**. A model given earlier turning rate, hand, destination and time missed by **0.1622 rad/s**. The paired interval for the difference extended across zero. Giving the full model acceleration from another matched trial increased its error to **0.1772 rad/s**. The lowest error among the tested models was **0.1508 rad/s**, using both sensors and omitting the target number. The study split repetitions separately for each person, hand and target. Some assessment trials occurred earlier in their hand session than fitting trials for different targets. [Study, paired intervals and secondary results](https://eliminatenoise.github.io/NeuroTranslation/papers/cylinder-rotation/)

The orientation comparison starts at the last input orientation and applies the forecast rotation for a tenth of a second. The full model’s mean orientation error was **0.909°**, compared with **1.185°** for holding the last orientation. The reference is the orientation estimate from the same device. The orientation calculation does not measure how far the cylinder travelled.

## Calculate one forecast

Install NumPy and run the following command from the extracted folder. Each three-component output uses the coordinate axes of the instrument. Acceleration includes gravity.

    python model/portable.py weights/full-17.json example.json

The archive contains 18 fitted Transformer checkpoints, five ridge regressions, 100-Hz sample windows from all three study partitions, and the code and reports for angular velocity, acceleration and orientation. The sixth Transformer input-and-loss condition fits only angular velocity. Its acceleration output has no interpretation and is omitted by the command. [Learning settings and comparisons](model/METHODS.md) · [Original recording guide](source/README.md)

## Rebuild the study

Python 3.11 or newer, NumPy and a CPU installation of PyTorch are sufficient. The fitting set contains repetitions three through six within each hand and target. The later two groups contain repetitions seven/eight and nine/ten. The first two repetitions were used in a separate optical study and are outside these partitions. A new run writes to the output folders you choose.

    python model/train.py source/train.npz rebuilt/weights --threads 1 --device cpu
    python model/score.py source/test.npz source/train.npz rebuilt/weights rebuilt/results
    python model/native.py source/test.npz rebuilt/weights rebuilt/results
    python orientation/kinematics.py score orientation/test.npz rebuilt/results/forecasts.npz rebuilt-orientation.json

To recreate the arrays from the publisher’s archive, first follow [the source instructions](source/README.md), then build quaternion endpoints on the same recording clock with `python orientation/kinematics.py extract source/test.npz source/_private/test rebuilt-quaternions.npz`. The source program’s archive-cache folder is local to your computer. No hidden service or account is needed for the supplied model weights.

Tim Sziburis, Susanne Blex, Tobias Glasmachers and Ioannis Iossifidis created the Ruhr Hand Motion Catalog (2025). We selected task repetitions and time windows, retained the sensor frame, fitted forecasting models and derived orientation errors. Underlying measurement arrays, source-derived parameters and figures carry CC BY 4.0 attribution and modification notes. Original project code and explanatory text are CC0 1.0. [Data deposit](https://doi.org/10.17605/OSF.IO/J3QC8) · [Original study](https://doi.org/10.1038/s41597-025-05576-7) · [CC BY 4.0](CC-BY-4.0.txt) · [CC0](LICENSE)
