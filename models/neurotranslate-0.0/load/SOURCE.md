# What the knee moment measures

Bend a knee and a camera can follow the leg. Working out how hard the leg turns at the knee takes another measurement. In this walking study, ten cameras tracked markers on the body while force plates beneath the treadmill belts recorded the load on the ground. The investigators combined those measurements with a model of the leg to estimate the net turning effect at each knee. This *internal knee moment* includes the combined effect of tissues acting across the joint. It tells us neither an individual muscle’s force nor the force between the joint surfaces. [Reznick and colleagues, acquisition and inverse dynamics](https://doi.org/10.1038/s41597-021-01057-9)

Each target has two numbers, right knee first and left knee second. Each is a sagittal-plane moment around the flexion–extension axis, in newton-metres per kilogram of body mass. A positive value acts toward bending the knee and a negative value toward straightening it. The leg can be straightening while a flexion moment resists that movement. The release already incorporates body mass and applies the authors’ internal-moment convention. Take the first component of each archived knee moment without changing its sign or dividing by weight. [Acquisition methods and Table 2](https://doi.org/10.1038/s41597-021-01057-9) · [Dataset dictionary, pp. 2–3](https://doi.org/10.6084/m9.figshare.14125814.v1) · [Vicon segment axes](https://vicon-help.atlassian.net/wiki/spaces/Nexus216/pages/11602609/Plug-in%2BGait%2Blower%2Bbody%2Bforces%2Band%2Bmoments)

## Which quarter of a second?

The input and target share a clock. If the last optical angle in the input is frame 500, ask for the knee moments at frame 525. Both series contain 100 frames per second. Use only angles at or before frame 500 and take the two moment values from frame 525. There is no target average, delay correction, force-plate resampling or interpolation at the endpoint. The source optical trajectories underwent gap filling, filtering and smoothing. Frame numbers establish a quarter of a second in the archived movement. The processing delay during live capture is unknown. [Acquisition methods and Table 2](https://doi.org/10.1038/s41597-021-01057-9)

Ten adults each contributed one continuous interval of level treadmill walking at a nominal 0.8 m/s. The researchers adjusted the actual commands for leg length. Their event records label the interval `s0x8` in the `Tread/i0` trial. The selection uses the interior of each interval, from the first native event bound plus one up to, and excluding, the second bound minus one in zero-based Python indexing. Nine archived nominal command traces agree throughout their intervals. AB10 has the task label and bounds without the separate trace. All input frames and the endpoint belong to the same participant and interval. The investigators’ stride-normalized release is a separate file. [Dataset and rights](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Selected bounds, units and channels](knee_moment_schema.json)

The authors treated exact zeros as gaps when removing unsuitable strides. For the present endpoint, both moments must be finite and nonzero at the target frame. This conservative rule can discard a genuine zero crossing. Intervening moments do not enter the input or determine endpoint eligibility. The selected files supply a net moment during swing as well as stance. The target uses the archived moment in both phases. [Data processing](https://doi.org/10.1038/s41597-021-01057-9)

## Reproduce the selection

Download `Streaming.mat` from the CC0 deposit by Emma Reznick, Kyle R. Embry, Ross Neuman, Edgar Bolívar, Nicholas P. Fey and Robert D. Gregg. Use the full file SHA-256 in the adjacent schema. The adapter needs Python 3.11 or later, h5py and NumPy. In h5py the first array dimension selects the component and the second selects time. The loaded arrays have one row per time point. The optical columns run right and left for knee, hip and ankle, in that order. [Streaming release](https://doi.org/10.6084/m9.figshare.14558181.v1) · [Source adapter](knee_moment_source.py)

```python
import h5py
from knee_moment_source import future_moment, load_trial, verify_archive

verify_archive("Streaming.mat")
with h5py.File("Streaming.mat", "r") as archive:
    trial = load_trial(archive, "AB01", include_moments=True)
target = future_moment(trial, 500)
```

Here 500 is an index within the retained interval. To recover the zero-based full-trial cutoff, add `trial.first_source_frame`. A missing or out-of-range endpoint returns `None`. Calling `load_trial` with its default settings reads only optical angles and task metadata. AB01–07 form the development set. AB08–10 form the assessment set for the mechanics predictor. All ten participants’ knee angles had previously been evaluated in a separate angle-only study. [Exact selection and assessment split](knee_moment_schema.json)
