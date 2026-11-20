# What moved when someone jumped?

Cameras around a laboratory tracked markers attached to a person's head, trunk, arms, hands, legs and feet. Each dot in this viewer follows one marker. Turn the view or choose a marker to inspect its position. Lines between dots help you follow the body. The dots give positions on the body surface. They cannot tell us how hard a muscle pulled or which nerves fired.

**[Open the three recordings](https://eliminatenoise.github.io/NeuroTranslation/whole-body/)**. To use them offline, download `index.html` and open it in a browser. The page contains all three recordings. In a downloaded copy of this folder, the Windows, macOS and Linux launchers open that same file.

| Movement described by the lab | What you can see in the displayed frames |
| --- | --- |
| Bend, scoop and lift | The right-hand marker spans 1.96 m vertically. The left-hand marker spans 0.51 m. |
| Jump forward | The centre of the four waist markers ends 1.34 m from where it began, measured across the floor. |
| Hop on the left foot | The waist markers travel 3.77 m across the floor between the first and last displayed frames. The right heel spans 0.77 m in height, the left heel 0.28 m. |

A *span* is the difference between the highest and lowest marker positions. The across-floor measurement is the straight-line horizontal distance between the two waist-centre positions. Both calculations use the archived marker paths. A foot's height alone cannot establish which foot carried weight. The wording for each movement comes from the lab catalogue. These recordings contain no spoken instructions or electrical recordings of the brain or muscles. [How the laboratory captured motion](http://mocap.cs.cmu.edu/info.php)

## Where the dots come from

The cameras recorded 120 frames each second. The viewer keeps every fourth frame, in the original laboratory coordinates. Each displayed frame contains 41 named marker positions, rounded to 0.1 mm for storage. That increment describes the saved numbers. The original measurement accuracy is unknown. Archive positions can include interpolation or other processing. In the hopping trial the archive supplies zero quality values throughout. Its saved positions do not carry per-marker accuracy. The source files specify upward Z for the scoop and jump. In the hopping file, where the screen axes are unspecified, head and heel heights support that orientation. [C3D point quality](https://www.c3d.org/HTML/Documents/3dpointresiduals.htm)

The three trials occupy 18.60, 3.43 and 6.20 seconds from the first to the last displayed frame. The native one-based frame numbers are stored in each JSON file. The forward-jump file includes additional model outputs. The viewer takes only the named body markers used for this comparison. The recording identifiers identify catalogue entries. They are insufficient to prove that all three people are different. [Scoop, trial 02_06](http://mocap.cs.cmu.edu/search.php?subjectnumber=02) · [Jump, trial 13_11](http://mocap.cs.cmu.edu/search.php?subjectnumber=13) · [Hop, trial 132_23](http://mocap.cs.cmu.edu/search.php?subjectnumber=132)

## Rebuild and check

Run the commands from this folder. `build.py` reads the original C3D point files. With `--download` it requests the three public files, checks each expected SHA-256 checksum and saves the original in `source/`. The check script uses Python’s standard library to read the original point words directly. It compares every displayed coordinate and frame number with the source, including the older DEC-format jump file.

```sh
python -m pip install -r requirements.txt
python build.py --source source --out data --download
python check_source.py --source source --packets data
npm ci
npm run build
```

The shared game viewer is in `viewer/`. The page builder bundles that code and the unmodified data packets into one HTML file. The browser verifies the selected packet before it draws the first frame. The NeuroSurge game reads the same packets from its own distribution. Linux Chromium replayed every clip from the saved page with network access disabled. Native Windows and macOS execution remains unverified. [Game preview](https://github.com/eliminatenoise/NeuroSurge/pull/2)

## Credit and reuse

The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. Carnegie Mellon permits copying, modification and redistribution of the motion recordings, including use in commercial products. Its terms prohibit direct resale of the data, including converted data. Those terms apply to the movement packets in this folder and their embedded copies in the HTML page. The project's original code and explanations carry the CC0 dedication. [CMU terms](http://mocap.cs.cmu.edu/) · [CMU FAQ](http://mocap.cs.cmu.edu/faqs.php) · [CC0 dedication](LICENSE)
