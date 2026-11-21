# Next Neuron Prediction

Open `index.html` in a browser. Replay the invented three-unit example or add observations yourself. The probability beside each local unit is its share of the model’s forecast for the next occupied millisecond. Two or more spikes in a single next bin have unresolved order. An empty history has no next-unit estimate.

Open **Open a different set of units** to choose a local JSON file such as `example.json`. The five model coefficients stay fixed as the local unit list changes. Only counts up to the most recent completed occupied bin enter the estimate. Use a separate history for each uninterrupted observation period. Choosing a file reads it on your device. The same input runs with the ordinary NeuroTranslate 0.0 prediction command.

For the two original rat recordings, an electrode unit represents a group of detected spikes attributed to a neuron by the original sorting method. The published experiment reports results for these detected units. [Sources and results](https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/next-neuron-prediction).
