# Forecast a cued arm movement

A person sees a cue to move a supported right arm or hand. At a quarter of a second after the cue, what can three sensors already tell us about their own next readings? This reader runs the same fitted models on any of seven instructions and four editable summaries of early movement.

Extract the whole ZIP into one folder. Open **index.html**, or use **Open on Windows.cmd**, **Open on macOS.command** or **Open on Linux.sh**. No installation, connection or local server is needed for the reader. If your system restricts downloaded scripts, open **index.html** in your browser. Source and licence links to the original studies require a connection.

## Try two forecasts

Select **Bend the elbow** and compare **Transformer** with **Cue average**. Open **Edit sensor history**, select **Elbow** and change its last median. The cue average has only the instruction to go on. The Transformer also has the early readings. Their forecasts need not move together. Each plot starts at zero change from the final early median. Read all nine numbers under **Read the forecast values**. Choosing another instruction takes the same invented readings into the new comparison. An out-of-range message identifies entries beyond what the fit saw, and an in-range example can still combine readings in an unusual way.

The model receives the instruction in advance. Decoding speech, brain signals or a person’s intention would require different inputs and a separate test. The elbow, forearm rotation and index-finger signals each have their own scale and unresolved anatomical sign. The demonstration forecasts changes in these three stored readings.

## Read the recorded errors

For the development comparison, seven separate fits each left out one of people S1–S7. That person's recordings supplied the later targets for that fit. The interactive model above the table uses the final weights fitted to all 882 trials from those seven people. The evaluation selector lists the groups included in this edition. The fixed assessment group comprises S8–S12, held outside all seven development fits and the final fit. S13–S15 are reserved. Outcomes from this small study apply to the motions, people and instruments it tested.

Choose a held-out group, then one movement instruction or all seven. Each displayed value pools the group. The three time columns average the absolute distance between each prediction and later sensor change. They remain in the chosen instrument's native units. **Overall** combines all nine errors, each divided by the corresponding target's standard deviation on its fitting group. The development folds therefore have different scales. People, runs within person and instructions within run receive equal weight. A smaller value indicates a closer forecast. For rows marked “incorrect cues,” the fitted method received each of the six other cue labels with the same early readings. The scoring code averaged their absolute errors. These are evaluation controls. The table gives errors across recorded trials. It cannot give an uncertainty interval for your own invented forecast. The supplied public summaries contain full-precision cohort and per-cue means with paired comparisons across people. They omit named person breakdowns and trial-level readings.

## What happened in the five new people?

The fixed model predicted 630 trials from five people over 15 runs. The Transformer’s overall error was 0.4933. The cue average scored 0.4672 and predicting no change scored 0.4888. The Transformer beat the feed-forward network in all five people. It had lower error than linear ridge in four, with a group advantage below the required 5%. It beat the cue average in one person and no change in one person. The full comparison therefore fell short of the prespecified standard. One hundred trials had at least one early sensor summary beyond the fitting range. The source summary and the reader retain those trials.

## Inputs and predictions

The authors recorded motor execution and motor imagery. This reader uses only the first three motor-execution runs of each included person. All sensors here have 64 readings per second. The cue occurs on the 512 Hz event clock. The last permitted sensor sample is at index `floor((cue_tick + 128) / 8)`, up to seven event ticks before the nominal cutoff. Split the last 32 samples into four groups of eight in chronological order. Each row of `history` contains two groups of three values, in this order.

1. The medians of the elbow, forearm rotation and proximal index-finger channels over that group.
2. The last four samples' median minus the first four samples' median for each of those channels, in the same order.

Use the exact seven cue names in the Python implementation. Pass a four-by-six array of finite numbers. The fitted model accepts optional `method` with one of `transformer`, `cue`, `still`, `ridge`, `mlp`, `unconditional`, `transformer_no_cue`, `ridge_no_cue` and `mlp_no_cue`. The returned `delta` has one row for each of 0.5, 1.0 and 1.5 seconds **after the cutoff** and one column per sensor in the input order. Each number predicts the difference between the later eight-sample median and the last early median. Finite endpoints are the resolution of this test.

The Transformer learns how to mix information from the known cue and all four early bins. Its weights were fitted from scratch. The cue average predicts the fitting group's mean for that instruction. No change predicts zero throughout. Linear ridge uses cue plus sensor history in a regularized linear fit. The feed-forward network uses the same inputs with one nonlinear hidden layer. Each “without cue” model was fitted separately. The training average gives the same prediction for every instruction and history. The frozen protocol gives the complete scale definitions, model shapes, training settings, omission rules, score and prespecified comparison thresholds. [Protocol](method/PROTOCOL.md) · [Development group](method/development-summary.json) · [Five-person assessment](method/assessment-summary.json) · [Weights and fitting scales](method/model.json) · [Frozen study hashes](method/freeze.json) · [Public aggregate manifest](method/projection-manifest.json)

## Reproduce a forecast

Open a terminal in the extracted folder. The Python predictor uses NumPy; the browser uses plain JavaScript and the same weights. Both implementations return three rows and three columns of native sensor changes. To rebuild the static reader and its explicit-inventory ZIP, use Python 3.10 or later.

```sh
python method/predict.py method/example.json
python build.py --zip ../arm-transfer-offline.zip
```

The regular browser script exposes `CuedArmTransfer.predict(model, request)`, where `model` is the parsed `method/model.json`. The example and reference evaluation stay separate. The package checksum list identifies the inputs, numeric results, page, scripts and launchers. Data attribution and modifications are in the notice. [Example](method/example.json) · [NumPy implementation](method/predict.py) · [JavaScript implementation](method/predict.js) · [Rights](NOTICE.md)

The model repository includes the training and assessment programs, the frozen fitting record and the source checks needed to reproduce the study from the authors’ recordings. [Full study source](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/arm-transfer) · [Download the study package](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/models/arm-transfer-model.zip)
