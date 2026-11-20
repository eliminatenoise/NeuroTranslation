# How precisely do words identify a recorded movement?

An observer described a performance after seeing it. Two studies asked whether a model could use those words to find the original movement in a set of recordings. This supplement to *NeuroTranslation: A New Paradigm In Brain-Body Mapping.* reports the comparisons and what they permit us to say about physical guidance and learning.

[Read in a browser](language-and-movement.html) · [Download the four-page paper](language-and-movement.pdf) · [Use the LaTeX text](language-and-movement.tex) · [Inspect sources and study-result fingerprints](evidence.json)

## Edit and rebuild

Edit the HTML to change the paper across formats. Opening it directly in a browser works offline. Keep the evidence file beside it. To rebuild the PDF and LaTeX fragment, install Python 3, ReportLab 4.4.9 and the four Liberation Sans TrueType styles, then run this command from this directory.

```sh
python export.py
```

The verified export used Python 3.12.14. Set the environment variable `LIBERATION_FONT_DIR` to the font directory if the exporter cannot locate it. Repeating the export with the same inputs produced byte-identical PDF and LaTeX files. To incorporate the fragment in an existing LaTeX article, load `hyperref` in the preamble and use `\input{language-and-movement.tex}` at the point of insertion. The fragment follows the host article's pagination.

The supplement text and export code carry the CC0 1.0 dedication. Source dataset terms are given in the manuscript and evidence file. [CC0](LICENSE)
