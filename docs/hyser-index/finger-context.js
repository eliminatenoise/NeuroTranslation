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

  globalThis.HyserFingerContext = { extraDigits, extraHistory, predict, validWeights };
})();
