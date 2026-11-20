# A quarter-second knee forecast in a second walking laboratory

The frozen NeuroTranslate knee specialist predicted the next knee angles more accurately than its ridge comparator on an independent optical recording. Its advantage over copying the previous stride was uncertain. Ten people walked on a level treadmill in Dallas. Each contributed equally to the scores below. The model had been fitted to inertial joint estimates from a separate walking study at Khalifa University. [External acquisition](https://doi.org/10.1038/s41597-021-01057-9) · [Original acquisition](https://physionet.org/content/multimodal-gait-dataset/1.0.0/) · [Published model and weights](https://github.com/eliminatenoise/NeuroTranslation/tree/12484172f3c10cdd545f71803f8658c68cca0026/models/knee-stride)

| Frozen method | Right knee MAE | Left knee MAE | Bilateral MAE |
| --- | ---: | ---: | ---: |
| Transformer correction to previous stride | 3.327° | 3.158° | 3.242° |
| Copy the previous stride | 3.236° | 3.560° | 3.398° |
| Ridge correction to previous stride | 3.501° | 3.703° | 3.602° |

| Paired difference in bilateral MAE | Mean | 95% participant bootstrap interval | Wins / ties / losses | Prespecified comparison |
| --- | ---: | ---: | ---: | --- |
| Transformer minus previous stride | −0.156° | −0.447° to +0.069° | 6 / 0 / 4 | Failed |
| Transformer minus ridge | −0.360° | −0.511° to −0.199° | 9 / 0 / 1 | Passed |
| Ridge minus previous stride | +0.203° | +0.014° to +0.384° | 1 / 0 / 9 | Failed |

A negative difference favors the first method. Each comparison needed a negative mean, a negative upper 95% bound and at least eight participant wins. The Transformer had met the advantage criterion against both controls on the original 12-person evaluation. Here it met that criterion against ridge alone. The external cohort combines a faster walking condition, another group of people and another measurement system. This comparison cannot attribute the change to any one of them. [External results and participant errors](results.json) · [Original results](https://github.com/eliminatenoise/NeuroTranslation/blob/12484172f3c10cdd545f71803f8658c68cca0026/models/knee-stride/results.json)

## Which movement was measured?

Reznick and colleagues recorded ten healthy adults aged 20–60 in Dallas using optical markers, Vicon Plug-in Gait reconstruction and a Bertec treadmill. The selected trial for each participant was level walking, with one continuous, nominal 0.8 m/s segment of about 30 seconds. The researchers report individual commands of 0.772–0.830 m/s after adjusting for leg length. Nine archived nominal command profiles corroborated 0.8 throughout the selected interval. AB10 had the authors' speed label and frame boundaries, with the command profile absent. Per-stride experimental speed fields lacked a verified units-and-row mapping for these cutoffs, so we report commanded conditions only. The original 0.5 m/s treadmill study used Xsens inertial reconstructions in a separate cohort. Personal identities cannot be cross-checked in these anonymised data. [External acquisition](https://doi.org/10.1038/s41597-021-01057-9) · [Investigator's speed table and data dictionary, pp. 2–3, 9](https://doi.org/10.6084/m9.figshare.14125814.v1) · [Original acquisition](https://physionet.org/content/multimodal-gait-dataset/1.0.0/)

The source fields RKneeAngles and LKneeAngles store right and left shank-to-thigh rotations. We took the first output component on each side, sagittal flexion positive, in degrees. That is the first reported Vicon angle around the thigh flexion axis. Xsens describes the same anatomical movement using its own ZXY frame convention. No sign, offset, weight or scaling adjustment was fitted. The optical pipeline filled small gaps, applied a 6 Hz fourth-order Butterworth filter and Woltring smoothing, and allowed marker corrections on anomalous trials. Previously filled gaps cannot all be identified from the joint outputs. Sources did not establish the time each reconstructed frame would have become available during live acquisition. Both the histories and the future references are stored optical estimates here. The recorded errors measure offline transfer. [Vicon angle order and positive direction](https://www.vicon.com/support/faqs/what-are-the-lower-body-segment-angles-from-plug-in-gait/) · [Xsens joint-angle convention](https://www.xsens.com/hubfs/User_Manual_Xsens%202025.pdf) · [Acquisition and filtering](https://doi.org/10.1038/s41597-021-01057-9)

We used the CC0 streaming release and the separately recorded left/right channels. The source provides 100 samples per second before gait-cycle normalization. Each 240-frame input was linearly sampled onto 60 Hz inside a single continuous speed interval. Cutoffs were 50 ms apart, making both each cutoff and its target 250 ms later coincide exactly with actual native frames. Interpolation used for a historical point never crossed its cutoff. Eligibility required finite, nonzero source knees across history and target, and six finite, nonzero sagittal channels across the original short availability interval. Treating a valid angle of exactly zero as unavailable can exclude a real sample. The model received only the knees. Of 5,162 candidate windows, 4,828 passed. All 334 exclusions occurred in AB08, who contributed 183 qualifying windows and the same weight as every other walker. Both knees and overlapping windows are repeated measurements within a person. The 95% intervals resample ten people 10,000 times and are unadjusted across comparisons. [Streaming release and CC0 rights](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Frozen protocol](preregistration.md) · [Clock addendum](clock-addendum.md)

| Walker | Scored cutoffs | Transformer | Previous stride | Ridge |
| --- | ---: | ---: | ---: | ---: |
| AB01 | 515 | 3.228° | 3.447° | 3.527° |
| AB02 | 516 | 3.763° | 3.983° | 3.999° |
| AB03 | 517 | 2.654° | 2.496° | 2.532° |
| AB04 | 516 | 2.341° | 2.150° | 2.535° |
| AB05 | 516 | 3.027° | 3.346° | 3.589° |
| AB06 | 516 | 2.984° | 2.859° | 3.155° |
| AB07 | 516 | 3.131° | 3.317° | 3.714° |
| AB08 | 183 | 4.882° | 6.150° | 5.688° |
| AB09 | 516 | 2.505° | 2.190° | 2.942° |
| AB10 | 517 | 3.907° | 4.045° | 4.337° |

## Reproducing the score

Download the original recording from the authors’ deposit. The authors' data release and data dictionary are CC0. The study article is CC BY 4.0. Cite Reznick, Embry, Neuman, Bolívar, Fey and Gregg (2021), and Katmah and colleagues for the original training study. The licensed file, the original algorithm, the external evaluation and both preregistration steps have separate hashes. The archived results supplied the original cohort comparison. [Data](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Collection and related documentation](https://doi.org/10.6084/m9.figshare.c.5175254) · [External study article](https://doi.org/10.1038/s41597-021-01057-9) · [Original data](https://physionet.org/content/multimodal-gait-dataset/1.0.0/)

From this directory, run the following command with Python 3.11 or later, NumPy and h5py installed. Replace the example source path with the location of the downloaded Streaming.mat file and choose a new output filename. The evaluator verifies the original archive, the selection and study design, the earlier model files and the archived stride score before computing the external scores. The archive has 2,195,168,300 bytes and SHA-256 `df8b3e31d2fe6869b95b4776a8f77639da476685b4c0ccb86c985bee3f01b531`. [Selected ranges](selection.json) · [Evaluator](evaluate.py)

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B evaluate.py /path/to/Streaming.mat reproduced.json
```

The evaluator confirmed the original direct forecasting entry point against the batched route at the first, middle and last eligible cutoff for every participant. Their greatest absolute difference was 7.11 × 10⁻¹⁵ degrees. An independent scalar lag search returned each of the same 30 periods. Changing all later native knee measurements changed the target by 123° and left each forecast unchanged. These checks establish the calculations on the stored inputs. They do not measure the optical system's own delay or its anatomical accuracy. [Machine-readable checks and slice hashes](results.json)

The study design was fixed locally before inspecting the external knee measurements. Its original SHA-256 was `f0b0b4c3ea5fe6b5491b736129aede492336b91342cb886e91e9fcd97a77392a`. The [public protocol](preregistration.md) omits two administrative sentences and has SHA-256 `a8c425b5d722a9f98b1ab77d9abf1c465fa324b13ace0aace1e870b41bc9b0f7`. The evaluator checks the distributed protocol while retaining the original provenance in the reproduced results. No entry in a public trial registry is claimed.
