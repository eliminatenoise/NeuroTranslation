# Can a model that forecasts distance also forecast a wrist angle?

A person steers a cursor by bending their right wrist up or down and tilting it from side to side. Two encoders on the pointing device measure those angles. Given the last half-second of wrist motion, where will it be a quarter-second later? Do electrodes on the forearm or scalp help?

The same computer model already forecasts the straight-line displacement of a human wrist or a tracked rat. We kept the part that reads changes over time and taught it to accept the pointing recordings and return two angles in degrees. The original wrist and rat settings still return a single straight-line distance in centimetres. The three experiments have different subjects, instruments and targets. They share model weights. [Frozen study plan](protocol.json)

## What if we correct the forecast?

First forecast the wrist angles from motion alone. Then use the forearm recordings to correct the shared model’s estimate. Error fell from 4.503° to 4.054°. A matched correction using only wrist motion scored 4.175°. The earlier wrist-specific convolutional network with its own forearm correction still led at 3.549°. The comparison covered the same six previously studied people. Try the fitted correction with `python predict.py forearm/example.json`. [How the forearm correction was tested](forearm/README.md) · [Scores and participant sensitivity](forearm/results.json)

## What the six people showed

We fitted a new input and output for each set of measurements. In turn, five people supplied the fitting examples and the sixth supplied every test example. Each person counts equally in the error below. A smaller error means a closer forecast.

| What the wrist model gets | Earlier distance-trained weights | One set of random weights |
| --- | ---: | ---: |
| Wrist angles and time since the cue | 4.503° | 4.268° |
| Wrist angles, cue and forearm EMG | 4.291° | 4.282° |
| Wrist angles, cue, forearm EMG and scalp EEG | 4.491° | 4.391° |

Adding both electrical recordings changed the earlier model’s error by just **−0.012°**. Three people improved. When we left one person at a time out of the summary, the difference ranged from −0.087° to +0.069°. The forearm alone had more to offer. Adding it reduced error by 0.212° and helped five of the six people. Adding the scalp channels to that fit raised error by 0.200° and hurt all six. [Errors by axis and paired comparisons](results.json)

Now keep the wrist history fixed and give the fitted model forearm measurements from a different trial at the same point after the cue. Its forecast moved by 2.723° on average in the root-mean-square sense. Its error against the real wrist rose by 0.815°. Swapping the scalp signal in the full model moved its forecast by 1.278° and raised error by 0.096°. Both streams affected the answer. Each could carry movement or contact artifacts along with electrical activity. This experiment cannot identify which component helped. [Signal-swap results](results.json)

The closest forecasts on these same rows came from an earlier wrist-specific convolutional network. Its motion forecast scored **3.618°**, falling to **3.549°** with a forearm-based correction. Repeating the last wrist angles scored 7.216°. The earlier models had different training procedures. The matched random control in the table had the same training opportunity as the distance-trained model in each row and beat it in all three comparisons. One random initialization and six previously studied people give us no evidence here that learning the two distance tasks improved the angle forecast. [Prior wrist model and fit](https://github.com/eliminatenoise/NeuroTranslation/tree/0ff78bbbd6723e49a72eeb29d93e8765079a2d40/benchmarks/wrist-forearm-correction)

## Run the models

Open the launcher for Windows, macOS or Linux to read the results offline. With Python 3 and NumPy installed, these two commands use the same packaged weights and run on a CPU. Both examples have invented inputs.

```sh
python predict.py angular-example.json
python predict.py spatial-example.json
```

The wrist-angle example should give 7.464° extension and 0.098° of tilt towards the thumb. The spatial examples should give 0.524 cm for the human wrist and 1.010 cm for the rat. To enter your own admitted measurements, follow the channel order and clock rules. [Input and reproduction guide](REPRODUCE.md) · [Sample angular input](angular-example.json) · [NumPy reader](predict.py)

## Where the numbers come from

Three sources contributed separate recordings. Human optical tracking supplied three-dimensional wrist positions for the distance task. A camera supplied two-dimensional rat positions for its distance task. The human pointing study supplied 1,879 usable trials across six people, with the two wrist encoders, four pairs of forearm electrodes and eight scalp electrodes all on the same recording clock. The old spatial predictions stayed numerically identical on the 583 human and 106 rat test windows checked. The angular model has one shared temporal block and separately fitted inputs and outputs. [Data sources and permissions](NOTICE.md)

The wrist recording stores 512 rows each second. A nominal 250-ms forecast spans 128 rows. The encoders refresh at about 100 Hz, so successive stored rows can repeat an angle. Physical acquisition delay is unknown. Six overlapping predictions per trial yield 11,274 rows. Each trial had to have all six eligible windows. An online system would have less information about which future observations will be usable. All six people previously contributed to method development. The original six reserved for independent confirmation and the separate three previously explored people stayed outside this extension. [Window construction and eligibility](wrist-source/README.md)
