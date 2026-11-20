# Forecast the next 100 milliseconds of handle movement

A macaque held a handle while a robot briefly pushed it. Later in the same trial a visual cue prompted a reach. Given the preceding 200 milliseconds, how far will the handle move in the next 100? These models return two numbers, the predicted horizontal and vertical changes in position, in centimetres. The archived robot encoders provide the comparison.

The study uses one active/passive reaching session from macaque C, recorded on 12 September 2017. The neural input counts events from 30 putative sorted units in cortical area 2. Each unit label belongs to that recording. Encoder preprocessing may use later samples during filtering, so the result applies to forecasts on the published archive. It does not measure live sensor latency or establish that the neural activity caused the movement. [Study](https://doi.org/10.7554/eLife.48198) · [Data, CC0](https://doi.org/10.5061/dryad.nk98sf7q7)

## Make one forecast

The example uses a synthetic history with the handle fixed at the origin, no spikes and no available cues. Its purpose is to check the interface. With Python and NumPy, run the command below from this directory.

```sh
python predict.py out/weights-all-17.json synthetic-history.json
```

In a browser, load the adjacent `predict.js` with a classic script tag. Pass the parsed weights and history objects directly to `Area2Forecast.predict(weights, history)`. The function runs offline and returns an array of two finite numbers. Modern JavaScript modules can import the same `predict` function from `predict.mjs`. The arithmetic mean of the output vectors for seeds 17, 41 and 73 gives the three-fit forecast.

## Supply a recorded history

Use `session` equal to `C_20170912_COactpas`. The five rows of each input run from oldest to newest. The last row ends at the forecast cutoff.

| Key | Measurements in one 40-ms row |
| --- | --- |
| `movement` | Endpoint x and y in cm, followed by x and y change from the start of that bin in cm. |
| `neural` | Thirty nonnegative integer spike counts, summed from the preceding four complete 10-ms rows. |
| `unit_ids` | Thirty ordered strings such as `ch12:sort1`. Match the electrode and positive sort IDs of the supplied neural data to the weights. |
| `cue` | Seven values in order. Perturbation known, cosine, sine, target known, cosine, sine, go known. Flags are 0 or 1. A hidden direction has cosine and sine both zero. A known direction has a unit-length cosine/sine pair. |

Take spike counts strictly before each endpoint. Use a cue only if its event row is earlier than the endpoint. This distinction matters at the instant a trial is anchored to a recorded cue. The archive gives the event's 10-ms row but loses its position within that row.

Choose weights by the measurements you have. The six filenames use `all`, `movement_cue`, `neural_cue`, `movement_only`, `cue_only` or `neural_only` before the seed number. Each is a separately trained model. An omitted required input raises an error. The optional omitted modalities in the smaller models need no fabricated zero observations.

## Reproduce the fits

Use the source reader and its original-trial partition to prepare separate `train.npz`, `validation.npz` and `test.npz` files. The precise row ordering, unit guide and cue encoding are part of the source contract. The native runs used PyTorch 2.14.0, NumPy, a single CPU thread and 32-bit floating point. The Python reader evaluates in double precision. The public weight files include their fitted scales and all learned parameters.

With this directory as the working directory and the prepared blocks in `../source`, the following commands write a fresh copy of the fitted weights, native forecasts and reference checks. Respect the chronological order when using these scripts to evaluate the recorded study. All model and preprocessing choices were fixed before assessment.

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python train.py fit --data ../source/train.npz --out reproduced
python train.py validation --data ../source/validation.npz --out reproduced
python verify_portable.py validation --data ../source/validation.npz --out reproduced --report reproduced/validation-check.json
python train.py test --data ../source/test.npz --out reproduced
python verify_portable.py test --data ../source/test.npz --out reproduced --report reproduced/test-check.json
```

The reference checks call Node.js as well as Python. Each prediction archive preserves the original trial, perturbation or reach epoch, offset, and source row. In the wrong-trial control, the joint model receives another original trial's neural history at the same event-relative offset with the same cue status at the cutoff. Rows without such an earlier donor carry NaN for that control. The training archive is labelled in-sample. Validation and test use later original trials.
