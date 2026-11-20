# How much turning moment will the knee carry?

A knee can keep bending while its muscles act to slow the bend. Knowing its angle tells us where it is. The **turning moment** describes the net tendency of forces to turn it about the joint. Here a positive moment acts towards flexion. A negative value acts towards extension. The laboratory estimated this quantity from optical body motion and external forces, then divided it by each walker’s mass. The result is expressed in newton-metres per kilogram (N·m/kg).

Give NeuroTranslate four seconds of walking, with six angle readings at every frame. It estimates the right and left knee moments 25 stored frames later, a quarter-second on the file’s 100 Hz clock. The model gets the angle history only. [Try the model](https://eliminatenoise.github.io/NeuroTranslation/knee-moment/) · [Original dataset](https://doi.org/10.6084/m9.figshare.14558181.v1)

## Does training help?

Seven people supplied 3,559 examples to fit the model. Three other people supplied 1,207 forecasts for evaluation at a nominal treadmill speed of 0.8 m/s. Each person counts equally, then each knee equally. The turning moments for these three people were first examined after fitting. Their angle recordings had been used in the earlier knee-angle comparison.

| What reads the past angles? | Mean absolute error (N·m/kg) |
| --- | ---: |
| Predict the average turning moment from the training group | 0.14510 |
| A linear fit to joint motion and stride timing | 0.09761 |
| Match the motion to the other walkers’ steps | 0.09373 |
| Add patterns from the shared NeuroTranslate encoder, keeping its weights fixed | 0.10190 |
| Use the same encoder after scrambling its weights once | 0.10349 |
| Train the encoder to correct the linear fit for this task | **0.08874** |

The task-trained model had the lowest average error across the angle-only methods. Its advantage varied by walker. It beat the linear fit for two of the three and the training-walker match for just one. Neither the task-trained model nor the shared encoder met its requirement for a consistent advantage.

| Walker | Eligible cutoffs | Linear fit | Training-walker match | Task-trained model |
| --- | ---: | ---: | ---: | ---: |
| AB08 | 183 | 0.13624 | **0.09669** | 0.11020 |
| AB09 | 517 | **0.07592** | 0.07710 | 0.08043 |
| AB10 | 507 | 0.08069 | 0.10739 | **0.07561** |

Suppose you also had earlier *moments* from the same walker. On the 1,187 cutoffs that supplied both past-moment controls, copying the moment from a similar part of the preceding stride scored **0.06785 N·m/kg**. The task-trained angle-only model scored **0.08884** on those same cutoffs, while carrying the current moment forward scored **0.21896**. The earlier mechanical measurement adds information that the angle-only model has to infer. [All scores, sides, sample exclusions and paired differences](results.json)

## What was measured?

Reznick and colleagues recorded optical marker movement and ground forces. Their software used inverse dynamics to estimate the combined turning effect around each knee. A single knee moment cannot tell us which muscle produced it or what force acted inside the joint. Both the inputs and the targets are laboratory reconstructions. This offline comparison does not establish live latency. [Acquisition paper](https://doi.org/10.1038/s41597-021-01057-9) · [Source fields and units](SOURCE.md)

The methods searched the last four seconds for a past stride that resembled the most recent second, then read the earlier angles at the matching phase. The linear fit uses that match, recent angles and summaries of four successive quarter-seconds. The frozen model also uses the time patterns the original movement encoder extracts from those four summaries. The task-trained model starts from the original encoder, then learns how to correct the linear estimate. The earlier movement tasks keep their fitted parameters. [Method fixed before testing](METHOD.md)

## Run or reproduce

From the parent `neurotranslate-0.0` folder, run `python predict.py load/example.json` with Python 3 and NumPy. The example is invented. Set `mode` to `mean`, `ridge`, `shared`, `scrambled` or `trained`. The input comprises 400 consecutive integer frame numbers and six angles per frame in right knee, left knee, right hip, left hip, right ankle, left ankle order. The output contains two signed estimates in right/left order. Zero and nonfinite input values are excluded under this dataset’s gap rule. A genuine zero crossing could be excluded too.

To reproduce the fits, use Python 3.11+, NumPy, h5py and CPU PyTorch. Download the source `Streaming.mat` and the previous shared checkpoint. The script verifies their hashes. Under the model folder run:

```sh
python load/study.py fit Streaming.mat parent.npz rebuilt.npz
python load/study.py score Streaming.mat rebuilt.npz rebuilt-results.json
```

[Exact parent checkpoint](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/c30623cd13a3a4245c6abc3fe22f0e2820d941c5/models/neurotranslate-0.0/movement-weights.npz) · [Data, authors and reuse terms](SOURCE.md) · [Terms carried by the shared checkpoint](../NOTICE.md)
