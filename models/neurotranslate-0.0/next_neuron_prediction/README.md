# Which recorded unit fires next?

After the first spike, each candidate gets a probability. After another spike, those probabilities change. The five learned coefficients stay fixed. They come from one rat on a W-shaped track. The candidate list and counts belong to the recording you supply.

Run the invented three-unit example from the directory containing `predict.py`. Python and NumPy suffice.

```sh
python predict.py next_neuron_prediction/example.json
```

Use one continuous trial per file. A sorted unit is a group of recorded spikes attributed to one neuron. List every candidate in `local_units`, including units that have supplied no spikes. Use at least two different integer IDs or nonempty names. Keep them in the same order in every row. Each row contains the spike counts in one complete millisecond, open on the left and closed on the right. A spike exactly at 5 ms belongs in the bin ending at 5 ms.

```json
{
  "domain": "next_neuron_prediction",
  "local_units": ["Amber", "Birch", "Cedar"],
  "bins": [{"end_ms": 1, "counts": [0, 1, 0]}]
}
```

`end_ms` is the integer closing boundary on the recording clock. Rows must increase in time. Give a known nonnegative integer count for each unit. You may leave out known empty bins or supply rows of zeros. Split at a gap in observation and begin again with fresh counts. A missing reading cannot count as zero. Drop partial edge bins.

The command returns one result for the supplied prefix. `logits` are the raw scores. Their softmax gives `next_unit_probabilities`, one entry per local ID in its original order. At 1 ms the scores give Birch 57.67% and the other two 21.16% each. At 5 ms Amber has also fired, and Birch still leads at 45.13%. Both Birch and Cedar fire in the bin ending at 9 ms. There is no single next unit to score for the forecast made at 5 ms. Both spikes still enter the new forecast at 9 ms. [Input](example.json) · [Output after each occupied bin](trace.json)

`observed_through_ms` marks the last supplied row. `forecast_time_ms` marks the end of the latest occupied bin. An empty row leaves the last forecast in force. Before the first occupied bin the forecast time, scores and probabilities are `null`. The target is the unit supplying the next spike observed in this trial. A future bin with multiple spikes leaves its identity unresolved at this resolution, even when they came from one unit. Trial end censors any outstanding forecast. The model supplies probabilities for identity only. The time of the next spike remains unknown.

On ten held trips of a second rat with 122 locally sorted units, the fitted model’s first choice earned 19.49% credit. A fixed count-and-recency rule earned 19.50%. Log loss, which uses every forecast probability, was 3.379 for the fitted model and 3.484 for that rule. Both rats came from one experiment. The recording supplied offline unit identities. Live sorting delays, unrecorded neurons and transfer to people remain unmeasured. [Study and reproduction](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/next-neuron-prediction) · [Browser experiment](https://eliminatenoise.github.io/NeuroTranslation/next-neuron-prediction/) · [Sources and rights](NOTICE.md) · [File provenance](provenance.json)
