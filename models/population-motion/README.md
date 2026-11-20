# How far will a rat move in a quarter of a second?

A camera already gives you a good clue. You can see how fast the rat is moving and whether it has just turned. Can recordings from its brain sharpen that forecast when the model has never seen this rat before?

Only one of three test rats met both comparisons we set in advance. For KL8, adding the correctly timed firing lowered the model’s average error from 2.466 to 2.369 cm. Substituting firing from an earlier trip raised it to 2.449 cm. Even for this rat, simply continuing at the last observed speed did better, with an error of 2.296 cm. For JS21 the movement-only model did better than the model with firing. For JS34 an earlier trip’s firing performed about as well as the correctly timed recording. The three rats give little basis for a general claim about what firing in these two areas adds to movement history.

| Rat outside training | Forecasts | Continue at last speed | Movement only | Movement + firing | Movement + earlier trip’s firing |
| --- | ---: | ---: | ---: | ---: | ---: |
| JS21 | 152 | 3.541 | 3.153 | 3.208 | 3.182 |
| JS34 | 130 | 3.739 | 3.074 | 3.033 | 3.031 |
| KL8 | 267 | 2.296 | 2.466 | 2.369 | 2.449 |
| **Equal weight per rat** | **549** | **3.192** | **2.898** | **2.870** | **2.887** |

Every number in the last four columns is an average absolute error in centimetres. A smaller number means the forecast came closer to what the camera measured. The table gives each of a rat’s 15 scored trips equal weight before averaging across rats. The firing histories came from dorsal CA1, part of the hippocampus, and the prefrontal cortex (PFC). With just three test animals from one study, individual differences carry more information than the small average change of 0.028 cm. [Full results by rat and trip](scores.json) · [Timing and equal-window comparison](timing-and-pooled.json)

## Follow one trip

At the first eligible instant in JS21’s second selected trip, the movement-only model predicted **8.45 cm**. Adding firing gave **8.61 cm**. The rat moved **1.83 cm** between the two camera samples. The first camera sample was already 30 ms old at the forecast cutoff, and the next one used for scoring came 250 ms after it. Over those 280 ms its final position was much closer to its starting point than any of the models predicted. This trip and forecast were selected by their order before we saw the errors. [Earlier observations](example-input.json) · [Full trip with camera, firing and forecasts](trace.json)

To run the example on your own computer, open the launcher named for your operating system. It uses Python 3 with NumPy installed. To use your own matching observations, run the command below from this folder. Replace the input file with one using the same fields, units and ordering as the example. The three results give predicted straight-line distances in centimetres.

```sh
python predict.py example-input.json
```

The model forecasts the distance between two positions. If the rat turned around between frames, that distance can be much shorter than the path it travelled. It gives neither a direction nor a limb position. A live forecast would also need to account for tracking, spike sorting and recording delays. The archive contains offline measurements. [Method and reproduction](METHODS.md) · [Source credit and licence](NOTICE.md)
