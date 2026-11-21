# A rat-trained forecast on a turtle’s recorded spike clusters

Can a model trained on a rat’s hippocampal and prefrontal recordings rank the next spike cluster in a turtle’s visual cortex? A turtle presents a different vertebrate lineage, a different circuit and a different task. The public example comes from a visual oddball experiment in dorsal cortex. The original authors plotted the spikes assigned to a putative single unit during repeated visual stimulation. Their figure file also supplies the other cluster labels and the times of stimulus presentation on a common clock. An extracellular cluster is a group of spikes the sorting algorithm assigns together. Its identity as one biological cell is uncertain. [Original publication](https://pubmed.ncbi.nlm.nih.gov/41296867/) · [Figure source](https://github.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/blob/b421ce0a62140a812e964cb027b97f979e98f049/plot_Fig1h.m) · [Data deposit](https://doi.org/10.5061/dryad.k98sf7mm6)

## What the model saw

The archive named 109 clusters in one recording. We restored the chronological order of the stimulus onsets and took nonoverlapping three-second windows. The first 20 windows supplied a list of 103 observed clusters. For the next 20 windows the rat-trained model started each trial with empty counters. It used the same five fitted coefficients for every cluster. It ranked the next occupied millisecond as soon as the current occupied millisecond closed. We scored a next bin only when it contained a single event. Eight trials ended early for scoring because a previously unseen cluster appeared. This selection can change the difficulty of the retained observations. The complete native roster is tested separately below. [Registered protocol](protocol.json)

## How accurate were the probabilities?

The table covers 6,978 resolved transitions. Log loss penalizes assigning a low probability to the observed cluster. Lower is better. First-choice accuracy gives partial credit for tied scores. The last two columns give each of the 99 scored target clusters equal weight, so frequently firing clusters have less influence on the summary.

| Method | Log loss | First choice correct | Equal-cluster log loss | Equal-cluster first choice |
| --- | ---: | ---: | ---: | ---: |
| Equal probabilities | 4.635 | 0.97% | 4.635 | 0.97% |
| Running counts | 4.044 | 8.03% | 4.907 | 1.72% |
| Recent activity | 4.013 | 9.46% | 5.202 | 2.37% |
| Five coefficients fitted on rat data | 3.992 | 9.48% | 4.979 | 2.32% |

Counting every scored spike equally favored the fitted model over running counts. Giving each target cluster equal weight reversed that comparison in log loss. Many spikes came from a smaller, easier-to-forecast part of the population. This one recording cannot establish accuracy for reptiles as a group. It measures an ordering in a recorded population, without measuring muscle force, behavior generation or developmental rules.

The additional analysis used all 109 cluster IDs supplied by the archive. It kept every selected trial window through its full duration, yielding 10,298 resolved transitions. The fitted model reached log loss 3.962, compared with 4.011 from running counts. The archived full roster would ordinarily be known after spike sorting. [Full selection and trial scores](results.json) · [Native-roster comparison](declared-roster-sensitivity.json)

## Reproduce the selection

Download the versioned figure file from the authors’ repository. Install NumPy and SciPy and obtain the adjacent Next Neuron Prediction scoring package. From this folder, run `python evaluate.py spikes.mat ../../next-neuron-prediction my-results.json`. Add `--declared-roster` to reproduce the supplementary check. The evaluator verifies the measurement file and scoring program against their selected SHA-256 hashes. Original project analysis code is dedicated to the public domain under CC0. The original dataset has its own CC0 dedication and authorship. [Versioned data file](https://github.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/blob/b421ce0a62140a812e964cb027b97f979e98f049/spikes.mat) · [Turtle dataset and rights](https://doi.org/10.5061/dryad.k98sf7mm6)

The original recording used a 20 kHz clock. The reader verifies each stored timestamp against that grid, recovers its integer sample index, and performs window selection and censoring on those indices. This avoids assigning an event to the wrong millisecond when a floating-point timestamp rounds slightly above an integer. [Acquisition methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12652236/)
