# Reserved reaching-change comparison

[Open the browser forecast](https://eliminatenoise.github.io/NeuroTranslation/reaching-ultrasound-300ms/change/) · [Download the tested change forecasts](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/reaching-ultrasound-300ms/change-forecast/reserved/NeuroTranslate-Reaching-Change.zip) · [Simple report](SIMPLE.md) · [Technical report](TECHNICAL.md) · [Aggregate measurements](RESULTS.json)

Extract the ZIP and open `START.md` inside it. The program needs Python and NumPy. It runs the five fixed methods from the study on an invented example or a compatible history.

All methods forecast the signed change in ultrasound point spread around 300 milliseconds ahead. On the six reserved participants, the motion-only linear forecast averaged 0.1528 mm of error. Predicting no change averaged 0.1592 mm. The uncertainty range includes a tie for each muscle.
