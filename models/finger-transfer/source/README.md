# Five recordings of a finger movement task

“Index” appears on a screen. A participant can bend the finger once or several times before the screen goes blank. The display gives us the instruction. Five glove sensors give us a separate measurement of how the fingers moved. A clinical electrode grid at the surface of each person’s brain recorded voltage throughout the task. These files let a researcher line up the three records on the time axis supplied by the depositor. [Stanford data collection](https://purl.stanford.edu/zk881ps0522) · [Original experiment](https://doi.org/10.1371/journal.pcbi.1002655)

The five development recordings were selected by their release codes before inspection. The working IDs below refer to different people. The anatomical grid is on the right for D02 and on the left for the other four. Assigning a contact to a broad region makes certain comparisons possible across people, but regional sampling differs. Handedness alone does not identify which hand performed an individual trial. No hand-side data field accompanies these measurements. [Source manifest and contributor codebooks](source-manifest.json)

| Working ID | Release | Array side | Contacts | Admitted seconds | Nominal glove ticks | Complete cue–blank pairs |
|---|---|---|---:|---:|---:|---:|
| D01 | bp | Left | 46 | 236.00 | 5,900 | 57 |
| D02 | cc | Right | 63 | 362.00 | 9,050 | 88 |
| D03 | ht | Left | 64 | 362.00 | 9,050 | 88 |
| D04 | jc | Left | 47 | 314.24 | 7,856 | 76 |
| D05 | jp | Left | 58 | 275.48 | 6,887 | 67 |

The crop starts at release row zero. For a recording of N milliseconds, take 60% of N, round down to a multiple of 40 milliseconds, then subtract four seconds. D01 also supplied data to an earlier single-person study. Its stricter limit of 236 seconds retains only the earlier fit interval. A complete pair has a fully bounded named-finger cue and following blank. The table counts all such pairs in the crop. The model applies additional calibration, timing and trial-matching requirements. [Development selection](selection.json) · [Source boundaries and counts](source-manifest.json)

## Read the measurements

The voltage array has one row per millisecond and one column per retained contact. Multiply the counts by 0.0298 for microvolts. The anatomical label at position k describes voltage column k **in that recording**. The contributor’s processing script supplies code 2, “rolandic,” which the task README omits. Codes 0 and 5 lack definitions in both sources. One D05 contact carries code 5. The model keeps an indicator for unassigned contacts. It can account separately for a region with no contacts. [Original source documentation and script digests](source-manifest.json)

The array called `target` contains the original `flex` readings. The columns run from thumb through little finger. Each has a sensor-specific offset and uses the glove’s raw counts. The release supplies no conversion to degrees. `cue` contains the displayed digit (1–5) or blank (0). The contributor’s separate `*_stim.mat` files label movement epochs. The original paper also describes identifying individual movement events and checking them. Neither the processed events nor a derived `behav` target enters this reader. Each selected source member contains `flex` and `cue`, with no variable named `behav`. [Source fields and original README](source-manifest.json) · [Study Methods](https://doi.org/10.1371/journal.pcbi.1002655)

Forty consecutive millisecond rows can carry the same glove reading. For each digit of each person we took the row numbers where its value changed in the first 80 seconds and checked their remainders on division by 40. Each digit had changes and exactly one remainder, zero. All changes in the rest of each admitted crop had the same remainder. The returned `time_ms` array gives that person’s nominal glove grid, including ticks at which the sensor value stayed still. The archive does not carry hardware timestamps to verify the arrival of an individual unchanged packet. The paper reports a between-device lag of 37 ms (SEM 3 ms). This reader uses the release alignment without an estimated per-person timing correction. [Timing and recording methods](https://doi.org/10.1371/journal.pcbi.1002655)

The recording Methods explicitly name subjects 1–8 for the glove. The task description covers subjects 1–9, and the task README maps D04 to subject 9. Its deposited `flex` variable has five varying columns on the same nominal block grid. D04 is included on the strength of that file. [Original article](https://doi.org/10.1371/journal.pcbi.1002655) · [D04 source receipt](source-manifest.json)

## Obtain a development prefix

Use Python 3.11 or later with NumPy and SciPy. Place this reader, its source manifest and its selection file in one directory. Choose a separate local cache directory. Each command prepares one selected person. Repeat it with D02, D03, D04 and D05 to obtain the other prefixes.

```sh
python fingerflex_source.py D01 --cache-dir ./private-cache
```

For an existing original MATLAB file, pass `--mat PATH`. For D01, `--bp-prefix PATH` can reuse the earlier checksum-verified 362-second crop. The reader checks the release catalogue, requests the selected ZIP member’s header and compressed byte interval, verifies the size, CRC and SHA-256, and binds each saved array to its own shape, dtype and SHA-256 in the manifest. An original variable is compressed across all time points. Its bytes must be unpacked to take the prefix. The saved cache contains only the admitted rows, screen codes and contact-region codes. Keep it private. [Reader](fingerflex_source.py) · [Archive and array digests](source-manifest.json)

Once the prefix is available, NumPy alone suffices to read it.

```python
from fingerflex_source import load_development

record = load_development("D01", "./private-cache")
ticks = record["time_ms"]
glove_counts = record["target"][ticks]  # One five-finger reading per nominal tick.
voltage_counts = record["voltage"]     # One row per millisecond, variable montage.
```

## Attribution and terms

Kai Joshua Miller deposited *A library of human electrocorticographic data and analyses* in the Stanford Digital Repository. The repository grants CC BY-SA 4.0 and requires respect for the privacy and confidentiality of individuals. This adaptation selects early recording intervals, renames variables and derives the nominal glove grid and coverage counts. The adapted material is available under CC BY-SA 4.0. Credit the original work, identify subsequent changes and preserve the share-alike terms. [Repository rights record](https://purl.stanford.edu/zk881ps0522.json) · [Data descriptor](https://doi.org/10.1038/s41562-019-0678-3) · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

The depositor requires the following paragraph, unchanged, in the Methods of any publication involving these data.

Ethics statement: All patients participated in a purely voluntary manner, after providing informed written consent, under experimental protocols approved by the Institutional Review Board of the University of Washington (#12193). All patient data was anonymized according to IRB protocol, in accordance with HIPAA mandate. These data originally appeared in the manuscript “Human Motor Cortical Activity Is Selectively Phase- Entrained on Underlying Rhythms” published in PLoS Computational Biology in 2012 [Reference].

[Reference] Miller KJ, Hermes D, Honey CJ, Hebb AO, Ramsey NF, Knight RT, Ojemann JG and Fetz EE (2012). Human Motor Cortical Activity Is Selectively Phase-Entrained on Underlying Rhythms. *PLoS Computational Biology* 8(9), e1002655. [Original publication](https://doi.org/10.1371/journal.pcbi.1002655)
