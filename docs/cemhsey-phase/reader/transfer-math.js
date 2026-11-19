"use strict";

(() => {
  const parents = ["history_phase", "history_phase_paired_grid"];
  const controls = ["persistence", "scheduled_cue", "persistence_plus_cue_change"];
  const arms = [...controls, ...parents.flatMap(parent =>
    ["frozen", "adjusted", "adapted"].map(mode => parent + "_" + mode))];
  const labels = Object.fromEntries(arms.map((arm, i) => [arm, [
    "Last force reading", "Scheduled cue at target time", "Last force + scheduled change",
    "Force history and cue · frozen", "Force history and cue · adjusted", "Force history and cue · adapted",
    "Five-grid model · frozen", "Five-grid model · adjusted", "Five-grid model · adapted"
  ][i]]));
  const carryArms = [...controls, ...parents.flatMap(parent =>
    ["frozen", "adjusted", "carried", "adapted"].map(mode => parent + "_" + mode))];
  labels.history_phase_carried = "Force history and cue · day 9 practice";
  labels.history_phase_paired_grid_carried = "Five-grid model · day 9 practice";
  function label(arm, withCarry) {
    if (withCarry && arm.endsWith("_adapted")) return labels[arm].replace("adapted", "day 10 practice");
    return labels[arm];
  }
  const {horizon, nIssues, cache} = globalThis.PinchIntervals;

  function cueLevel(tick) {
    if (tick <= 1000 || tick >= 5000) return 0;
    if (tick < 2000) return (tick - 1000) / 1000;
    if (tick <= 4000) return 1;
    return (5000 - tick) / 1000;
  }

  function estimates(frozen, tick, q, coefficients = null, prior = null) {
    if (![.1, .3, .5].includes(q)) throw Error("Choose a prescribed target of 10%, 30% or 50%.");
    const future = cueLevel(tick + horizon);
    const u = future - cueLevel(tick);
    const point = {
      persistence: frozen.persistence,
      scheduled_cue: q * future,
      persistence_plus_cue_change: frozen.persistence + q * u
    };
    for (const parent of parents) {
      point[parent + "_frozen"] = frozen[parent];
      point[parent + "_adjusted"] = frozen[parent] + (q - .3) * u;
      if (prior) point[parent + "_carried"] = point[parent + "_adjusted"] + prior[parent] * u;
      if (coefficients) point[parent + "_adapted"] = point[parent + "_adjusted"] + coefficients[parent] * u;
    }
    if (!Object.values(point).every(Number.isFinite)) throw Error("Forecasts exceed the numerical range.");
    return point;
  }

  function newAdapter() {
    return {sumSquares: 0, numerator: Object.fromEntries(parents.map(parent => [parent, 0]))};
  }

  function addAdapterSample(adapter, frozen, tick, q, actual) {
    const u = cueLevel(tick + horizon) - cueLevel(tick);
    const point = estimates(frozen, tick, q);
    adapter.sumSquares += u * u;
    for (const parent of parents) adapter.numerator[parent] += u * (actual - point[parent + "_adjusted"]);
  }

  function finishAdapter(adapter) {
    if (!(adapter.sumSquares > 0)) throw Error("The practice trial needs cutoffs where the cue changes.");
    const coefficients = Object.fromEntries(parents.map(parent => [parent, adapter.numerator[parent] / adapter.sumSquares]));
    if (!Object.values(coefficients).every(Number.isFinite)) throw Error("The practice fit exceeds the numerical range.");
    return coefficients;
  }

  function newScores(withCarry = false) {
    return Object.fromEntries((withCarry ? carryArms : arms).map(key => [key, {n: 0, abs: 0, square: 0, signed: 0}]));
  }

  function addScore(scores, predictions, actual) {
    for (const [key, prediction] of Object.entries(predictions)) {
      const total = scores[key];
      const error = prediction - actual;
      total.n += 1;
      total.abs += Math.abs(error);
      total.square += error * error;
      total.signed += error;
    }
  }

  function finishScores(scores, q) {
    return Object.fromEntries(Object.entries(scores).filter(([, count]) => count.n).map(([arm, total]) => {
      const mae = total.abs / total.n;
      const metrics = {mae, rmse: Math.sqrt(total.square / total.n), bias: total.signed / total.n, target_relative_mae: mae / q};
      if (!Object.values(metrics).every(Number.isFinite)) throw Error("Trial errors exceed the numerical range.");
      return [arm, metrics];
    }));
  }

  function fromExample(base, q, repeat, day = 10) {
    const force = base.force.map((value, tick) => {
      const delay = (repeat === 1 ? 12 : 17) + (day === 9 ? 6 : 0);
      const t = tick / 200;
      return value - .29 * cueLevel(tick) + q * (day === 9 ? .91 : .96) * cueLevel(tick - delay) +
        (repeat === 1 ? .009 : .013) * Math.sin(t * 3.2 + repeat) * cueLevel(tick);
    });
    const rms = base.rms.map((value, offset) => {
      const g = cueLevel((Math.floor(offset / 320) + 1) * 10);
      return value * (1 + (q - .3) * g) * (1 + ((repeat - 1) * .025 + (day === 9 ? .04 : 0)) * g);
    });
    return {force, rms};
  }

  globalThis.PinchTransfer = Object.freeze({
    parents, arms, carryArms, labels, label, horizon, nIssues, cache, cueLevel, estimates,
    newAdapter, addAdapterSample, finishAdapter, newScores, addScore, finishScores, fromExample
  });
})();
