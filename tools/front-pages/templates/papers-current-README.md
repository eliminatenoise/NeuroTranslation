# NeuroTranslation and Brain2Body: the four papers

*NeuroTranslation: A New Paradigm In Brain-Body Mapping.* asks what a recording of the brain or of a muscle adds to a forecast of a movement that already knows how the body has just been moving, and reports every study of the repository's numbered table.

*Brain2Body: The Next Generation In Body-Brain Interfacing.* asks what a person keeps when a machine guides their hand through a skill and then stops. It is a proposal: it reports no experiment on that question.

Each is written twice: a Technical edition, and a Simple English edition that explains the same things in ordinary words. Start with a Simple English edition.

| | Technical | Simple English |
| --- | --- | --- |
| NeuroTranslation | [PDF, {{ pages(0) }} pages](neurotranslation-technical.pdf) | [PDF, {{ pages(1) }} pages](neurotranslation-explained.pdf) |
| Brain2Body | [PDF, {{ pages(2) }} pages](brain2body-article.pdf) | [PDF, {{ pages(3) }} pages](brain2body-simple-english.pdf) |

These are working drafts, built on {{ built_date() }}. Inside the project they have been read by checkers who had not written them, one for every number and statement against its source, the other for the writing: the whole of two editions, then every change made after that, the licences included. Every fix in this edition has been checked; the last few were made in the words the last check gave. Nobody outside the project has reviewed them.

## Where each study is

Each link opens the NeuroTranslation PDF at the study's row in appendix B, the table of every study (the macaque study at appendix A, where it is told in full). The study numbers are those of the [studies page](https://github.com/eliminatenoise/NeuroTranslation/blob/main/benchmarks/README.md) of the repository, which lists every study with its results. A PDF reader that ignores the link's destination opens at the first page; the page number is in the link's text.

{{ page_table_md() }}

## The files beside the papers

- [`NOTICE.md`](NOTICE.md): every dataset, simulator and typeface the papers rely on, with its licence and the credit it is owed. The two font licence texts are in [`third-party-notices/`](third-party-notices/).
- [`results/`](results/): the small result files of the studies that have no folder of their own in the repository: [`link-macaque.json`](results/link-macaque.json), [`earlier-decoding.json`](results/earlier-decoding.json), [`finger-intent-and-replay.json`](results/finger-intent-and-replay.json), [`simulated-arm.json`](results/simulated-arm.json), [`phrase-policy.json`](results/phrase-policy.json), [`muscle-pulse.json`](results/muscle-pulse.json) and [`template-mesh.json`](results/template-mesh.json). The seven hold aggregate numbers only, each with the file and field it was read from. Beside them, [`training-diagnostic-summary.json`](training-diagnostic-summary.json) is the long training run's own summary.
- [`manifest.json`](manifest.json): the checksum and page count of each PDF and of every file here, and the page of each study. [`font-provenance.json`](font-provenance.json): the fonts each PDF embeds.

Keep the files of this folder together so that the links between them work. You can also open the [reading index](index.html) in a browser. All dataset credits of the repository: [docs/RIGHTS.md](https://github.com/eliminatenoise/NeuroTranslation/blob/main/docs/RIGHTS.md).
