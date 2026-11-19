/* A recorded lift supplies 29 cue-relative histories and separately stored outcomes. */
"use strict";
const GripReplay = (() => {
  const FIRST = 120, LAST = 680, STEP = 20, MAIN = 200, MUSCLE = 1600;
  const ISSUES = Array.from({ length: 29 }, (_, i) => FIRST + i * STEP);
  const format = "way-grip-trial-v1";
  const fields = ["format", "series_type", "trial_number", "main_s", "emg_s", "grip_n",
    "load_n", "position", "eeg", "emg", "later_grip_n", "later_time_s"];
  function check(ok, message) {
    if (!ok) throw new Error(message);
  }
  function lastAt(clock, time) {
    let low = 0, high = clock.length;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (clock[mid] <= time + 1e-10) low = mid + 1;
      else high = mid;
    }
    return low - 1;
  }
  function read(trial, predict) {
    check(trial?.format === format && Object.keys(trial).length === fields.length
      && fields.every(key => Object.hasOwn(trial, key)), "Use the complete way-grip-trial-v1 trial format.");
    const mainCount = LAST - FIRST + MAIN;
    for (const key of ["main_s", "grip_n", "load_n", "position", "eeg"]) {
      check(Array.isArray(trial[key]) && trial[key].length === mainCount, key + " must span all 29 cutoffs.");
    }
    check(Array.isArray(trial.emg_s) && Array.isArray(trial.emg)
      && Math.abs(trial.emg_s.length - (MUSCLE + (LAST - FIRST) * 8)) <= 1
      && trial.emg.length === trial.emg_s.length, "The trial needs the full 4 kHz EMG history.");
    check(["later_time_s","later_grip_n"].every(key => Array.isArray(trial[key])
      && trial[key].length === ISSUES.length && trial[key].every(Number.isFinite)),
      "Supply one finite reference time and grip force for every cutoff.");
    function windowAt(issue) {
      check(ISSUES.includes(issue), "Choose a scheduled cutoff.");
      const start = issue - FIRST, stop = start + MAIN;
      const cutoff = trial.main_s[stop - 1];
      const emgStop = lastAt(trial.emg_s, cutoff) + 1, emgStart = emgStop - MUSCLE;
      check(emgStart >= 0 && Math.abs(cutoff - issue / 500) < 1e-8, "The source clock does not cover this cutoff.");
      return {
        format: "way-grip-window-v1", issue_offset: issue, series_type: trial.series_type, trial_number: trial.trial_number,
        time_from_cutoff_s: { main: trial.main_s.slice(start, stop).map(t => t - cutoff),
          emg: trial.emg_s.slice(emgStart, emgStop).map(t => t - cutoff) },
        grip_n: trial.grip_n.slice(start, stop), load_n: trial.load_n.slice(start, stop),
        position: trial.position.slice(start, stop), eeg: trial.eeg.slice(start, stop), emg: trial.emg.slice(emgStart, emgStop),
      };
    }
    const predictions = new Map();
    for (const [i, issue] of ISSUES.entries()) {
      // The predictor validates every past sample. Reject an unscorable trial before replacing the prior display.
      predictions.set(issue, predict(windowAt(issue)));
      check(Math.abs(trial.later_time_s[i] - (issue + 60) / 500) < 1e-8,
        "A reference timestamp does not fall 120 ms after its cutoff.");
    }
    return { windowAt, scoresAt: issue => predictions.get(issue), outcome: issue => trial.later_grip_n[(issue - FIRST) / STEP] };
  }
  function invented(predict) {
    // Make overlapping windows contiguous by appending only newly observed samples.
    const seed = GripForecast.synthetic(FIRST);
    const trial = {format, series_type: seed.series_type, trial_number: seed.trial_number,
      main_s: [], emg_s: [], grip_n: [], load_n: [], position: [], eeg: [], emg: [], later_grip_n: [], later_time_s: []};
    for (const issue of ISSUES) {
      const w = GripForecast.synthetic(issue), start = issue === FIRST ? 0 : MAIN - STEP;
      const mStart = issue === FIRST ? 0 : MUSCLE - STEP * 8;
      const time = issue / 500;
      trial.main_s.push(...w.time_from_cutoff_s.main.slice(start).map(t => time + t));
      trial.emg_s.push(...w.time_from_cutoff_s.emg.slice(mStart).map(t => time + t));
      for (const key of ["grip_n", "load_n", "position", "eeg"]) trial[key].push(...w[key].slice(start));
      trial.emg.push(...w.emg.slice(mStart));
      trial.later_time_s.push(time + 0.12);
      trial.later_grip_n.push(GripForecast.synthetic(issue + 60).grip_n.at(-1));
    }
    return read(trial, predict);
  }
  return { format, read, invented };
})();
