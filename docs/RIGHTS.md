# Whose recordings these are, and what you may reuse

**What the project wrote is yours to take.** Its text and code are dedicated to the public domain under [CC0 1.0](LICENSE), as far as the project holds the rights.

**The recordings are not the project's to give.** Eleven open datasets carry every study of the numbered table, and seven more carry the studies published after it and the 3D recordings. Each belongs to the people named below, under the terms named below. The repository holds fitted models and summary results derived from those recordings, and some excerpts of the recordings themselves, named below under their datasets. The credit set out here travels with all of it. Fetch a recording from its own archive. A file you open in a browser page stays under the terms it came with.

## The eleven datasets of the numbered table

The study numbers are those of [the studies page](../benchmarks/README.md).

### EEG-EMG-WristMotion Dataset, version 3

Studies 1 to 3 and 28, row 29, the wrist trial example, the browser copy of study 28's models, and the wrist-angle task of the general model's shared fit ([`models/neurotranslate-0.0/`](../models/neurotranslate-0.0/)), with its browser copy ([`models/neurotranslate-browser/`](../models/neurotranslate-browser/)), the [page](shared-motion/README.md) that runs it and its forearm correction; and row 29's model, refitted on all six people ([`models/wrist-specialist/`](../models/wrist-specialist/)). Recorded and shared by Jorge German Perez Blanco and Javier Mauricio Anteliz Ortiz, under CC BY 4.0.

Changed here: pointing trials were selected, the encoder angles decoded, and motion, EEG and forearm EMG features derived for the models. Study 28 publishes its three fitted models, with the scales taken from the recordings, and [`interfaces/paired-wrist-browser/`](../interfaces/paired-wrist-browser/README.md) repacks the same fitted numbers for a web browser, as `models/neurotranslate-browser/` does for the shared fit's wrist-angle task. The shared fit's forearm correction is fitted on row 29's six people, and `models/wrist-specialist/` reuses study 1's fitted motion network with a correction fitted on the same six: all of them keep this credit and the dataset's CC BY 4.0 terms.

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

Licence: not yet confirmed. The papers' notice lists it as to be confirmed at the source, so read the terms at the record itself before you reuse the data. The study's aggregate results are published with the papers ([`link-macaque.json`](../papers/current/results/link-macaque.json)); nothing from the recordings themselves is.

[DANDI 001201, version 0.251023.2336](https://dandiarchive.org/dandiset/001201/0.251023.2336)

### Reach&Grasp: a multimodal dataset of the whole upper-limb during simple and complex movements, version 1.0

Study 25. Published by IIT Dataverse, which declares CC BY 4.0. The summary file this project keeps names no authors.

Changed here: one recording was used; four invalid rows were left out, and the surface EMG was reduced to its amplitude over the trailing 40 ms.

[Dataset](https://doi.org/10.48557/L6OWMM) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Daily and Sports Activities

Study 26 and the general model's five-sensor walking fit (row 27 of the studies page). Recorded and shared by Billur Barshan and Kerem Altun through the UCI Machine Learning Repository, under CC BY 4.0.

Changed here: two walking activities were selected, and the accelerometer readings of the right-arm sensor (study 26) or of all five sensors (row 27) were cut into short histories of 16 readings, each with the reading recorded three readings (120 ms) after its last one; forecasts were fitted and their errors computed. The five-sensor folder also holds an excerpt of the recordings themselves: 16 readings, and the reading recorded 120 ms after the last of them, from each of the five sensors in one clip of one person, under the same licence.

[Dataset](https://archive.ics.uci.edu/dataset/256/daily+and+sports+activities) · [DOI 10.24432/C5C59F](https://doi.org/10.24432/C5C59F) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Seven more datasets, behind the newer studies and the 3D recordings

These carry the studies published after the numbered table (listed at the end of [the studies page](../benchmarks/README.md)) and the [3D recordings](whole-body/README.md).

### HoloAssist

Two newer studies, [finding a hand movement from a sentence](../benchmarks/hand-language-retrieval/) and [an instructor's words and a one-second wrist forecast](../benchmarks/preceding-instructions/), the [hand search](hand-search/README.md) page that runs both, and the general model's [shared fit](../models/README.md), with its two browser copies and its [page](shared-motion/README.md). By Xin Wang, Taein Kwon, Mahdi Rad, Bowen Pan, Ishani Chakraborty, Sean Andrist, Dan Bohus, Ashley Feniello, Bugra Tekin, Felipe Vieira Frujeri, Neel Joshi and Marc Pollefeys: *HoloAssist: an Egocentric Human Interaction Dataset for Interactive AI Assistants in the Real World*, ICCV 2023, pages 20270–20281. Released under the Community Data License Agreement – Permissive, Version 2.0, which permits use and modification, and sharing the data with the agreement supplied. It places no conditions on computational results, which include fitted models.

Changed here: hand measurements, sentences written by observers and instructors' words were selected and turned into features; models were fitted and scored. The hand search keeps five stretches of one recording, with the observers' sentences and the headset's estimates of the right hand. The agreement's text sits beside each of these and stays with them when they are shared.

[Publisher](https://holoassist.github.io/) · [Paper](https://doi.org/10.1109/ICCV51070.2023.01854) · [Agreement](../benchmarks/hand-language-retrieval/CDLA-Permissive-2.0.txt)

### KIT Motion–Language Dataset

The newer study [which recording a sentence describes](../benchmarks/text-motion-retrieval/). Created by Matthias Plappert, Christian Mandery and Tamim Asfour, from movements recorded for the KIT Whole-Body Human Motion Database, which Christian Mandery, Omer Terlemez, Martin Do, Nikolaus Vahrenkamp and Tamim Asfour described. No open licence to pass on its descriptions, its movements or models fitted to them has been established, so the folder holds only the study's numerical summaries and the facts of its split. To run the study again, fetch the release from KIT.

[Dataset and citation](https://motion-annotation.humanoids.kit.edu/dataset/) · [KIT Whole-Body Human Motion Database](https://motion-database.humanoids.kit.edu/)

### Single Day W-Track Learning, version 0.240511.0307

The newer study [on brain-cell firing and a rat's movement](../benchmarks/wtrack-neural-motion/), and the general model's [shared fit](../models/README.md). By Justin Shin and Shantanu Jadhav (2024), DANDI Archive, under CC BY 4.0. No endorsement by the authors is implied.

Changed here: one rat, one session and one running period were used. 34 whole trips were selected with their original positions and spike times and put in per-trip arrays, from which past-only inputs were built, forecasts fitted and their errors computed. The selected records, the fitted weights and the forecasts keep this credit and licence.

The separate three-rat forecast used sixteen annotated trips from each of six rats. It groups spikes by brain region, pairs their timing with camera observations, and fits or tests models on different animals. Its data excerpts, results and fitted coefficients retain Shin and Jadhav’s CC BY 4.0 attribution, including the recorded trip in the browser and the offline ZIP. [Changes and source credit](../models/population-motion/NOTICE.md)

The shared fit learned from both HoloAssist and this dataset. Its fitted weights are released under CC BY 4.0, with credit to the model and to both datasets; [its data credits](../models/shared-motion-browser/DATA-CREDITS.md) give the full author lists and what was changed. Its two browser copies, [`models/shared-motion-browser/`](../models/shared-motion-browser/) and [`models/neurotranslate-browser/`](../models/neurotranslate-browser/), hold its fitted numbers for a web browser and carry the same credits, with the agreement text of HoloAssist beside them.

[Versioned dataset](https://doi.org/10.48324/dandi.000978/0.240511.0307) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Treadmill muscle and joint-angle recordings

Katmah and colleagues released these recordings through PhysioNet under CC BY 4.0. The 15-frame knee forecast derives weights and aggregate errors from six angle channels at 0.5 m/s. The four-second knee forecasts (the corrections trained for the knees, and the general model's knee task) use the two knee angles and publish derived weights and errors with the same attribution ([their terms](../models/knee-stride/RIGHTS.md)). The knee viewers open with invented values. The separate rhythm reader presents frequencies derived from 12 surface muscle channels and two reconstructed knee angles. Its reported peak rates and fitted coefficients retain CC BY 4.0 attribution. [Rhythm study and reuse terms](../models/gait-rhythm/README.md#sources-and-reuse) Obtain any recorded trial directly from the study. [Full credit and reuse terms](../models/knee-motion/RIGHTS.md) · [Original dataset](https://doi.org/10.13026/r0ea-7161)

### CMU Graphics Lab Motion Capture Database

The [3D recordings](whole-body/README.md): trials 02_06, 13_11 and 132_23. The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. Carnegie Mellon permits copying, modification and redistribution of the motion recordings, including use in commercial products, and prohibits direct resale of the data, converted data included. Those terms apply to the movement files in `docs/whole-body/data/` and to their copies inside its page.

Changed here: every fourth frame was kept, with 41 named markers, rounded to 0.1 mm for storage.

The walk/run model was fitted to 31 CMU recordings. Its viewer includes two measured training excerpts, a walk from trial 07_01 and a run from 09_01. Each keeps every third frame from the selected interval and uses 18 surface landmarks. CMU’s terms apply to these excerpts, including copies inside the page and offline ZIP. [Model and data credits](../models/word-motion/RIGHTS.md)

The stride continuation viewer also carries a short walk and run excerpt. It samples the source at 20 Hz and overlays measured and predicted marker positions. CMU’s terms, including the restriction on direct resale, cover the recorded portions in both the viewer and the standalone package. [Stride data credits](../models/stride-continuation/RIGHTS.md)

[CMU terms](http://mocap.cs.cmu.edu/) · [CMU FAQ](http://mocap.cs.cmu.edu/faqs.php)

### A library of human electrocorticographic data and analyses: the finger-flexion recordings

Kai Joshua Miller deposited *A library of human electrocorticographic data and analyses* in the Stanford Digital Repository; Miller and colleagues reported the finger experiment in *Human Motor Cortical Activity Is Selectively Phase-Entrained on Underlying Rhythms* (2012). The recordings are of electrical activity picked up by electrodes laid on the surface of the brain, beside a glove's readings of five fingers. Stanford's catalogue licenses the library under CC BY-SA 4.0: credit it, say what was changed, and share what is made from it under the same or a compatible licence. Its use statement also asks that the people recorded be protected from identification.

Changed here, in both studies that use it: only the first 362 seconds of one person's recording were used; band power of the brain signal and the glove and screen-cue histories were derived from them; forecasting models were fitted and their errors published as averages. The fitted weights, the results and the example worked with those weights are under CC BY-SA 4.0; the project's own code is CC0. The recordings stay with Stanford. The archive asks that an ethics statement go with publications that use the data: it is in the study's rights file. [Stanford Digital Repository](https://purl.stanford.edu/zk881ps0522) · [Library descriptor](https://doi.org/10.1038/s41562-019-0678-3) · [Original publication](https://doi.org/10.1371/journal.pcbi.1002655) · [Terms, credit and the ethics statement](../models/cortical-glove/RIGHTS.md) · [The same for the study of how much each finger moves](../models/finger-motion/RIGHTS.md)

### Treadmill walking recorded with optical markers (Reznick and colleagues)

E. Reznick, K. Embry, R. Neuman, E. Bolívar, N. Fey and R. Gregg recorded ten adults walking on a treadmill, tracked by cameras following markers on the body. The streaming release used here, with its data dictionary, is under CC0 1.0; the article that describes the recordings is under CC BY 4.0. Changed here: level walking at a nominal 0.8 m/s was selected and the stored knee angles were compared with the forecasts of the four-second knee model, unchanged. Only scores are published. [Data and licence](https://doi.org/10.6084/m9.figshare.14558181.v1) · [How they were recorded](https://doi.org/10.1038/s41597-021-01057-9) · [The test, its scores and its credits](../models/knee-stride/external-optical/)

## One more recording, behind the portable interface source

The source in [`interfaces/experimental/portable/`](../interfaces/experimental/portable/NOTICE.md) was written for one macaque reaching recording: *Nonhuman Primate Reaching with Multichannel Sensorimotor Cortex Electrophysiology*, by Joseph E. O'Doherty, Mariana M. B. Cardoso, Joseph G. Makin and Philip N. Sabes (Zenodo, version 2, 2020), reported as CC BY 4.0 at its source (the papers' notice still lists its licence as to be confirmed). No study on the studies page uses it. The NeuroTranslation paper's earlier studies (its section 4.8) used two recording days of it, and their aggregate scores are published with the papers ([`earlier-decoding.json`](../papers/current/results/earlier-decoding.json)). Nothing from that recording, and no model fitted to it, is published here.

[Zenodo record 3854034](https://zenodo.org/records/3854034) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Three more recordings and three simulators, behind the papers' earlier studies

The NeuroTranslation paper's earlier studies, and the two simulated hands of the Brain2Body paper, used these as well. No study on the studies page uses them, and nothing from them is published here except aggregate scores, in [the papers' result files](../papers/current/results/). The papers' notice gives each with what it was used for: [papers/current/NOTICE.md](../papers/current/NOTICE.md).

- *Attempted finger movements recorded from two participants* (Finger_RL), by Charles Guan, Tyson Aflalo, Kelly Kadlec and Jorge Gamez. [DANDI 000252, version 0.230408.2207](https://doi.org/10.48324/dandi.000252/0.230408.2207). Licence to be confirmed at the source.
- Macaque reach-to-grasp recordings with muscle signals, from the FALCON benchmark, by Brianna M. Karpowicz, Joel Ye and colleagues. DANDI 000941; [benchmark paper](https://doi.org/10.52202/079017-2439). Licence to be confirmed at the source.
- Touch-area (area 2) recordings with whole-arm movement, by Raeed H. Chowdhury, Joshua I. Glaser and Lee E. Miller. DANDI 000127; [paper](https://doi.org/10.7554/eLife.48198). Licence to be confirmed at the source.
- MuJoCo, the physics engine, by Emanuel Todorov, Tom Erez and Yuval Tassa ([paper](https://doi.org/10.1109/IROS.2012.6386109)); MyoSuite and MyoSim, the muscle-driven hand and arm models, by Vittorio Caggiano, Huawei Wang, Guillaume Durandau, Massimo Sartori and Vikash Kumar ([MyoSuite paper](https://proceedings.mlr.press/v168/caggiano22a.html), [MyoSim 0.2.3](https://github.com/MyoHub/myo_sim)); OpenSim, by Ajay Seth and colleagues ([paper](https://doi.org/10.1371/journal.pcbi.1006223)), with limblab's macaque arm model ([MIT](https://github.com/limblab/monkeyArmModel)). The licences of MuJoCo, MyoSuite, MyoSim and OpenSim are still to be confirmed at their sources.

## Fonts in the papers

The four PDFs embed Noto Sans and Noto Sans Mono, and the two NeuroTranslation editions Fira Math as well, all under the SIL Open Font License 1.1. The licence texts travel with the papers: [credits and font licences](../papers/current/NOTICE.md). The seven font files are in the papers' source download.

## Calibrated cortical transfer and knee turning moments

The five-person model groups contacts from the Stanford FingerFlex release by the source's anatomical labels. The source-derived model weights and comparative results carry CC BY-SA 4.0. The archive's required ethics statement appears in the model methods, the browser companion and the finger-cue research note. [Full attribution and licences](../models/finger-transfer/RIGHTS.md)

The Reznick optical kinematics and inverse-dynamics estimates used by the knee-moment study are CC0. The older shared checkpoint keeps its original source terms; training an additional readout does not change the original contributions. [Authors, source fields and units](../models/neurotranslate-0.0/load/SOURCE.md) · [Shared checkpoint licences](../models/neurotranslate-0.0/NOTICE.md)

### Overground walking on two force plates

Florent Moissenet and Céline Schreiber released the version 8 walking recordings under CC BY 4.0. NeuroTranslation selected slow overground trials with documented contacts, formed histories of marker positions and right-leg muscle voltage, and fitted and assessed predictors of the subsequent plate readings. Source-derived weights and results retain the applicable attribution conditions. The shared model also keeps the terms of its earlier training sources. [Dataset authors’ licence file](walking-force/DATA-LICENCE.txt) · [Dataset and version](https://doi.org/10.6084/m9.figshare.7734767.v8) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Study article](https://doi.org/10.1038/s41597-019-0124-4) · [Shared model credits](../models/neurotranslate-0.0/NOTICE.md)

The authors’ MATLAB exporter writes a GPL-3.0-or-later software notice into the original C3D metadata. The optional ezc3d and python-c3d libraries have MIT licences and can be installed separately to check decoded recordings. The downloads contain independently written readers, new model code and invented inputs. The project dedicates its own contributions to the extent of its rights under CC0. [Export code and notice](https://github.com/fmoissenet/CGA_Rehazenter_Toolbox/blob/e35dc90c1acd24da134897fd1b4241152cff6005/exportNormalisationValues.m) · [ezc3d](https://github.com/pyomeca/ezc3d) · [python-c3d](https://github.com/EmbodiedCognition/py-c3d) · [Walking study credits](walking-force/NOTICE.md)
