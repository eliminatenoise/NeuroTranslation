# Forecast heel movement on a ramp

Extract the paired-plates preview and open a terminal in that folder. With Python 3.9 or newer, run the invented ramp example.

```sh
python3 adaptive_walk.py --mode body-motion --input example-ramp.json
```

On Windows, use `py -3` or `python` in place of `python3`. The program works offline. The example supplies an invented 10° slope. The model uses past positions of both heels and the front of the pelvis to estimate how far each heel will move in the next 100 milliseconds.

## Prepare your own measurements

1. Copy `example-ramp.json`. Enter the XYZ positions in millimetres in one room coordinate system. Use positive X toward the walker's left, positive Y opposite the direction of travel, and positive Z upward. Give the left heel first and the right heel second. For the pelvis, use the midpoint between the two front markers.
2. Set `bin_end_ms` to integer timestamps 20 milliseconds apart. Supply at least ten samples per position series. Use measurements available by each timestamp and leave missing positions as `null`. Both heels and the pelvis need complete positions for the last ten samples. Earlier windows with missing positions are skipped.
3. Set `floor_normal_xyz` to three numbers describing the direction perpendicular to your measured floor. Use the same room axes as the positions and choose the direction that points up. The vector's length does not matter, but its Z component must be positive. Use one measured plane per history. A flat floor has normal `[0, 0, 1]`. Leave out the field to use the ordinary room axes. The option is available only in `body-motion` mode.

Use measured floor geometry from your camera or laboratory calibration to get the normal. Enter the positions in room axes and let the program handle the rotation. It reports heel displacement in the same room axes, in millimetres. It also predicts the chance of a new floor-plate load and the signed force impulse. The impulse adds up predicted force along room up over 100 milliseconds, in newton-seconds. On a ramp, room up and the direction perpendicular to the floor point in different directions.

## What the ramp recordings showed

The comparison used 682 of 695 catalogued walking clips from 12 people. Thirteen clips were excluded before forecasting because the left and right directions in the room could not be confirmed. Participants walked in both directions on level ground and on 7.5° and 10° ramps. Giving the same fitted model the measured floor orientation lowered mean heel displacement error from **38.89 mm to 26.36 mm** across 22,304 scored foot forecasts, with equal weight per person. Mean vertical force-impulse error rose from **13.25 to 13.38 newton-seconds** across 9,763 scored in-contact forecasts. [Ramp recordings by Schreff, Vielemeyer, Müller and Tronicke, CC BY 4.0](https://doi.org/10.6084/m9.figshare.29300888.v1)

The study used archived marker positions on the laboratory's recording clock and three calibrated force plates. Load-start scoring covered the time around confirmed contacts between a foot and its plate. Impulse scoring required the full forecast window to fall within measured contact on one plate. Live camera delay and force beyond the plates remain unverified.
