# Can an instructor’s words predict the next wrist movement?

A person wearing a headset works on a printer, a camera, a game console or a coffee machine. An instructor watches and speaks. After an instruction ends, we wait a quarter of a second and ask how far the person’s right wrist will be from its present position one second later. The headset supplies the two positions. Their straight-line distance, in centimetres, is the answer. A wrist can travel a long way and return to where it started, so this measure can be small even during a large movement. [HoloAssist dataset and paper](https://holoassist.github.io/)

**Repeating the previous second’s measured wrist displacement gave the smallest error, 7.38 cm. Adding the instructor’s words to a fitted model with recent wrist motion and task information raised its error from 9.79 to 10.04 cm.** We could score 26 forecasts from four recording groups. This pilot did not establish that words improved the forecast.

## What the models knew

We used completed instructor speech recorded during the activity. The source annotations mark its start, end and purpose. A fixed list of ordinary words allowed us to discard names and the wording of whole sentences. A word had to occur in at least three usable training examples to get its own model weight. Six survived — *back, change, off, on, put,* and *turn*. Their presence or absence was the entire language input. Word order and repeated words were discarded. Of the 26 assessment instructions, 14 contained a word the model retained. The remaining 12 still counted. Every included transcript carried the publisher’s literal confidence value `none`, so we could not test the forecast on affirmatively high-confidence transcripts. [Publisher’s annotation guide](https://holoassist.github.io/data_links/README.html)

For the motion input, we took the latest valid, tracked right-wrist positions at four times in the second leading up to the cutoff. Those positions gave the speed and direction between samples. A wrist could be out of view. We allowed a past reading to be up to a tenth of a second old and required distinct, advancing measurement times. The model also knew the device task, elapsed recording time, completed instruction length, how many distinct words matched the original list and the confidence indicator. The forecast used none of the later wrist readings. We looked for that endpoint only after applying the past-data requirements.

## What the measurements showed

Every number below is mean absolute error in centimetres. A 2 cm overestimate and a 2 cm underestimate each contribute 2 cm. We averaged within each recording, then within its recording group, then across the four groups. The same 26 forecasts enter every row.

| Forecast | Error (cm) |
| --- | ---: |
| Repeat the previous second’s straight-line displacement | **7.38** |
| Continue at the latest measured velocity | 9.27 |
| Fit recent wrist motion alone | 9.73 |
| Fit recent wrist motion and known task and timing information | 9.79 |
| Add the actual word indicators to the preceding model | 10.04 |
| Use the same fitted word model with all word indicators removed | 9.97 |
| Give it a different training instruction from the same task | 9.72 |
| Fit task and timing information, including the known word count | 10.79 |
| Fit task and timing information plus the word indicators, without wrist motion | 11.06 |
| Predict that the wrist stays in place | 10.90 |

To substitute words, we chose an instruction from a different training recording group that involved the same device task. Among those with a genuinely different set of retained words, we picked the closest one in elapsed time and instruction length on the prescribed log scale. All the recipient’s measured motion and contextual inputs stayed in place. Every scored case had a donor.

Actual words raised error relative to the motion-and-context fit in each of the four groups. The estimated increase was 0.25 cm. Resampling those four groups gave an exploratory 95% interval of 0.18 to 0.31 cm. The same model with substituted words had 0.33 cm lower average error than with actual words, with a paired interval for that difference spanning −0.23 to +0.97 cm (actual error minus substituted error). Four recording codes give little information about the wider population. Twenty of the 26 observations came from one code; equal group weighting cannot supply additional groups.

The assessment started with 52 qualifying instructions in six assigned recording groups. Twenty-four lacked recent wrist measurements. Of the 28 that remained, two lacked a usable future endpoint. The resulting 26 came from seven recordings in four groups and covered five device tasks. In every scored case, the endpoint lay one second after the cutoff on the released video grid. The underlying wrist sensor clock gave intervals of 0.978 to 1.024 seconds. We do not know how much additional timing error the speech annotation introduces. Other conversation overlapped six of the 26 forecast windows.

Eighteen recordings from eleven different groups were assigned to training. They contained 134 qualifying instructions. The hand-history requirement left 53. An observed target remained for 44 examples from 12 recordings and nine groups. This cleared the minimum to fit a regularized linear model, with 40 rows required. The attention model required at least 160 rows, eight groups and 20 retained words. It stayed untrained. The absence of a word advantage here leaves open what richer language input or more training data might show.

All 29 recordings came from the earlier hand-caption study’s development pool and the publisher’s training split. We froze the new recording-group split before looking at forecast outcomes. A group code identifies an acquisition group, and an individual actor or instructor may appear under more than one code. The earlier assessment, reserved groups and publisher’s evaluation data stayed unopened. This experiment measures a predictive association in visible wrist motion. It supplies no test of compliance with an instruction, neural activity, muscle force or the effect of changing what the instructor said.

## Try the calculation

The file `synthetic-reference.json` starts with invented past wrist movement, a device task and one retained word. It contains no later measured distance. The two model estimates let you check the arithmetic or see what happens when the word indicator changes. Changing a word in this calculation cannot tell us what changing a spoken instruction would do to a person.

Open `results/model.json` and `results/weights.json`. Subtract the training means from the indicated motion and context values and divide by their training scales. Append a zero-or-one column for each task, then each retained word, using the order in the model file. Multiply these numbers by the slopes following the first entry of `motion_context_words`, add its first entry (the intercept) and set a negative estimate to zero. The result is a model estimate in centimetres.

## Reproduce the study

The accompanying ZIP contains the fit and scoring code, hash-bound source inventory, a reader that recreates the restricted word indicators locally, the model weights and an invented calculation example. The HoloAssist source data carry the Community Data License Agreement – Permissive 2.0. The authored software and documentation carry CC0. Use a Python interpreter supported by NumPy 2.5.3, the version used to fit the model. PyTorch is optional; the actual fit never reached its predeclared attention threshold.

From the unpacked directory, keep the two sibling directories together. The source reader recreates the restricted word inputs from the publisher. `restore_tracks.py` requests only the 29 selected right-hand source members from the publisher, verifies each source digest, and checks the converted hand file against the frozen hash. The full restoration transfers about 916 MB of selected hand payload. It reuses matching local files. On a machine with the earlier workspace, the original verified `hand-text-source/train/` directory can be used directly. Restoring from the public server requires its pinned edition to remain accessible. Compression differences between environments can change a file hash; the script reports a discrepancy before assessment.

```sh
python -m pip install -r preceding-words-model/requirements.txt
python -B preceding-words-source/extract.py
python -B preceding-words-model/restore_tracks.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B preceding-words-model/fixture.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B preceding-words-model/run.py fit --workspace . --output reproduced
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B preceding-words-model/run.py assess --workspace . --output reproduced
```

`protocol.json` and `protocol-addendum.json` state the selection rules, model gates and comparisons fixed before fitting. The generated `fit.json` records the source and code fingerprints. `results/aggregate.json` gives the reported errors, intervals and exclusions. Running the two stages locally recreates the full group-level assessment. The two stages reject changed methods or inputs and require a fresh output directory for a new fit.
