# Which wrist moves when the annotated side changes?

A reach on the left side of one camera image may land on the right side of another. Which wrist should a model follow? Here the movement annotation names the wrist opposite the implanted hemisphere. The model calls it *contralateral*. It follows the other wrist, the *ipsilateral* wrist, separately. Fifteen earlier frames set the axes and the scale. Both forecasts go back into the original camera image.

From the extracted NeuroTranslate 0.0 directory, run these commands with Python 3.10 or later and NumPy.

```sh
python predict.py cross_person_wrist/example.json
python -m cross_person_wrist.verify
```

The example contains an invented right-hemisphere implant and a left-wrist reach. All bundled coordinates and fitted coefficients come from simulation. The companion file gives the invented future positions for comparison. The predictor reads only the earlier frames. [Input](example.json) · [Forecast](expected.json) · [Invented future](invented-reference.json)

## Read the two times and two wrists

Each method returns a two-by-two grid. The rows give the two times, eight and fifteen frames after the last observed wrist. At a nominal 30 frames per second that is about 267 and 500 milliseconds. The columns always run contralateral, then ipsilateral. Each entry is an image position `[x,y]` or `null` with an explanation in `reason_by_horizon`. Use `role_wrist` to look up the original side.

`endpoint_native_px` uses the detector's original image pixels. `endpoint_shoulder_widths` gives the same point relative to the final earlier shoulder midpoint. Its lateral axis points from the ipsilateral shoulder towards the contralateral shoulder. Its perpendicular points towards decreasing image y. One unit is the median projected shoulder separation over the fifteen frames. The Transformer also reports its wrist displacement and its endpoint relative to the final earlier shoulder in units of that arm's own projected length. Two projected upper-arm and forearm segments give that length. `span_change_px` is the forecast change in the distance between the two wrists in the image.

## What can the other arm contribute?

The primary model, `ridge`, fits one regularized linear regression per wrist and time. For each of the 15 frames it reads three landmarks relative to the last earlier wrist, all in shoulder widths. It standardizes those 90 features using the development recording alone and fits future wrist displacement with penalty one on mean squared error. Compare it with `persistence` (hold the wrist still), `velocity` (continue its average motion between the first and last earlier frames) and `damped_velocity` (scale that motion by a gain between zero and one, fitted on the same development rows). The prespecified human comparison asks whether ridge beats damped velocity on the contralateral wrist at **both** times, using paired mean endpoint error in shoulder widths.

The temporal Transformer asks a different question. Each arm contributes fifteen time steps. Two attention heads mix the resulting thirty tokens. A residual feed-forward layer and gated readout predict changes from the development mean at both times. Three fits with separate initial weights contribute equally to each forecast.

| Method | What each target wrist can use |
| --- | --- |
| `intact` | Both arms from this event, with parameters fitted on all eligible training events. |
| `blocked` | Its own tokens throughout training and prediction. Both shoulders still define the common frame. |
| `intact_swapped` | Its own arm plus the other arm from an earlier event. The intact model keeps the same weights. |
| `matched_intact`, `matched_blocked` | The same two fitted interventions restricted to the same donor-eligible training events. |
| `matched_intact_swapped`, `trained_swap` | The earlier other arm, first using the matched intact weights and then using weights trained with the substitution. |
| `zero`, `mean_px`, `mean_normalized` | Zero displacement, mean displacement in aligned pixels, or mean displacement in arm lengths. |
| `constant_velocity`, `kinematic_ridge` | Continue the last five-frame slope, or regress displacement on shoulder and segment slopes over 4, 8 and 15 frames. |

A donor supplies only the other arm's earlier tokens. It is aligned to its own shoulders before substitution. The recipient retains its own wrist anchor, arm scale and shoulder frame. These controls test what the other arm's tokens add once both shoulders have established the coordinate system.

## Forecast a local case

Use `example.json` as a template. The six track names are `R_Wrist`, `R_Elbow`, `R_Shoulder`, `L_Wrist`, `L_Elbow` and `L_Shoulder`. Each track holds 15 ordered pixel pairs. Supply nonnegative native `frame_indices` and the archive's independently established `implant_side` and `annotated_wrist`. The interface accepts the two opposite-side label pairs. The recording's own metadata has to establish which applies. The earlier-donor member is optional. When supplied it must describe the same recording, at least 900 frames earlier in a distinct 3,600-frame block. The local reader assigns the block from the frame immediately after the final earlier sample.

Leave missing coordinates as JSON `null`. A gap in the frame sequence or either shoulder prevents the common reference. A width below one pixel, an unstable shoulder direction (mean separation vector shorter than half the median width), or an ambiguous up direction (absolute image-y component below 0.10) also prevents it. Missing elbow or wrist history withholds that arm's ridge output and every bilateral method. The other ridge arm can still run. A bilateral projection whose median arm length is at most 0.000001 pixels also abstains. A missing donor disables only methods that need it. Neither interpolation nor physical camera calibration is part of this interface.

The human study used 2D pose estimates and retrospectively marked contralateral reach onsets. The first unseen index for onset time t is the ceiling of 30t. Take the fifteen frames before it. The future landmarks are seven and fourteen frames after that first unseen index. This task measures forecasts conditional on a marked event. It supplies no onset detector, depth, force, nerve activity or physical distance. A change of camera perspective or foreshortening can change apparent lengths. Read the original recording and annotation methods before using real signals. [AJILE12 data release](https://doi.org/10.48324/dandi.000055/0.220127.0436) · [Methods](https://doi.org/10.1038/s41597-022-01280-y)

## Rebuild the fitted weights

With PyTorch installed alongside NumPy, run the command below from the extracted NeuroTranslate 0.0 directory. It creates a new JSON checkpoint and prints errors for fifteen held invented events, broken down by time and wrist. These errors measure agreement with the simulator whose rules generated those events.

```sh
python -m cross_person_wrist.rebuild rebuilt.json --threads 2
python predict.py cross_person_wrist/example.json --checkpoint rebuilt.json
```

The simulator rotates two planar segments per arm. The length of each segment, camera translation, shoulder width, movement phase and speed vary. Sixty invented events train the models. A fresh random stream generates the held series with the opposite camera orientation and implant side. The first evaluation event supplies an earlier donor, leaving fifteen common recipients. Training uses double precision, full batches, AdamW at learning rate 0.003 and weight decay 0.01, and sixty updates per network. The initialization seeds are 17, 43 and 97. The loss on residuals is a smooth approximation to absolute error with transition scale 0.1 arm lengths. A two-thread CPU rebuild was checked with Python 3.14, NumPy 2.5 and PyTorch 2.14. Floating-point results can vary across library versions. Compare endpoints with absolute tolerance 1e−9 pixels. [Generator](simulate.py) · [Numerical checks and synthetic errors](synthetic-evaluation.json)

## Use your own development recording

Obtain the versioned recordings and metadata from the AJILE12 release under its stated access and licensing terms. Each person's pose estimator and camera view matter. Keep one source recording for fitting and leave a different person out of every development choice. Store histories and individual coefficients locally. [Official DANDI release and download instructions](https://dandiarchive.org/dandiset/000055/0.220127.0436) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

One JSON line per development event holds a `case` in the input format above, without a donor, and `future_by_name` containing `L_Wrist` and `R_Wrist`, each with two pixel pairs at +8 and +15. Keep unavailable outcomes as null coordinates. Use a single recording in chronological order, one event per two-minute block and at least thirty seconds apart. The fitter preserves the rows with missing landmarks. Each ridge head uses its own eligible rows. The bilateral ensemble needs both arms and both outcomes. Donor-dependent training uses the most recent earlier event with eligible bilateral inputs. It needs no outcome from the donor.

```sh
python -m cross_person_wrist.fit_local development.jsonl local-fit.json
python predict.py local-case.json --checkpoint local-fit.json
```

If you already hold a compatible fitted ensemble (a `shoulder-frame-v1` NumPy archive) and a four-head prospective ridge JSON, the importer validates the parameter names and shapes, removes source-event metadata and writes only a local checkpoint. Keep the converted file private along with its inputs. The public example and checkpoint are released with the package under CC0. [Software licence](../LICENSE)

```sh
python -m cross_person_wrist.import_fit ensemble.npz ridge-heads.json local-fit.json
python predict.py local-case.json --checkpoint local-fit.json
```
