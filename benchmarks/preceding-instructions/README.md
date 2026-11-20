# Can an instructor’s words improve a one-second wrist forecast?

A headset recorded a person’s right wrist while an instructor spoke. The model waited until the annotated instruction had ended, then waited another quarter of a second. From the wrist’s recent movement and information already available at that point, it predicted how far the wrist would be from its current position one second later.

Repeating the wrist’s previous one-second displacement gave the smallest average error, **7.38 cm**. A fitted model using motion, task and information about the completed instruction missed by **9.79 cm**. Adding the identities of six recurring words raised its error to **10.04 cm**. Each of the four acquisition-code groups counted equally. There were 26 forecasts from seven recordings, with 20 of them from a single group. The records had previously been available for development of a different hand-search task.

The linear models were fitted on 44 usable examples. The study required at least 160 before fitting an attention model. The publisher’s transcript-confidence field was unrated throughout the admitted sample. These observations limit what this experiment can establish about language and later movement. [Methods, comparison models and uncertainty](preceding-words-model/README.md) · [Data source](https://holoassist.github.io/)

**[Try the wrist forecast](https://eliminatenoise.github.io/NeuroTranslation/hand-search/forecast.html).** Enter four earlier wrist positions and choose the words the model can use. To open it offline, double-click `forecast.html` or use the launcher for your operating system. An optional later measurement stays separate until you choose to compare it.

**Run the published calculation.** The package contains fitted coefficients, training scales, an invented input, and source code. The example’s coordinates and instruction are artificial. The reported study errors above come from the recordings. [Invented example and calculation](preceding-words-model/artificial.py) · [Fitted coefficients](preceding-words-model/results/weights.json) · [Aggregate results](preceding-words-model/results/aggregate.json)
