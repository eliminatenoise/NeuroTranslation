"use strict";
(() => {
  const {cueLevel} = PinchTransfer;
  const {nIssues, horizon, cache, phaseAt, phases} = PinchIntervals;
  const protocol = "e8d7cd2cb14e5546d42a07ea38aed134b456ab75a284e7e12bd3b5a09dbf8640";
  const parents = ["persistence_plus_cue_change", "history_phase", "history_phase_paired_grid"];
  const parentNames = ["Current force + cue change", "Force history + cue", "Force history + cue + five EMG grids"];
  const versions = ["unchanged", "pooled", "split"];
  const versionNames = ["Unchanged", "One gain", "Rise and fall gains"];
  const arms = ["persistence", "scheduled_cue", ...parents.flatMap(key => versions.map(mode => key + "_" + mode))];
  const names = Object.fromEntries(arms.map((key, i) => [key, i === 0 ? "Current force" : i === 1 ? "Scheduled target" :
    parentNames[Math.floor((i - 2) / 3)] + " · " + versionNames[(i - 2) % 3]]));
  const blank = keys => Object.fromEntries(keys.map(key => [key, 0]));
  const directions = ["pooled", "rise", "fall"];
  const pause = () => new Promise(resolve => setTimeout(resolve, 0));
  function base(frozen, tick) {
    const future = cueLevel(tick + horizon);
    const u = future - cueLevel(tick);
    return {u, persistence: frozen.persistence, scheduled_cue: .5 * future,
      persistence_plus_cue_change: frozen.persistence + .5 * u,
      history_phase: frozen.history_phase + (.5 - .3) * u,
      history_phase_paired_grid: frozen.history_phase_paired_grid + (.5 - .3) * u};
  }
  function newFit() {
    return {den: blank(directions), num: Object.fromEntries(parents.map(key => [key, blank(directions)])), n: 0};
  }
  function add(fit, row, actual) {
    fit.n++;
    const u = row.u;
    if (u === 0) return;
    for (const dir of ["pooled", u > 0 ? "rise" : "fall"]) {
      fit.den[dir] += u * u;
      for (const key of parents) fit.num[key][dir] += u * (actual - row[key]);
    }
  }
  function finish(fit) {
    if (fit.n !== 6 * nIssues) throw Error("Fit both repeats from each of three people.");
    const gains = {};
    for (const key of parents) {
      gains[key] = {};
      for (const dir of directions) {
        const gain = fit.num[key][dir] / fit.den[dir];
        if (!Number.isFinite(gain)) throw Error("A gain exceeds the numerical range.");
        gains[key][dir] = gain;
      }
    }
    return gains;
  }
  function predict(row, gains) {
    const point = {persistence: row.persistence, scheduled_cue: row.scheduled_cue};
    for (const key of parents) {
      point[key + "_unchanged"] = row[key];
      point[key + "_pooled"] = row[key] + row.u * gains[key].pooled;
      point[key + "_split"] = row.u === 0 ? row[key] : row[key] + row.u * gains[key][row.u > 0 ? "rise" : "fall"];
    }
    if (!Object.values(point).every(Number.isFinite)) throw Error("The forecast exceeds the numerical range.");
    return point;
  }
  async function fitTrial(fit, trial, model, check) {
    const read = cache(trial, model);
    for (let i = 0; i < nIssues; i++) {
      if (i % 64 === 0) { await pause(); check(); }
      const {estimates, tick} = read(i);
      add(fit, base(estimates, tick), trial.force[tick + horizon]);
    }
  }
  function forecaster(trial, model, gains) {
    const read = cache(trial, model);
    return i => {
      const {estimates, tick} = read(i);
      const row = base(estimates, tick);
      return {tick, u: row.u, points: predict(row, gains)};
    };
  }
  async function score(trial, forecast, check) {
    const totals = Object.fromEntries(["overall", ...phases].map(phase => [phase, {
      n: 0, rows: Object.fromEntries(arms.map(key => [key, {abs: 0, sq: 0, signed: 0}]))
    }]));
    for (let i = 0; i < nIssues; i++) {
      if (i % 64 === 0) { await pause(); check(); }
      const {tick, points} = forecast(i);
      const actual = trial.force[tick + horizon];
      for (const group of [totals.overall, totals[phaseAt(tick)]]) {
        group.n++;
        for (const key of arms) {
          const error = points[key] - actual, row = group.rows[key];
          row.abs += Math.abs(error);
          row.sq += error * error;
          row.signed += error;
        }
      }
    }
    for (const group of Object.values(totals)) {
      for (const [key, row] of Object.entries(group.rows)) {
        const mae = row.abs / group.n;
        const metrics = {mae, rmse: Math.sqrt(row.sq / group.n), bias: row.signed / group.n, relative: mae / .5};
        if (!Object.values(metrics).every(Number.isFinite)) throw Error("The trial errors exceed the numerical range.");
        group.rows[key] = metrics;
      }
    }
    return totals;
  }
  function example(seed, person, repeat) {
    const {force, rms} = seed;
    const delay = 5 + person * 2 + repeat * 3;
    const forceOut = force.map((v, i) => {
      const directionDelay = i < 3000 ? delay : 3 * delay;
      return v - .29 * cueLevel(i) + (.47 + .004 * person) * cueLevel(i - directionDelay) +
        .008 * Math.sin(i / 83 + repeat + person * .7) * cueLevel(i);
    });
    const rmsOut = rms.map((v, i) => v * (1 + (.06 * person + .03 * repeat) * cueLevel((Math.floor(i / 320) + 1) * 10)));
    return {force: forceOut, rms: rmsOut};
  }
  globalThis.PinchPhase = Object.freeze({protocol, parents, parentNames, directions, arms, names, versions,
    base, newFit, add, finish, predict, fitTrial, forecaster, score, example});
})();
