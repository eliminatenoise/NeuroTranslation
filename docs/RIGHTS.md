# Whose recordings these are, and what you may reuse

**What the project wrote is yours to take.** Its text and code are dedicated to the public domain under [CC0 1.0](LICENSE), as far as the project holds the rights.

**The recordings are not the project's to give.** Eleven open datasets carry every study of the numbered table, and four more carry the studies published after it and the 3D recordings. Each belongs to the people named below, under the terms named below. The repository holds fitted models and summary results derived from those recordings, and some excerpts of the recordings themselves, named below under their datasets. The credit set out here travels with all of it. Fetch a recording from its own archive. A file you open in a browser page stays under the terms it came with.

## The eleven datasets of the numbered table

The study numbers are those of [the studies page](../benchmarks/README.md).

### EEG-EMG-WristMotion Dataset, version 3

Studies 1 to 3 and 28, row 29, the wrist trial example, the browser copy of study 28's models, and the wrist-angle path of the general model's shared fit ([`models/neurotranslate-0.0/`](../models/neurotranslate-0.0/)). Recorded and shared by Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz, under CC BY 4.0.

Changed here: pointing trials were selected, the encoder angles decoded, and motion, EEG and forearm EMG features derived for the models. Study 28 publishes its three fitted models, with the scales taken from the recordings, and [`interfaces/paired-wrist-browser/`](../interfaces/paired-wrist-browser/README.md) repacks the same fitted numbers for a web browser: all of them keep this credit and the dataset's CC BY 4.0 terms.

The [wrist trial example](../interfaces/wrist-language-motion/README.md) holds one three-second trial of the recordings themselves (participant 41, run 03, block 1, trial 1), under the same licence. Changed there: the interval was selected and the two forearm channels were subtracted.

[Deposit](https://doi.org/10.6084/m9.figshare.29666735.v3) · [Descriptor paper](https://doi.org/10.1038/s41597-026-07287-z) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### KIN-MUS UJI, version 1.0

Study 4. Recorded and shared by Néstor J. Jarque-Bou, Margarita Vergara, Joaquín L. Sancho-Bru, Verónica Gracia-Ibáñez and Alba Roda-Sales, under CC BY 4.0.

Changed here: the raw forearm EMG was selected and reduced to sixteen amplitude values per channel; two models were fitted, one on the task and its timing and one with the EMG added; the differences were averaged with each person counted equally.

[Deposit](https://doi.org/10.5281/zenodo.3469380) · [Descriptor paper](https://doi.org/10.1038/s41597-019-0285-1) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### A kinematic and EMG dataset for upper limb and hand movement analysis in post-stroke and healthy subjects

Study 5. The dataset paper is by Francesca Lucchetti, Gaia Bailo, Monia Cabinio, Alberto Marzegan, Arturo Nuara, Federica Rossetto, Simona Squartecchia, Ilaria Carpinella, Maurizio Ferrarin and Tiziana Lencioni. The two participant records used, HS 01 and HS 02 (version 1), are by Francesca Lucchetti, Tiziana Lencioni and Gaia Bailo. Licence: CC BY 4.0.

Changed here: five hand-to-mouth repetitions were taken from each of the two healthy participants, with the elbow angle as stored and the EMG reduced to its amplitude over a short window.

[Dataset paper](https://doi.org/10.1038/s41597-025-06174-3) · [Record HS 01](https://doi.org/10.6084/m9.figshare.28596026.v1) · [Record HS 02](https://doi.org/10.6084/m9.figshare.28596038.v1) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### IACKD: Intention Action Conflict EEG-Hand Kinematics Dataset, version 1.0.0

Studies 6 to 8. Recorded and shared by Mengpu Cai, Rongrong Fu, Yaodong Wang, Bin Lu, Saiwei Guo and Fangyao Xu, under CC0 1.0. CC0 asks for no credit. It is given here anyway.

[OpenNeuro ds006840](https://doi.org/10.18112/openneuro.ds006840.v1.0.0) · [Descriptor paper](https://doi.org/10.1038/s41597-026-07146-x) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)

### WAY-EEG-GAL

Studies 9 and 10. Recorded and shared by Matthew D. Luciw, Ewa Jarocka and Benoni B. Edin. The source carries two notices and no single licence line: CC0 1.0 on the Figshare version-1 records, and CC BY 4.0 on the descriptor paper.

The European Commission supported the original recordings through the WAY project (FP7-ICT-288551). [The original study's acknowledgements](https://pmc.ncbi.nlm.nih.gov/articles/PMC4365902/#ack1)

Changed here: the sign of the stored grip force was reversed so that squeezing is positive, and windows of past force, motion, scalp EEG and surface EMG were taken on the stored clocks. The grip-force and contact-force readers carry fitted models and summary results derived from these recordings.

[Collection, version 2](https://doi.org/10.6084/m9.figshare.c.988376.v2) · [Descriptor paper](https://doi.org/10.1038/sdata.2014.47) · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### HYGRIP

Studies 11 to 13. Pablo Ortega, Tong Zhao and A. Aldo Faisal wrote the acquisition paper. The version-1 deposit names Aldo A. Faisal and Pablo Ortega. Licence: MIT for the deposit, CC BY 4.0 for the paper. The MIT notice stays with anything redistributed from the deposit.

Changed here: right-hand trials only, and the sensor's signed voltage forecast as it was released.

[Deposit, version 1](https://doi.org/10.6084/m9.figshare.12383639.v1) · [Deposit terms](https://api.figshare.com/v2/articles/12383639/versions/1) · [Acquisition paper](https://doi.org/10.3389/fnins.2020.00919) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Hyser: Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings, version 2.0.0

Studies 14 to 17. Contains information from the [Hyser database, PhysioNet 2.0.0](https://doi.org/10.13026/hxan-pe94), by Xinyu Jiang, Chenyun Dai, Xiangyu Liu and Jiahao Fan, made available under the [Open Data Commons Attribution License 1.0](https://opendatacommons.org/licenses/by/1-0/).

The finger readers contain models derived from the Hyser 2.0.0 Random dataset.

[Study and benchmark paper](https://doi.org/10.1109/TNSRE.2021.3082551) · [PhysioNet paper](https://doi.org/10.1038/s44360-026-00096-z)

### CEMHSEY GRASP, version 2

Studies 18 to 23. Recorded and shared by Shutian Yang, Dongxuan Li, Chen Chen and Xiangyang Zhu, under CC BY 4.0.

Changed here: one two-finger pinch task was used, with the gauge force as released, as a share of that day's hardest squeeze, and the forearm EMG reduced to amplitude features. The pinch readers ship invented weights, not weights fitted to these recordings.

[Deposit, part I](https://doi.org/10.5281/zenodo.15077957) · [Deposit, part II](https://doi.org/10.5281/zenodo.15070187) · [Acquisition paper](https://doi.org/10.1038/s41597-025-05733-y) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### LINK: Long-Term Intracortical Neural Activity and Kinematics

Study 24. By Hisham Temmar, Nina Gill, Yixuan Wang, Nicholas B. Mellon, Chang Liu, Luis Hernan Cubillos, Rio I. Parsons, Joseph T. Costello, Matteo Ceradini, Madison M. Kelberman, Matthew J. Mender, Aren I. Hite, Dylan M. Wallace, Samuel R. Nason-Tomaszewski, Matthew S. Willsey, Parag G. Patil, Anne W. Draelos and Cynthia A. Chestek.

Licence: the papers say the DANDI recordings they use are listed under CC BY 4.0. They do not name this record when they say it, so read the terms at the record itself before you reuse the data.

[DANDI 001201, version 0.251023.2336](https://dandiarchive.org/dandiset/001201/0.251023.2336)

### Reach&Grasp: a multimodal dataset of the whole upper-limb during simple and complex movements, version 1.0

Study 25. Published by IIT Dataverse, which declares CC BY 4.0. The summary file this project keeps names no authors.

Changed here: one recording was used; four invalid rows were left out, and the surface EMG was reduced to its amplitude over the trailing 40 ms.

[Dataset](https://doi.org/10.48557/L6OWMM) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Daily and Sports Activities

Study 26 and the general model's five-sensor walking fit (row 27 of the studies page). Recorded and shared by Billur Barshan and Kerem Altun through the UCI Machine Learning Repository, under CC BY 4.0.

Changed here: two walking activities were selected, and the accelerometer readings of the right-arm sensor (study 26) or of all five sensors (row 27) were cut into short histories of 16 readings, each with the reading recorded three readings (120 ms) after its last one; forecasts were fitted and their errors computed. The five-sensor folder also holds an excerpt of the recordings themselves: 16 readings, and the reading recorded 120 ms after the last of them, from each of the five sensors in one clip of one person, under the same licence.

[Dataset](https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities) · [DOI 10.24432/C5C59F](https://doi.org/10.24432/C5C59F) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Four more datasets, behind the newer studies and the 3D recordings

These carry the studies published after the numbered table (listed at the end of [the studies page](../benchmarks/README.md)) and the [3D recordings](whole-body/README.md).

### HoloAssist

Two newer studies, [finding a hand movement from a sentence](../benchmarks/hand-language-retrieval/) and [an instructor's words and a one-second wrist forecast](../benchmarks/preceding-instructions/), the [hand search](hand-search/README.md) page that runs both, and the general model's [shared fit](../models/README.md). By Xin Wang, Taein Kwon, Mahdi Rad, Bowen Pan, Ishani Chakraborty, Sean Andrist, Dan Bohus, Ashley Feniello, Bugra Tekin, Felipe Vieira Frujeri, Neel Joshi and Marc Pollefeys: *HoloAssist: an Egocentric Human Interaction Dataset for Interactive AI Assistants in the Real World*, ICCV 2023, pages 20270–20281. Released under the Community Data License Agreement – Permissive, Version 2.0, which permits use and modification, and sharing the data with the agreement supplied. It places no conditions on computational results, which include fitted models.

Changed here: hand measurements, sentences written by observers and instructors' words were selected and turned into features; models were fitted and scored. The hand search keeps five stretches of one recording, with the observers' sentences and the headset's estimates of the right hand. The agreement's text sits beside each of these and stays with them when they are shared.

[Publisher](https://holoassist.github.io/) · [Paper](https://doi.org/10.1109/ICCV51070.2023.01854) · [Agreement](../benchmarks/hand-language-retrieval/CDLA-Permissive-2.0.txt)

### KIT Motion–Language Dataset

The newer study [which recording a sentence describes](../benchmarks/text-motion-retrieval/). Created by Matthias Plappert, Christian Mandery and Tamim Asfour, from movements recorded for the KIT Whole-Body Human Motion Database, which Christian Mandery, Omer Terlemez, Martin Do, Nikolaus Vahrenkamp and Tamim Asfour described. No open licence to pass on its descriptions, its movements or models fitted to them has been established, so the folder holds only the study's numerical summaries and the facts of its split. To run the study again, fetch the release from KIT.

[Dataset and citation](https://motion-annotation.humanoids.kit.edu/dataset/) · [KIT Whole-Body Human Motion Database](https://motion-database.humanoids.kit.edu/)

### Single Day W-Track Learning, version 0.240511.0307

The newer study [on brain-cell firing and a rat's movement](../benchmarks/wtrack-neural-motion/), and the general model's [shared fit](../models/README.md). By Justin Shin and Shantanu Jadhav (2024), DANDI Archive, under CC BY 4.0. No endorsement by the authors is implied.

Changed here: one rat, one session and one running period were used. 34 whole trips were selected with their original positions and spike times and put in per-trip arrays, from which past-only inputs were built, forecasts fitted and their errors computed. The selected records, the fitted weights and the forecasts keep this credit and licence.

The shared fit learned from both HoloAssist and this dataset. Its fitted weights are released under CC BY 4.0, with credit to the model and to both datasets; [its data credits](../models/shared-motion-browser/DATA-CREDITS.md) give the full author lists and what was changed.

[Versioned dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### CMU Graphics Lab Motion Capture Database

The [3D recordings](whole-body/README.md): trials 02_06, 13_11 and 132_23. The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. Carnegie Mellon permits copying, modification and redistribution of the motion recordings, including use in commercial products, and prohibits direct resale of the data, converted data included. Those terms apply to the movement files in `docs/whole-body/data/` and to their copies inside its page.

Changed here: every fourth frame was kept, with 41 named markers, rounded to 0.1 mm for storage.

[CMU terms](http://mocap.cs.cmu.edu/) · [CMU FAQ](http://mocap.cs.cmu.edu/faqs.php)

## One more recording, behind the portable interface source

The source in [`interfaces/experimental/portable/`](../interfaces/experimental/portable/NOTICE.md) was written for one macaque reaching recording: *Nonhuman Primate Reaching with Multichannel Sensorimotor Cortex Electrophysiology*, by Joseph E. O'Doherty, Mariana M. B. Cardoso, Joseph G. Makin and Philip N. Sabes (Zenodo, version 2, 2020), reported as CC BY 4.0 at its source. No study on the studies page uses it. Nothing from that recording, and no model fitted to it, is published here.

[Zenodo record 3854034](https://zenodo.org/records/3854034) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Fonts in the papers

The four PDFs embed Noto Sans, Noto Sans Mono, Fira Math and DejaVu Sans. Their licences travel with the papers: [fonts and paper notices](../papers/current/NOTICE.md).
