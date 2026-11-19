"use strict";
(() => {
  const phases = ["initial_rest", "ramp_up", "hold", "release", "final_rest"];
  const phaseNames = ["Initial rest", "Ramp up", "Hold", "Ramp down", "Final rest"];
  const ends = [0, 1000, 2000, 4000, 5000, 6000];
  const phaseKeys = [...phases.map((s) => "phase_" + s), ...phases.map((s) => "phase_age_" + s)];
  const forceKeys = ["force_now", "force_delta_5", "force_delta_10", "force_delta_20", "force_delta_40"];
  const emgKeys = ["emg_older_median", "emg_older_q90", "emg_recent_median", "emg_recent_q90"];
  const layouts = {
    phase: phaseKeys,
    history: forceKeys,
    history_phase: [...forceKeys, ...phaseKeys],
    history_phase_paired_emg: [...forceKeys, ...phaseKeys, ...emgKeys],
  };
  const labels = {
    persistence: "Last force reading",
    phase: "Cue phase",
    history: "Force history",
    history_phase: "Force history and phase",
    history_phase_paired_emg: "Force, phase and forearm EMG",
  };
  const modes = new Set(["nominal_release_index", "force_only"]);
  const equal = (a, b) => Array.isArray(a) && a.length === b.length && a.every((x, i) => x === b[i]);
  const vector = (x, n) => Array.isArray(x) && x.length === n && x.every(Number.isFinite);
  function checkFit(fit) {
    if (
      !fit ||
      fit.format !== "cemhsey-pinch-fit-v1" ||
      !/^[a-f0-9]{64}$/.test(fit.protocol_sha256) ||
      !modes.has(fit.timing_mode) ||
      !fit.models
    )
      throw Error("The bundled fit is unreadable.");
    const names = Object.keys(layouts).filter(
      (k) => k !== "history_phase_paired_emg" || fit.timing_mode === "nominal_release_index",
    );
    if (!equal(Object.keys(fit.models).sort(), names.slice().sort()))
      throw Error("The fitted model list differs from the protocol.");
    for (const k of names) {
      const model = fit.models[k],
        keys = layouts[k];
      if (
        !equal(model?.feature_names, keys) ||
        !vector(model.center, keys.length) ||
        !vector(model.scale, keys.length) ||
        !vector(model.coef, keys.length) ||
        model.scale.some((x) => x <= 0) ||
        !Number.isFinite(model.intercept) ||
        model.add_force_now !== (k !== "phase")
      )
        throw Error("The fitted feature order or coefficients are invalid.");
    }
    return fit;
  }
  function validEmg(x) {
    return vector(x, 4) && x[0] >= 0 && x[0] <= x[1] && x[2] >= 0 && x[2] <= x[3];
  }
  function checkTrial(trial, fit) {
    if (
      trial?.format !== "cemhsey-pinch-trial-v1" ||
      trial.protocol_sha256 !== fit.protocol_sha256 ||
      !modes.has(trial.timing_mode) ||
      !Array.isArray(trial.rows) ||
      trial.rows.length !== 592
    )
      throw Error("Choose a trial packet from the converter for this edition (592 cutoffs).");
    for (let n = 0; n < trial.rows.length; n++) {
      const row = trial.rows[n];
      if (
        row?.issue_tick !== 60 + 10 * n ||
        !Number.isFinite(row.force_now) ||
        !vector(row.force_deltas, 4) ||
        (trial.timing_mode === "force_only"
          ? row.emg_summaries !== null
          : !validEmg(row.emg_summaries)) ||
        (row.measured_target !== null && !Number.isFinite(row.measured_target))
      )
        throw Error(
          "The packet contains a missing, invalid or out-of-order input at cutoff " + (n + 1) + ".",
        );
    }
    return trial;
  }
  function phaseAt(tick) {
    const i = ends.findIndex((end, k) => k > 0 && tick < end) - 1;
    if (i < 0) throw Error("Issue tick outside the trial.");
    const one = phases.map((_, k) => (k === i ? 1 : 0)),
      age = (tick - ends[i]) / (ends[i + 1] - ends[i]);
    return { name: phaseNames[i], features: [...one, ...one.map((active) => active * age)] };
  }
  function forecast(fit, row) {
    const phase = phaseAt(row.issue_tick).features,
      force = [row.force_now, ...row.force_deltas],
      both = [...force, ...phase];
    const inputs = { phase, history: force, history_phase: both };
    if (row.emg_summaries && fit.models.history_phase_paired_emg)
      inputs.history_phase_paired_emg = [...both, ...row.emg_summaries];
    const out = { persistence: row.force_now };
    for (const [key, features] of Object.entries(inputs)) {
      const m = fit.models[key];
      let value = m.intercept;
      for (let j = 0; j < features.length; j++)
        value += (m.coef[j] * (features[j] - m.center[j])) / m.scale[j];
      if (m.add_force_now) value += row.force_now;
      if (!Number.isFinite(value)) throw Error("The inputs exceed the model's numerical range.");
      out[key] = value;
    }
    return out;
  }
  function score(fit, rows) {
    const sums = {};
    for (const row of rows) {
      if (!Number.isFinite(row.measured_target))
        throw Error("Trial scoring requires a measured target at all 592 cutoffs.");
      for (const [key, prediction] of Object.entries(forecast(fit, row))) {
        const e = prediction - row.measured_target;
        const s = sums[key] ?? (sums[key] = { abs: 0, square: 0, count: 0 });
        s.abs += Math.abs(e);
        s.square += e * e;
        s.count++;
      }
    }
    return Object.fromEntries(
      Object.entries(sums).map(([key, s]) => {
        if (s.count !== rows.length || !Number.isFinite(s.square) || !Number.isFinite(s.abs))
          throw Error("Trial scores require the same valid cutoffs throughout.");
        return [key, { mae: s.abs / s.count, rmse: Math.sqrt(s.square / s.count) }];
      }),
    );
  }
  function invented(fit) {
    function force(tick) {
      const t = tick / 200;
      const cue = t < 5 ? 0 : t < 10 ? (t - 5) / 5 : t < 20 ? 1 : t < 25 ? (25 - t) / 5 : 0;
      return 0.018 + 0.29 * cue + 0.008 * Math.sin(t * 4.2) + 0.003 * Math.cos(t * 10.7);
    }
    const withEmg = fit.timing_mode === "nominal_release_index";
    function amplitude(second) {
      const a = 0.027 + 0.4 * Math.abs(force(Math.round(second * 200)));
      return [Math.log1p(a), Math.log1p(1.7 * a)];
    }
    const rows = Array.from({ length: 592 }, (_, i) => {
      const t = 60 + 10 * i;
      return {
        issue_tick: t,
        force_now: force(t),
        force_deltas: [5, 10, 20, 40].map((k) => force(t) - force(t - k)),
        emg_summaries: withEmg ? [...amplitude(t / 200 - 0.25), ...amplitude(t / 200 - 0.15)] : null,
        measured_target: force(t + 24),
      };
    });
    return {
      format: "cemhsey-pinch-trial-v1",
      protocol_sha256: fit.protocol_sha256,
      timing_mode: fit.timing_mode,
      rows,
    };
  }
  globalThis.PinchForecast = { checkFit, checkTrial, phaseAt, forecast, score, invented, labels };
})();
