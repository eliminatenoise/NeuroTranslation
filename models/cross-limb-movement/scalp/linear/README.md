# A straight-line alternative to the neural network

A ridge regression learns one set of numerical weights for the wrist and another for balance. For each 125 ms forecast it starts with the last muscle amplitudes and the marker's recent velocity. It then estimates a correction using earlier marker positions and muscle activity. One version also reads the earlier scalp measurements. The other gets the same list of available electrodes and a constant reference value for each.

With the reference inputs, the average path errors were 2.327 mm for the pelvis and 5.446 mm for the wrist. Adding the scalp history increased these to 2.431 and 5.657 mm. Of the four prespecified comparisons within this linear analysis, only wrist muscle amplitude favored the added scalp measurements at its uncertainty threshold. These comparisons concern 18 balance participants and six grasp participants in development. The linear fits used every available training example with person-balanced weights. The neural models instead trained on repeated samples using a fixed update budget. [Results in the original units](results.json) · [Methods](DESIGN.md)

To reproduce the linear fits from this folder, prepare the two development files and the earlier-trial matches as described in the parent study. Use Python with NumPy. The output directory contains the group results, the trained numerical weights and a private array of individual forecasts.

```sh
OPENBLAS_NUM_THREADS=1 python linear.py --motion /path/to/movement/development.npz --scalp /path/to/scalp/development.npz --support /path/to/input/support.npz --out /path/to/linear-output
```

The coefficient archive holds two sets of weights and their input scales for each study and held participant group. It contains no individual recordings. The central-minus-reference column in the result file subtracts one error from the other on the same participants. The wrong-trial comparison uses only events with an eligible earlier recording.
