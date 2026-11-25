# Use a compatible recorded history

Run `python predict.py --input /path/to/history.json --mode full --passes 3`. The forecast runs locally with NumPy. The input file follows `example.json`. The example uses invented values.

- Supply ten rows of 26 numeric fields under `history`. Row 1 covers the interval from −0.200 s through just before −0.180 s. Row 10 ends just before issue, which is time zero. Use the field order and units in `model-info.json`.
- Fill availability fields with 1 for present or 0 for absent. Supply 0 for a missing reading.
- Under `ultrasound_times_from_issue_s`, supply ten timestamps for the binned ultrasound values. Use `null` for an absent time. Set each present time inside its bin. `gap` removes the last five ultrasound values and availability fields. `blind` removes all ten.
- Use `--seed both` for the average of the two saved shared forecasts. Use `--passes 1`, `3`, `5` or `8` to vary the number of repeated refinement steps. Outputs are millimetres, ordered triceps then brachialis.

The two NumPy weight files preserve all saved 32-bit values. The runner rounds the normalized inputs and each successive model state to 32 bits. The other inference calculations use 64-bit NumPy arithmetic. All 36 combinations of input mode, pass count and checkpoint choice matched the saved forecasts within 0.000030 mm on 6,275 validation windows. The package runs the two shared checkpoints and the controls shown by the launcher. The study reports include additional methods. [Model and validation results](TECHNICAL.md)
