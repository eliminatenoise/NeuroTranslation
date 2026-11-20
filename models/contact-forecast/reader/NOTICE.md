# Data, fits and reuse

Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller published the original macaque recordings and experimental analysis. This reader uses animal C’s active/passive sessions of 12 and 13 September 2017 from the CC0 Dryad deposit. The count-forecast study and its fitted models are a new analysis. [Dryad data](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original paper](https://doi.org/10.7554/eLife.48198) · [Study report](https://eliminatenoise.github.io/NeuroTranslation/papers/contact-forecast/)

| Source member under reaching_experiments | SHA-256 |
| --- | --- |
| C_20170912_COactpas_TD.mat | a391516945a67aff89039f33c0829a1c5423d859ce79baaaca962985916996af |
| C_20170913_COactpas_TD.mat | 4b81469ed6ef2460d5f07aaf26fe0580d213fd86e0f6a08b0e280292fbef2fe7 |

The 26 columns follow the shared contact numbers with sort code zero in the two source guides. Each output sums that contact’s exported events in source rows k through k+9, on the released 10-ms sampling grid. The input covers k−20 through k−1. Source row numbers start at one. The display lists electrodes in numeric order. Their coordinates and the identities of the cells contributing on successive days are unavailable here.

Robot encoder positions are planar centimetres. The five consecutive four-sample intervals use the final position and last-minus-first position change in X and Y, totals of earlier counts at all 26 contacts, and previously visible task events and their elapsed times. A cue stamped exactly at the input edge is still hidden. The source encoder processing includes offline filtering. A go cue marks the task instruction to move. Actual movement onset may occur later.

For each date and phase the reader includes every retained offset from the first eligible original and the first original with an earlier eligible movement donor. An original may satisfy both rules. The recorded examples use all retained offsets and preserve missing donors. The September 12 validation block contains pre-target pushes only. September 13 original 1 was excluded after source inspection. No example was selected on forecast error. The phase-level results use the complete matching group of trials named in the interface.

weights.js contains the full frozen parameter sets and first-day feature scaling. predict.js evaluates them locally and rebuilds model inputs from the selected history. Expected counts use a softplus function with a 0.000001 floor added for the Transformer and an exponential link for the regression. Their forecasts can be fractional. The chart’s recorded counts are integer totals from the dataset. cases.js contains selected source histories, outcomes, earlier-trial movement and first-day per-contact means. evidence.js holds the group summaries. SHA256SUMS lists the hashes of the distributed files.

Original reader code and derived materials follow the repository’s CC0 1.0 dedication. The original dataset also uses CC0 1.0. [License](LICENSE)
