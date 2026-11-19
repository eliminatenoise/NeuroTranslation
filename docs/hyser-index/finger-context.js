"use strict";

(() => {
  const channels = ["thumb", "index", "middle", "ring", "little"];
  const order = ["index", "thumb", "middle", "ring", "little"];
  const extraDigits = order.slice(1);
  const lags = Array.from({ length: 41 }, (_, i) => i - 40);
  const summaryInputs = ["latest_v", "ols_slope_v_per_tick"];
  const widths = { index_only: 41, aligned_five: 205, aligned_summary: 49 };
  const alphas = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10];
  const slopeDenominator = lags.reduce((sum, lag) => sum + (lag + 20) ** 2, 0);
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  function validWeights(weights) {
    const features = weights?.features;
    if (
      weights?.schema !== "hyser-finger-context-weights-v1" ||
      weights.experiment !== "hyser-random-finger-context-20261119-v1" ||
      !same(features?.input_channel_order, channels) ||
      !same(features?.feature_channel_order, order) ||
      !same(features?.history_lags_ticks, lags) ||
      !same(features?.summary_per_nonindex_channel, summaryInputs) ||
      features?.rate_hz !== 100 ||
      features?.horizon_ticks !== 12 ||
      features?.input_unit !== "V" ||
      features?.target_unit !== "V" ||
      features?.target_channel !== "index" ||
      !same(Object.keys(weights.models ?? {}).sort(), Object.keys(widths).sort())
    )
      return false;
    return Object.entries(widths).every(([key, width]) => {
      const fit = weights.models[key];
      return (
        same(Object.keys(fit ?? {}).sort(), ["alpha", "coef", "intercept", "mean", "scale"]) &&
        alphas.includes(fit.alpha) &&
        Number.isFinite(fit.intercept) &&
        ["mean", "scale", "coef"].every((field) =>
          Array.isArray(fit[field]) && fit[field].length === width && fit[field].every(Number.isFinite),
        ) &&
        fit.scale.every((v) => v > 0)
      );
    });
  }

  function extraHistory(force, issue) {
    return extraDigits.map((digit) => {
      const channel = channels.indexOf(digit);
      return lags.map((lag) => force.voltage(issue + lag, channel));
    });
  }

  function predict(indexHistory, others, weights) {
    const last = indexHistory.at(-1);
    const linear = globalThis.HyserForecast.linear;
    const predictions = { index_only: linear(indexHistory, weights.models.index_only, last) };
    if (!others.every((digit) => digit.every(Number.isFinite))) return predictions;
    const summary = others.flatMap((digit) => [
      digit.at(-1),
      digit.reduce((sum, value, i) => sum + value * (lags[i] + 20), 0) / slopeDenominator,
    ]);
    predictions.aligned_five = linear([...indexHistory, ...others.flat()], weights.models.aligned_five, last);
    predictions.aligned_summary = linear([...indexHistory, ...summary], weights.models.aligned_summary, last);
    return predictions;
  }

  function inventedForce() {
    // Match score_session.py --example --whole-hand --trial 1 (Day 2).
    const sensors = [
      (t) => 0.06 + 0.025 * Math.sin(t * 1.2 + 1),
      (t) => 0.08 + 0.04 * Math.sin(t * (1.05 + 2 / 20) + 0.25) + 0.02 * Math.cos(t * 2.1),
      (t) => 0.07 + 0.031 * Math.sin(t * 1.08 + 0.4),
      (t) => 0.09 + 0.015 * Math.cos(t * 1.4 + 0.2),
      (t) => 0.04 + 0.018 * Math.cos(t * 0.91 + 0.7),
    ];
    return {
      voltage(tick, channel) {
        return sensors[channel](tick / 100);
      },
    };
  }

  async function scoreTrial(force, weights, isCurrent = () => true, { includePersistence = false } = {}) {
    if (!validWeights(weights)) throw new Error("Fitted finger-context models are unavailable.");
    const { first, last, step, windowAt, observationAt, yieldFrame } = globalThis.HyserForecast;
    const scheduled = (last - first) / step + 1;
    const record = { force };
    const arms = includePersistence ? ["persistence", ...Object.keys(widths)] : Object.keys(widths);
    const totals = Object.fromEntries(arms.map((arm) => [arm, { absolute: 0, squared: 0 }]));
    let count = 0;
    let missingHistories = 0;
    let missingTargets = 0;
    for (let i = 0; i < scheduled; i++) {
      if (i % 75 === 0) {
        await yieldFrame();
        if (!isCurrent()) return null;
      }
      const issue = first + i * step;
      const index = windowAt(record, issue, { observe: false, skipMissing: true });
      const others = extraHistory(force, issue);
      const hasHistory = index && others.every((digit) => digit.every(Number.isFinite));
      const target = observationAt(record, issue);
      if (!hasHistory) missingHistories++;
      if (target === null) missingTargets++;
      if (!hasHistory || target === null) continue;
      const forecasts = predict(index.force, others, weights);
      if (includePersistence) forecasts.persistence = index.force.at(-1);
      for (const arm of arms) {
        const error = forecasts[arm] - target;
        totals[arm].absolute += Math.abs(error);
        totals[arm].squared += error ** 2;
      }
      count++;
    }
    // The Python scorer rejects incomplete trials. Never compare a partial trial.
    let models = null;
    if (count === scheduled) {
      models = Object.fromEntries(arms.map((arm) => [arm, {
        maeV: totals[arm].absolute / count,
        rmseV: Math.sqrt(totals[arm].squared / count),
      }]));
      if (Object.values(models).some(({ maeV, rmseV }) => !Number.isFinite(maeV) || !Number.isFinite(rmseV))) {
        throw new Error("The trial has a nonfinite forecast error.");
      }
    }
    return { count, scheduled, missingHistories, missingTargets, models };
  }

  globalThis.HyserFingerContext = { extraDigits, extraHistory, predict, validWeights, inventedForce, scoreTrial };
})();
