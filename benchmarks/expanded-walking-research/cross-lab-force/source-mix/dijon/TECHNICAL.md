# Frozen force forecasts on the Dijon overground cohort

The browser exercise runs the published weights and displays the three reported Dijon test groups. [Compare forecasts in the browser](https://eliminatenoise.github.io/NeuroTranslation/force-forecast/)

On the prespecified subset with latest plate force mean at least 20 N, the mixed recurrent correction had mean absolute error **10.0355 N·s**, compared with **10.1349 N·s** for walking-only and **14.0301 N·s** for the recent-trend control. The paired mixture gain was 0.0994 N·s, with a 95% resampling interval of −0.2639 to 0.4874. The walking-only correction beat trend for all 29 participants. [Simple edition](SIMPLE.md) · [Aggregate results](results.json)

## Recording and forecast windows

Use version 1 of Riglet and colleagues’ Dijon archive, all first-session raw C3Ds for comfortable overground walking. The first participant by archive ID was assigned to engineering from the file inventory alone. The other 29 were assigned to evaluation. The clock is 100 Hz for frame layout and 1,000 Hz for the analog force. The two type-2 platforms supply force channels calibrated in newtons. We project those readings onto the lab vertical using the platform geometry. Engineering cross-checked selective slices against a second reading method. For each evaluation recording, the native calibration is used with fixed channel names, axes and scale signs. The measured outcome concerns the load on each recorded plate. [Author methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC11139954/) · [Versioned data](https://doi.org/10.6084/m9.figshare.25592865.v1)

The issue grid starts after the first 200 ms and advances in 400 ms increments while a full 100 ms outcome fits. Each input is ten successive 20 ms means, most recent last. The target sums the following 100 native readings on the same plate and multiplies by 0.001 s. The grid keeps every issue history disjoint from every target span. We sealed forecasts for all 19,846 plate windows before numerical decoding of any target span. The test uses the seven methods and fitted weights from the earlier study. Each of the three recurrent methods averages its three independently initialized and trained networks before scoring. [Model and fit specification](../TECHNICAL.md)

## Errors on common support

Participant means receive equal weight. All three groups contain 29 participants. The loaded and lower-load subsets use the most recent average in each forecast’s input.

| Method | At least 20 N, 855 rows | Below 20 N, 18,991 rows | All 19,846 rows |
| --- | ---: | ---: | ---: |
| Persistence | 15.3110 | 0.1700 | 0.8669 |
| Recent trend | 14.0301 | 0.2130 | 0.8500 |
| Walking-only ridge correction | 11.6955 | 1.3373 | 1.8163 |
| Mixed ridge correction | 12.3677 | 1.4301 | 1.9334 |
| Walking-only recurrent correction | 10.1349 | 0.3489 | 0.8015 |
| Mixed recurrent correction | 10.0355 | 0.3616 | 0.8085 |
| Mixed direct recurrent forecast | 10.8502 | 0.2776 | 0.7644 |

For loaded histories, the paired walking-only correction gain over trend was 3.8952 N·s, with interval 3.1665 to 4.7050. The mixed correction gain over trend was 3.9946 N·s, with interval 3.1856 to 4.8644, and it improved 28 of 29 participant means. Intervals use 4,000 paired resamples, with participants as the independent units. Window counts are support counts.

The recurrent correction improved on trend for loaded overground plates in this cohort. The estimated effect of adding the second training archive spans zero. The lower-load subset favours persistence. Any switch rule based on these results needs a separate evaluation. [Read the original comparison and download the models](../SIMPLE.md)
