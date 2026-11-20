"""Check half-open event boundaries, past-only mechanics and native finite masks."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from prepare import TrialError, trial_windows


def construct():
    origin = 8.46
    tm = origin + np.arange(441) / 2000
    tv = origin + np.arange(4401) / 20000
    e = tv[[0, 1999, 2000, 2399, 2400, 4400]]  # Includes first history and target edges, and final observed endpoint.
    isi = np.diff(e)
    return SimpleNamespace(time=tm, time_PotMem=tv, Force=tm*2, Length=-tm*3,
                           PotMem=tv.copy(), spiketimes=e, ISI=isi, firing_rate=1/isi)


def run(rec):
    data = dict(afferent="fixture", trial=1, prefix=0, trial_type="triangle_series")
    return trial_windows(rec, data, Path("."))


def main():
    r = construct()
    rows, bins = run(r)
    np.testing.assert_array_equal(rows["bin_index"], np.arange(5,11))
    np.testing.assert_array_equal(rows["X"][0, :, 4], [1,0,0,0,1])
    np.testing.assert_array_equal(rows["y_count"], [2,1,0,0,0,0])
    np.testing.assert_allclose(rows["y_delta"], np.tile([.04,-.06],(6,1)), atol=1e-12)
    np.testing.assert_allclose(rows["X"][:,:,2], 2, atol=1e-12)
    np.testing.assert_allclose(rows["X"][:,:,3], -3, atol=1e-12)
    np.testing.assert_allclose(rows["cutoff_s"][0], r.time[200])
    assert bins["count"].sum() == len(r.spiketimes)-1
    # Alter future mechanics and final event positions without changing first prediction's inputs.
    r.Force[200:] += 3
    r.spiketimes[2] += .0201
    r.spiketimes.sort()
    r.ISI = np.diff(r.spiketimes)
    r.firing_rate = 1/r.ISI
    alt, _ = run(r)
    np.testing.assert_array_equal(rows["X"][0], alt["X"][0])
    np.testing.assert_array_equal(rows["mech_mean"][0], alt["mech_mean"][0])
    assert alt["y_count"][0] == 1
    assert np.isclose(alt["y_delta"][0,0] - rows["y_delta"][0,0], 3)
    # Reject missing explicit electrical clocks and mask every window involving a bad sample.
    r = construct()
    r.PotMem[2000] = np.nan
    alt, m = run(r)
    assert not m["valid"][5] and not len(alt["X"])
    del r.time_PotMem
    try:
        run(r)
    except TrialError as e:
        assert "time_PotMem" in str(e)
    else:
        raise AssertionError("Missing electrical clock admitted")
    print("Passed boundary, signed units, exact support, target isolation, finite-mask and clock checks.")


if __name__ == "__main__":
    main()
