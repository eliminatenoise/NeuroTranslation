NEUROTRANSLATOR: RECENT FINGERTIP VELOCITY

A fingertip has moved. Give the saved decoder the preceding count window and
ask how fast it was moving along two source-coordinate axes. The useful result
is a signed number in metres per second that can eventually be compared with
an independent movement measurement. An attractive moving arm cannot supply
that measurement.

This directory contains unexecuted interface source. It includes no model
payloads, installed dependencies, runnable download, build or images from a
build. The server and page have not been opened, run or rendered. Read the
future-use instructions below as instructions for a separately qualified
package, not as evidence that such a package exists. Display this guide in a
sans-serif text viewer; plain text cannot control a viewer's fallback font.

WHAT YOU WOULD OPEN

After actual model/runtime and package qualification, the package root would
contain preview_server.py, preview.html and this README.txt, together with the
unchanged neural/__init__.py, neural/portable_loco.py, neural/portable_numpy.py
and requirements.numpy.txt. Its two fixed payload pairs would retain these
bundle-relative names:

artifacts/loco_multiregion/portable/first60seconds/model.weights.npz
artifacts/loco_multiregion/portable/first60seconds/model.architecture.json
artifacts/loco_multiregion/portable/full_training_partition/model.weights.npz
artifacts/loco_multiregion/portable/full_training_partition/model.architecture.json

The architecture files include preprocessing, source-local identities and
saved physical scalers. Their expected SHA-256 values are independently fixed
in preview_server.py: 355a1a1d40daea75417fce71ecf9b74116a266e7e8a733a424aa8b2a65425651
for first60seconds and
6332dd535b4ee2550699ea0bd49917064b91f0117d84e6d8b4adcd59a64092ef
for full_training_partition. The selected weight declarations are, respectively,
291ad8bc31e7314b67439f0586379089886723c9d41bb9f88764691cbc12b022 and
6fe0ce0daa86a3b99223cc590a1b6ad5f17e25a64cbf16ab5570e6f2e3bfd017.
These are supplier declarations retained from the accepted source case. Their
current payload bytes, existence and loaded state have not been checked here.
The unchanged decoder checks the metadata hash, then its bound weight archive
before inference. A different file with the same filename is insufficient.

The eventual package also needs the accepted full model card, source and
evaluation provenance, current qualified environment and dependency/license
records. Its release owner must supply the actual admitted payloads and current
package identity. Raw recordings, source checkpoints, protected tests, replay
windows and parity fixtures are not part of this interface's input package.
There is no route for downloading weights or arbitrary project files. The
broader raw-recording application is a different entry with a different
read footprint; this source does not launch or qualify it.

The Python entry uses the standard library for its local HTTP interface. Real
inference imports the unchanged PortableLocoDecoder, NumPy and SciPy lazily,
inside the explicitly invoked runtime. The recorded requirements are
numpy==2.5.3, scipy==1.18.1 and pydantic==2.13.5. This small HTTP entry does not
use Pydantic or PyTorch. Installed versions, compatible Python/platform and
normal offline dependency access remain to be qualified; nothing installs or
fetches packages automatically. Python 3.11 or later is the prospective entry
baseline, not an independently accepted environment claim.

In that future qualified environment, from that exact package root, the
end-user startup command would be:

python -I -B preview_server.py run --port 8765

Use it only after the release owner has qualified the actual model files,
matching code, local environment and intended use. These future-use instructions
do not authorize running this source candidate. It has never been invoked,
including --help. Opening the broader raw-recording application would require
its own qualification; this entry never opens it.

Open the printed http://127.0.0.1:8765/ address on the same computer. A different
available nonprivileged port can be selected explicitly; the printed address
then changes with it. Opening preview.html as a file cannot load a model. A
phone's loopback address refers to the phone, so this is not a remote phone
service or a demonstrated mobile interface. Ctrl+C exits the foreground server
and its socket closes. It has no cloud calls, background workers or inference
retry. Pool settings default to one for OMP, OpenBLAS, MKL, NumExpr and vecLib,
before numerical imports; existing process-local settings are retained. The
server handles requests sequentially in one process. These choices do not
establish performance, effective library threads or CPU/GPU qualification for
a future machine. Numerical backend geometry remains owned by NumPy/SciPy and
their BLAS implementation; no GPU backend is supplied or tuned here.

GIVE THE WINDOW ITS RECORDING

The source is Loco's nonhuman-primate reaching recording loco_20170215_02,
Zenodo record 3854034. M1 means primary motor cortex; S1 means primary
somatosensory cortex. Spikes were sorted into 344 source-local features, with
163 from M1 followed by 181 from S1 in the fixed original channel/sorted-slot
order. Each ID contains the original source, session, region, channel and slot
identity. It is a recording-feature ID, not proof that the same cell persists
across recordings.

Choose a training budget, then paste the caller source SHA-256 and a JSON
array of all 344 ordered feature ID strings. The expected source is
6cdaa3c9f6845bd3f0c31c45136f09ecc259049d1ea51fc327599c7e194a133c.
The expected-identity panel makes the loaded metadata inspectable. Its explicit
copy button fills those two declaration fields only; choosing a model never
silently fills them. Confirm that your count columns actually use that source
and order. The server passes your supplied source and IDs to decode; it does
not replace a wrong or missing identity with its own.

Paste a JSON array containing twenty rows of 344 numeric counts. Rows run from
oldest to newest. Each row is one completed 20 ms bin, so the window covers
400 ms. Counts are counts per bin, not firing rates in hertz and not a neural
voltage. Present-region values must be finite nonnegative integers that remain
exact and finite in float32. A Boolean is not a count. The page preserves the
entered number literals in the request. The server reads their decimal values
exactly before checking that present counts are integers within the finite
float32 range and exactly representable there. A tiny fraction cannot become a
zero count merely because a binary floating-point parser rounded it away.
Only then does the interface form a uniform numeric window for the unchanged
decoder; the supplied source, ordered IDs and optional mask keep their meanings.

Choose entered, simulated or caller-declared measured as the input origin.
Every choice is a caller declaration. A matching checksum and ordered ID list
check the declared software contract; neither can authenticate a recording or
a sensor. There is no empirical example window, synthetic template or hidden
prediction preloaded into this source. Entered or simulated data keeps its
origin label, and its output remains a model estimate.

WHAT THE TWO BUDGETS CHANGE

The short-budget selection is
first60seconds:combined:direct_scratch_specialist.
It needs all 344 recorded features and both regions. The other selection is
full_training_partition:combined:unfrozen_source_trunk.
It uses the same source features, with learned region adapters and a
171-coordinate computational input basis. The saved selection rule is
validation only, unchanged after the protected test. Changing this selector
chooses an existing trained export; it does not train, fine-tune or reselect
anything.

With the mask omitted, both regions are present. If you choose an explicit
mask, it must include Boolean M1 and S1 entries. The short-budget direct model
requires both true. The full-budget adapted model supports an absent region by
removing that region's whole affine branch, including its bias. All regions
absent is unsupported. Keep twenty rows and all 344 numeric columns even when
a region is masked. Their values must still be finite JSON numbers. The
interface replaces masked columns with zero placeholders before NumPy can
choose a dtype for the complete array, so those ignored values cannot alter
the representation of present counts. The unchanged decoder then omits the
masked affine branch and its bias. Masking does not reconstruct unobserved
cells or qualify a missing-region biological claim.

Before either saved model reads the window, counts pass through a square-root
transformation and standardization with saved training values. The direct
model reads those 344 features. The adapted model instead transforms each
available region through a learned matrix plus bias and sums the branches into
171 coordinates. Those are coordinates in a computation, not measured neurons.

A gated recurrent unit, or GRU, then carries a state through the twenty bins.
Its reset and update gates determine which information that state retains.
The final state and mean input over the window feed the velocity head; saved
scalers restore physical units. The computation has learned weights from the
saved training study. Pressing the estimate button does not change them, and
software state in a GRU does not establish learning in a biological body.

READ THE ARROW WITHOUT INVENTING A JOURNEY

Select Estimate recent velocity. The old result disappears before submission.
A successful reply identifies this request, model, origin and mask, and gives
signed X and Y estimates in m/s. The equal-axis arrow shows the same two
numbers. Its axis extent adjusts to their magnitude and is printed beside it;
compare component values rather than arrow length across different estimates.
A zero vector has no direction. There is no integration into position, no
manufactured trajectory, no body animation and no anatomy claim.

The comparison target in the original study came from successive selected
fingertip positions divided by actual elapsed time. Positions were transformed
into XY metres using -0.01 × rawfinger columns 1:3, retaining the original
(z, -x, -y) centimetre convention. Signs therefore belong to that transformed
source frame; this display does not label them as anatomical forward or left.
The nominal last position support ends 4 ms before the count-bin end. Physical
acquisition and physiological latency are unknown. A browser request's wall
clock cannot replace either measurement.

The result concerns recent movement within this source and recorded task.
Neither a future motor command nor unique intent is established. There is no
calibrated uncertainty interval in this entry and no new measured reference
velocity in the page. Decimal places are numerical detail, not a measure of
biological accuracy. The saved study did not confirm source-transfer benefit
for either budget. No claim of human EEG equivalence, cross-recording or
cross-species transfer, persistent cell matching, sensory delivery, retained
skill or biological teaching follows. Unmeasured spinal and peripheral activity
stays unmeasured; EMG would not be a direct peripheral nerve recording.
Physical spinal scope remains read-only. There is no actuation or stimulation.

WHEN A REQUEST FAILS

Validation errors name the input requirement that failed. The server rejects
unexpected fields, malformed UTF-8/JSON, duplicate JSON keys, NaN/Infinity,
nonfinite numbers, ambiguous or missing Content-Length, non-JSON content types,
unsupported encodings and bodies larger than 1500 kB (1,500,000 bytes). It
checks the complete window shape, count representation, physical units, source,
ordered IDs and supported region mask. It returns no private path or traceback.
Only GET /, GET /api/models and POST /api/decode exist. The server binds IPv4
loopback only. Exact Host, same-origin/loopback checks and a per-process request
token guard decoding; there is no cross-origin permission header or arbitrary
file-serving route. These are source mechanisms, not an independent security
or runtime test result.

The complete request read has a ten-second deadline including headers; writes
have a five-second socket timeout. The browser waits at most 45 seconds, with
no automatic retry. A validation refusal clears the estimate and permits a
corrected manual submission. A timeout, transport failure or mismatched reply
can leave the server outcome unknown: the page clears output and disables
further submissions. Closing the page does not cancel running inference. Resolve
that outcome before a new attempt; do not treat an absent result as proof that
nothing ran. The server consumes each UUID before inference, rejects repeat
IDs and caps a process session at 1024 attempted inference requests. IDs are
held in memory only; restarting does not resolve an earlier unknown outcome.
There are no automatic reconnect, retry, recovery or persistence claims.

The page is self-contained HTML, CSS and JavaScript with no external libraries,
fonts or CDNs. It requests only this local server. Labels, native keyboard
controls, live request status, textual signed components and a described SVG
vector are present in source, with responsive layout and sans-serif families.
Actual browser behavior, accessibility, font fallbacks, phone use, offline
operation, performance, error/drain handling and exported output still require
their own checks. A source inspection cannot certify those outcomes.

THE EVIDENCE THAT ALREADY EXISTS

The saved independent portable comparison covered 8,330 windows per budget,
two velocity components each: 33,320 scalar outputs across both. Saved PyTorch
replay was bit-exact to its protected reference; the NumPy comparison, with
PyTorch imports blocked, recorded maximum differences of
1.4901161193847656e-08 m/s and 3.725290298461914e-08 m/s for the short and full
budgets. Acceptance used absolute tolerance 2e-6 m/s and relative tolerance
1e-5. Missing-region checks were narrower: 100 sampled full-budget windows for
each condition. These historical implementation comparisons are reused as
documentary evidence. They have not been rerun here, establish no new movement
accuracy or transfer result, and give no current interface latency measurement.

The full lifelike 3D body, anatomy, physics, reference SERIES, functional GUI,
full source-specific portfolio and broader model/scientific mission remain
open. Their scientific, reference, held-out, rights and output requirements
remain in force. A partial scientific display cannot replace them. A usable
release still needs the actual qualified model and build, an opened
and independently checked download and images captured from that same build.
No screenshot, paper or visualization archive can stand in for those results.

NAMES AND RIGHTS KEEP THEIR HISTORY

NeuroTranslation names the proposed field: mappings with stated sources,
targets, tasks and tests. NeuroTranslator names the implemented software.
NeuroTranslate names a proposed mapping operation. Current companion glossary:
revision 28, SHA-256
c253cdfa96c3ca68877ae2f5af05322d9876952bef8bed5eb646928d3ec90041.
The unchanged serialized model contract remains at historical revision 5,
SHA-256 17fadf58b0e550b1fc95732234dceb168dc0f399f08afcdd204e5e466898d235,
including the literal older Neurotranslator and Neurotranslation Network
labels. Current display spelling does not rewrite that evidence.

The acquisition receipt reports the recording as CC BY 4.0. Model, code,
dependency, body-asset, consent/use and redistribution rights need separate
review in their actual intended context. This private source step clears no
publication, Hugging Face, arXiv, clinical or distribution requirement, uploads
nothing and grants no permission expansion. SOURCE-REPORT.json records the
separate source-authoring evidence and remaining qualification requirements.
