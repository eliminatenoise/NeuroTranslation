# Recording and model

Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller published the recording. Chowdhury collected and processed it in Miller’s laboratory. The example contains 20 readings from a training trial recorded in macaque C on 7 September 2017. A camera followed one mark on the hand and another near the elbow. The robot measured where the handle went.

Both browser models learned from the same 1,533 parts of 72 reaching trials. One model reads the recorded positions. The other subtracts the last position in each of the eight columns from every reading in that column. Each model has its own fitted weights and scales. A fitted linear calculation supplies a first estimate. The transformer then samples a correction at one forecast time and uses it when drawing the next one. The result is 32 possible paths for the two marks at 20, 50, 70 and 100 milliseconds. The display also shows the path each mark would follow at its recent speed and direction.

The browser runs one training seed, 1117, for each model. In the two-seed comparison, the relative-position models scored better than their recorded-position counterparts on a different macaque’s reaching session. The relative autoregressive model scored best across sets of proposed paths. A relative linear model gave the closest single path. The evidence comes from 266 trials in one held-out recording. [Published comparison](https://eliminatenoise.github.io/NeuroTranslation/joint-alpha/shared-tasks/trajectory/reach/density/second-day/different-animal/position-frame/)

Each model takes eight position readings at each time. Its 37 brain-signal fields are masked. In this archive the camera estimates were smoothed and aligned, and the handle data were filtered in both directions. A reading can depend on nearby later samples. The forecast times follow the processed recording.

The source offers the readings under CC0. The browser models, interface and this package are available under the same terms. [CC0 1.0](CC0-1.0.txt) · [Recording archive](https://doi.org/10.5061/dryad.nk98sf7q7) · [Original research article](https://doi.org/10.7554/eLife.48198)
