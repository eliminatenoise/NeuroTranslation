[The studies](../README.md) › Study 20 · Pinch: width of the band

# A band set stage by stage was narrower and held more readings, and every band fell short during the release

A forecast gives one force reading to expect. A band around it says how far off the gauge may land: here, a range meant to hold 90% of the readings that follow. Around the five-grid pinch forecast of [study 19](../cemhsey-arrays/README.md), one band width for the whole pinch was **2.21%** wide and held 4,476 of 4,736 later readings (94.5%). A width set separately for each stage of the cue was **2.16%** wide and held 4,502 (95.1%): narrower, and it held more. The same held for all three forecasts tested. But while the pinch was being released, every band fell below 90%.

Widths are in % of the person's hardest squeeze that day (their maximum voluntary contraction, MVC). The band score charges a band both for its width and for every reading it misses, so drawing a very wide band costs something; lower is better. [Interval score, equation 43](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

| Band around | Width set from | Later readings inside | Share inside | Average width | Average band score |
| --- | --- | ---: | ---: | ---: | ---: |
| Repeat the current force | The whole pinch | 4,493 / 4,736 | 94.9% | 2.89% | 3.32 |
| Repeat the current force | The same stage of the cue | 4,499 / 4,736 | 95.0% | 2.54% | 2.90 |
| Force history and cue | The whole pinch | 4,466 / 4,736 | 94.3% | 2.20% | 2.60 |
| Force history and cue | The same stage of the cue | 4,494 / 4,736 | 94.9% | 2.15% | 2.47 |
| Force, cue and five EMG grids | The whole pinch | 4,476 / 4,736 | 94.5% | 2.21% | 2.60 |
| Force, cue and five EMG grids | The same stage of the cue | 4,502 / 4,736 | 95.1% | 2.16% | 2.48 |

The release was the hard part of the cue. Around the five-grid forecast, the band set by stage held 704 of 800 release readings (88.0%), despite its higher share over the whole trial; the single width held 87.1%. All six bands held between 86.1% and 89.6% of the release readings, short of the 90% target. Widths and scores are counted over the same forecast moments. Rounding the widths for display can hide small differences; the comparison uses the unrounded averages. [Results file](RESULTS.json) · [Explore by stage of the cue or recording day](https://eliminatenoise.github.io/NeuroTranslation/cemhsey-intervals/)

## What was done

The forecasts had already been fitted, in study 19. Eight recordings from four people set the band widths. Eight other recordings, from two other people, tested how much the bands held and how wide they had to be. The test recordings were opened once, after the widths were fixed. Each 30-second trial gives 592 overlapping forecasts. [Study plan](PROTOCOL.md) · [Inputs fixed in advance](DESIGN.json) · [Original acquisition study](https://doi.org/10.1038/s41597-025-05733-y)

The rule set before scoring called a band set by stage "a descriptive gain on this panel" if it was narrower, held at least as many readings and had a lower score than the single width; narrower but missing more would have been a trade-off. All three bands set by stage were descriptive gains. That is a rule about how a band is drawn; it says nothing about which forecast is better.

## What it does not show

Every trial follows the same 30-second cue, and a band can miss at many neighbouring moments during one swing of the gauge. Four people setting widths and two testing them say nothing about how much a band would hold for other people, nothing about live timing, and nothing about holding a whole trace at once. [Original recording study](https://doi.org/10.1038/s41597-025-05733-y)

[Download the 48 comparisons, whole-pinch and by stage, with the share of readings below and above each band](../../docs/cemhsey-intervals/metrics.csv)
