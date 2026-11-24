# Outdoor insole pressure

NeuroTranslate forecasts the pressure measured by an insole 100 milliseconds ahead. Its same-foot model averaged 49.58 mbar of error on eight people held out of fitting and development. Carrying the latest reading forward averaged 60.37 mbar. These are results from outdoor recordings the study authors resampled offline.

- [Run the browser example](https://eliminatenoise.github.io/NeuroTranslation/outdoor-insole-pressure/)
- [Download the offline model and example](https://raw.githubusercontent.com/eliminatenoise/NeuroTranslation/main/benchmarks/outdoor-insole-pressure/outdoor-insole-pressure.zip)
- [Simple edition](SIMPLE.md) · [Technical edition](TECHNICAL.md) · [Results data](results.json)

To use the offline copy, extract the ZIP and open **Open insole pressure.html**. You can also use the Windows, macOS or Linux launcher in the extracted folder. The browser example starts with generated pressure readings. With Node.js installed, `node run.mjs example.json` runs the same model from the command line.

The recordings are from Viktor Losing and Martina Hasenjäger's NEWBEE study. The portable code and model weights use CC0, as does the source data release. [License](LICENSE) · [Dataset](https://doi.org/10.6084/m9.figshare.19834324.v1) · [Original study](https://doi.org/10.1038/s41597-022-01580-3)
