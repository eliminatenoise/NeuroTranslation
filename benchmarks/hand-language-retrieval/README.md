# Find a recorded hand movement from a sentence

A headset wearer loads a printer. Someone watches the video and writes down what the wearer did. Can you take that sentence, hide the video, and recover the right stretch of hand tracking?

The two fitted models in this preview rank the five measured intervals from one printer recording. Type a description. The default ridge model gives each interval a score. The attention model offers a second reading of the same measurements. The person, the printer and the room stay the same across all five choices. This recording helped train the models. Try it to see how the search works. The independent check used ten other recordings. [HoloAssist](https://holoassist.github.io/)

## Try the fitted models

Install Python 3.11 or later and the packages in `requirements.txt`. These commands work in a terminal opened in this directory.

```sh
python -m pip install -r requirements.txt
python rank.py "press the button"
python rank.py "load the paper tray" --method attention
```

Each result gives the source interval in seconds, the reference description and a similarity score. The model sees the words you supplied and the right-hand measurements from each candidate. The source description appears *after* scoring so you can see what the annotator saw. Equally scored intervals share a rank. The output also gives the number of words the training vocabulary recognized. A query with no recognized words can still produce a ranking from learned offsets or the unknown-word embedding. Its ordering carries no query-specific word meaning.

## What the held-out recordings showed

We fitted the models on 146 intervals from 24 eligible recordings in 15 recording groups. For each new sentence, we asked the fitted models to find the original interval among the other eligible intervals **from that same recording**. The independent sample contained 60 intervals in ten recordings from six other groups. A group's name comes from the release's recording prefix. The source provides no verified person identifier for this comparison. All selected recordings came from the publisher's training partition. Ten further recordings in three reserved groups stayed unopened.

| Ranker | Correct interval first | Mean reciprocal rank |
| --- | ---: | ---: |
| Uniform chance in each recording | 20.66% | 0.443 |
| Sentence length alone → hand geometry | 16.44% | 0.419 |
| Sentence → interval duration | 25.76% | 0.502 |
| Sentence → position in recording | 24.31% | 0.506 |
| Sentence → tracking availability | 24.83% | 0.463 |
| Sentence → duration, position and tracking availability | **35.56%** | **0.570** |
| Sentence → hand geometry, ridge | 23.89% | 0.514 |
| Sentence → hand geometry, attention | 23.59% | 0.486 |
| Ridge fitted with shuffled movements | 8.89% | 0.336 |
| Attention fitted with shuffled movements | 21.71% | 0.436 |

Reciprocal rank gives one point for first place, half a point for second place, a third for third, and so on. Tied scores share credit across all possible orders. We averaged descriptions within their interval, intervals within their recording, and recordings within their group. Each of the six groups then carried equal weight. The galleries contained two to eleven intervals. Four had five candidates or fewer, so putting the correct interval in the first five required no discrimination in those four.

**Timing and tracking availability recovered more intervals than either hand model.** Even the better geometry fit put the original interval first in fewer than a quarter of searches. Attention's top-rank difference from ridge was −0.30 percentage points. Its exploratory 95% paired group-bootstrap interval ran from −17.26 to +15.97 points. Neither geometry fit passed the comparison specified before training.

Language repeated too. Twenty assessment descriptions matched training wording after tokenization. Another eight had at least 80% overlap between their sets of words and a training description. Among the 32 remaining descriptions, the correct interval ranked first for 17.96% with ridge and 10.65% with attention, against 19.22% for chance within those galleries. Only six queries in two groups had distinct-wording competitors tagged with the same verb and noun. The source annotators supplied those tags. Exact and near-copy checks found no cross-partition copy of the measured phase sequences at the registered thresholds. Full per-group results, comparisons and diagnostics are in [results.json](results/results.json).

## What the headset measured

The HoloLens 2 estimated 26 joint locations on the right hand. We used its wrist and five fingertip positions. Their 15 pairwise distances describe hand shape. A sixteenth distance measures how far the wrist has moved from its first sampled position in that interval. All distances are in metres. For each interval we sampled 24 locations in time. Each sample uses the closest recorded frame inside that interval, within a tenth of a second. We kept joints only when the hand was active and the joint was valid and tracked. At least twelve samples needed eight usable distances and at least two distinct native sensor timestamps overall. [Exporter format and joint order](https://github.com/microsoft/psi/blob/master/Sources/MixedReality/HoloLensCapture/HoloLensCaptureExporter/Readme.md)

The geometry rankers received those distances. The ridge fit predicted summaries of hand shape and movement from the words. The attention fit learned a score for each sentence and sequence pairing. Both used means and scales computed on the training set. Untracked measurements became the training mean for that channel. A separate comparison tested how far the pattern of missing measurements could take a search on its own.

A hand can press several different buttons with much the same movement. The sentence can distinguish them by name even when the measured fingers cannot. Here the descriptions were written after the action. This comparison provides no test of advance instructions, intention, neural activity, muscle activity, force, left-hand motion or a new movement generated from words. [Wang and colleagues, ICCV 2023](https://arxiv.org/abs/2309.17024)

The fitted coefficients, attention weights, example gallery, study code, a compact 206-interval feature edition, acquisition indexes and frozen rules accompany the preview. [Reproduction](REPRODUCE.md) · [Data, model and code permissions](NOTICE.md)
