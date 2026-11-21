# Vertebrate neural recordings

A turtle looking at an unexpected image, a songbird singing and a person recognizing a photograph all produce neural activity. The files preserve different parts of that activity. A turtle recording gives a timestamp and a cluster label for each detected spike. In the finch recording a threshold crossing belongs to an electrode channel. A human memory experiment supplies sorted unit labels, while scalp EEG records voltage over a much larger region. These distinctions determine which prediction a recording can test.

The [machine-readable register](datasets.json) identifies **15 public deposits** across amphibians, ray-finned fishes, birds, a non-avian turtle and mammals. Birds and turtles both belong to the reptile lineage. A deposit can contain several animals, or several files from a single animal. Each entry names the appropriate unit of comparison and links to a specific file, the release or asset identifier, the reuse terms and the original source.

| Animal and experiment | What the file preserves | Primary deposit |
| --- | --- | --- |
| Tiger salamander, retinal responses to visual stimuli | Sorted ganglion-cell spike times from recordings acquired at 10 kHz | [Dryad](https://doi.org/10.5061/dryad.1f1rc) |
| Tiger salamander, repeated natural movies | Binary activity of 93 retinal cells in 16.667 ms bins | [Dryad](https://doi.org/10.5061/dryad.4qrfj6qm8) |
| African clawed frog, responses to injected current | Membrane voltage from individual tectal neurons during current steps | [Dryad](https://doi.org/10.5061/dryad.18kk6) |
| Cane toad, awake and anesthetized recordings | One-minute extracellular voltage recordings from implanted forebrain electrodes | [Dryad](https://doi.org/10.5061/dryad.np5hqc03s) |
| Red-eared slider, visual oddball | Millisecond cluster timestamps in one example, plus separate field-potential recordings | [Dryad](https://doi.org/10.5061/dryad.k98sf7mm6) · [Authors’ spike file and timing code](https://github.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/tree/b421ce0a62140a812e964cb027b97f979e98f049) |
| Zebra finch, song production | Channel threshold crossings from the song motor nucleus RA, with song audio | [DANDI](https://dandiarchive.org/dandiset/001046/draft) |
| Pigeon, visual object recognition experiment | Stimulus responses from forebrain channels, predominantly multi-unit activity recorded under anesthesia | [Figshare](https://doi.org/10.6084/m9.figshare.30406729.v1) |
| Brown ghost knifefish, electrosensory communication | Single afferents, simultaneously recorded afferent pairs, and separate hindbrain and midbrain recordings | [Dryad](https://doi.org/10.5061/dryad.d8p66) |
| Zebrafish, temperature changes | Two-photon forebrain fluorescence image series, including a neural calcium indicator | [DANDI](https://doi.org/10.48324/dandi.000235/0.230316.1600) |
| Rat, W-track learning | Sorted hippocampal and prefrontal spike times, plus local field potentials and running position | [DANDI](https://doi.org/10.48324/dandi.000978/0.240511.0307) |
| Mouse, vision | Sorted spike times with unit quality measurements and visual-stimulus intervals | [DANDI](https://doi.org/10.48324/dandi.000021/0.251116.2246) |
| Rhesus macaque, perturbed reaches | Sorted spike times from somatosensory area 2, with arm and cursor measurements | [DANDI](https://doi.org/10.48324/dandi.000127/0.220113.0359) |
| Human, recognition memory | Sorted single-unit activity from the medial temporal lobe during image recognition | [DANDI](https://doi.org/10.48324/dandi.000004/0.220126.1852) |
| Human, natural arm movement | Cortical surface voltages and camera-derived joint positions during inpatient activity | [DANDI](https://doi.org/10.48324/dandi.000055/0.220127.0436) |
| Human, motor execution and imagery | Scalp EEG with event codes for the movement or imagery instruction | [PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/) |

## Choosing a file

For a **next-unit forecast**, start with an experiment that recorded several units at the same time and preserved their event times and local labels. The Area 2 training file has 65 unit rows and 1,017,465 timestamps. In the turtle example, 347,291 timestamps carry 109 distinct cluster labels. The experimenters sorted the 200 stimulus onsets by condition for plotting. An analysis of time order must recover chronology from the onset values. Cluster labels still need isolation checks, and repeated sightings of the same movie frame need their own split when testing generalization to new visual content. [Macaque file](https://api.dandiarchive.org/api/assets/ded26b6c-418d-43f5-8a37-dfd072c2dbd4/) · [Turtle raster code](https://github.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/blob/b421ce0a62140a812e964cb027b97f979e98f049/plot_Fig1h.m)

For a **calcium or field forecast**, keep the recorded quantity and its own sampling clock. One zebrafish acquisition series has 1,182 images of 512 × 512 pixels. A model can predict a fluorescence response to temperature after establishing the indicator channel and identifying the cells. A scalp recording records an entirely different quantity. Its EDF header identifies 64 EEG electrodes plus an annotation channel. For the motor data, the run determines whether a cue refers to an executed or an imagined movement. [Zebrafish file](https://api.dandiarchive.org/api/assets/141d29b1-d651-4d10-8fdc-770f9485610c/) · [EEG protocol](https://physionet.org/content/eegmmidb/1.0.0/)

For **generalization to a new animal**, keep each animal on one side of the split. A single finch supplies every file in the song benchmark, including the three labels its archive calls subjects. Holding out a day asks whether the model carries across recording days in that bird. Holding out a species requires independent recordings in the new species, a common observable target and an explicit account of the new task, recording site and instrument. [Finch release notes](https://api.dandiarchive.org/api/dandisets/001046/versions/draft/info/)

## Reading the evidence

Open `datasets.json` and choose a row by `id`. Its `source.asset` gives the filename, byte size and direct download. Where a public mirror was checked, the register gives the matching archive checksum. Each `evidence` entry says whether the check reached the catalogue listing, ZIP member directory, or recording file itself. A header or shape confirms file structure. The separate `model_evidence` entry identifies previously evaluated tasks where known. All proposed tasks elsewhere in this register require their own performance tests.

The catalogue distributes links and file descriptions. Each original deposit specifies the terms for reusing its recordings. Human entries point to the providers’ released material. No human waveform samples are included here.

## Where the spike forecast was tested

The [two-rat study](../next-neuron-prediction/) fitted five coefficients on earlier trips from one animal. Separate evaluations kept those coefficients fixed for [turtle dorsal cortex](turtle/) and [salamander retina](amphibian/). Each unit label belongs to its recording. The test scores cover detected events during the stated trials and visual stimuli. [Browse the recordings and results](https://eliminatenoise.github.io/NeuroTranslation/vertebrate-neural-data/) · [Optional fly and worm comparisons](../../docs/when-fly-and-worm-data-help.md).
