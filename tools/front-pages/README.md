# The front pages are built from the result files, not typed

Fifteen pages of this repository are written by a program: the README you land on, the studies page, the website's start page, the papers page, the list of launchers, the rights page and nine smaller ones. Each page has a template in [`templates/`](templates/).

Where a page prints a score or an error, its template holds a short call that names a results file and the field the number sits in. [`build_front.py`](build_front.py) opens that file, reads the value, rounds it and writes it into the page. No score on these pages is typed by hand, so none can drift away from the result it reports. What the templates hold as plain text is written by hand: names, licences, links, and each study's settings, such as how far ahead it forecast.

The builder checks the sentences around the numbers too. A page that says the muscle signal made a forecast worse can be built only while the results file says so. If a result changes, the build stops at the call that checks that sentence and names it.

**To change one of these pages, edit its template, never the page.** The next build overwrites anything written into a generated page directly. Each generated page but three starts with a comment, invisible on GitHub and on the site, that names its template.

## Run it

From the top folder of the repository:

```
python3 tools/front-pages/build_front.py           # writes the fifteen pages
python3 tools/front-pages/build_front.py --check   # writes no page; lists each page as "same" or "DIFFERS"
```

It needs Python 3 (its standard library only), git, and two small programs from Poppler that read the papers' text and page numbers: `pdftotext` and `pdfinfo` (the `poppler-utils` package on most Linux systems, `brew install poppler` on macOS). It keeps the papers' text in `.cache/` beside it, a folder git ignores.

Two more options: `--out DIR` writes the pages into another folder, as a preview; `--facts FILE` also writes a table of every number it printed, with its page, file and field and the value before rounding.

## Change a page

1. Edit its template in [`templates/`](templates/). The table below says which template makes which page.
2. Run the builder.
3. Run it again with `--check`. Every page should say "same".
4. Commit the template and the page together.

A number goes into a template as a call between double braces. `{{ N('models/knee-motion/phase-results.json', 'transformer_mean_mae_degrees', 2) }}` prints that field of that file to two decimal places. The studies of the numbered table use `{{ S(n)... }}`, which reads the pointer the ledger holds for each of their numbers. Every call the templates use is defined in `build_front.py`.

## The fifteen pages

| Page | Its template in `templates/` |
| --- | --- |
| [`README.md`](../../README.md), the front page | `README.md` |
| [`benchmarks/README.md`](../../benchmarks/README.md), the studies page | `benchmarks-README.md` |
| [`docs/START.html`](../../docs/START.html), the website's start page | `docs-START.html` |
| [`papers/README.md`](../../papers/README.md), the papers page | `papers-README.md` |
| [`docs/papers/current/index.html`](../../docs/papers/current/index.html), the papers' page on the website | `docs-papers-current-index.html` |
| [`LAUNCHERS.md`](../../LAUNCHERS.md) | `LAUNCHERS.md` |
| [`docs/RIGHTS.md`](../../docs/RIGHTS.md), every dataset's credit and licence | `docs-RIGHTS.md` |
| [`docs/README.md`](../../docs/README.md), the website's file list | `docs-README.md` |
| [`docs/preview.html`](../../docs/preview.html), an old address that forwards to the start page | `docs-preview.html` |
| [`demo/README.md`](../../demo/README.md) and [`demo/RIGHTS.md`](../../demo/RIGHTS.md), the browser app's source folder | `demo-README.md`, `demo-RIGHTS.md` |
| [`interfaces/experimental/portable/NOTICE.md`](../../interfaces/experimental/portable/NOTICE.md) | `portable-NOTICE.md` |
| [`interfaces/experimental/portable/README.txt`](../../interfaces/experimental/portable/README.txt) | `portable-README.txt` |
| [`papers/current/README.md`](../../papers/current/README.md) and [`papers/current/index.html`](../../papers/current/index.html), the papers' own folder | `papers-current-README.md`, `papers-current-index.html` |

The last three carry no comment naming their template. The two pages of the papers' folder are part of the papers' release: the edition's `manifest.json` records their checksums, and the papers' download ZIP holds copies of them byte for byte. `README.txt` is plain text, where a comment would show.

## Add a study

First publish the study itself: its folder with its results files, under `benchmarks/` or `models/`, and its page under `docs/` if it has one. Then choose how the front pages show it.

- **Leave it to the builder.** A new folder under `benchmarks/` is listed at the next build after the studies page's newer studies, under "Published after this page was last written", with the first heading of its own `README.md` and a link. It enters no count. A new folder under `models/` is not listed by itself. A new page under `docs/` needs a card on the start page (below); the website's file list then gives it a line of its own, with a link.
- **Write it up.** Add its row, paragraph or card to the templates, with every number written as a call to its results file. When the website's file list gets a written row for a new page, add that page's folder name to `PAGE_ROWS` in `build_front.py`, so it is not listed twice.
- **Give it a row in the numbered table.** Every count on the studies page is a count of that table's rows, so a new row changes them all. The row goes into [`ledger.json`](ledger.json), each number as a pointer (the file, the field and the value read there), and the tallies in its `counts` block change to match. The builder recounts the tallies behind the studies page's tables from the rows and stops if they disagree.

Two kinds of new folder stop the build until a line is written for them, and the message says which:

- A page under `docs/` with an `index.html` must be linked from the start page. Add a card for it to `templates/docs-START.html`.
- A task folder of the general model, `models/neurotranslate-0.0/<task>/`, must be listed in `GENERAL_FITS` in `build_front.py`, as `'unseen'` or `'seen'` for the people it was scored on (nobody had looked at them before the test, or somebody had), or as `'not the general model'` or `'not a task'`. A test on people nobody had looked at also needs an entry in `UNSEEN` that asserts its result, because the front page's heading counts those tests and the general model's wins; `GENERAL_HEADING` must then say the new count.

## What stops the build

The builder stops, naming the template and the call, when:

- a value in a results file differs from the ledger's copy, so a result of the numbered table changed after it was checked;
- a sentence's claim no longer matches the results: which forecast came closer, whether a study's own rule was met, how many people were scored;
- a call in a template fails, or leaves `{{` or `}}` on the page;
- a page under `docs/` is missing from the start page, or a task folder of the general model is not listed (above);
- a result that the pages call "not in the papers" turns up in the papers' text. A new edition has caught up, and the pages' lists of what the papers leave out must change with it.

`--check` refuses one thing more: a page in the repository that is not what its template makes, which is what a hand edit to a generated page looks like. It lists that page as DIFFERS and ends with exit status 1.

## The ledger

[`ledger.json`](ledger.json) holds one row per study of the numbered table on the [studies page](../../benchmarks/README.md): each number with the file and field it was read from and its value there, and the tallies the pages print. Rows 1 to 25 were read from the repository at commit `6ff1c2b` and checked row by row against the result files on 20 November 2026; rows 26 to 29 were added from later commits the same day, each of their files pinned to the checksum its study published. The papers' source download holds the same rows and tallies in its own `ledger.json`.

## Files here

- [`build_front.py`](build_front.py): the builder. Its `TARGETS` table says which template makes which page.
- [`later_studies.py`](later_studies.py): finds the folders under `benchmarks/` that no row of the ledger names.
- [`ledger.json`](ledger.json): the numbered table's numbers, each with its source.
- [`templates/`](templates/): one template per page.
- `.gitignore`: keeps the builder's cache and Python's compiled files out of git.
