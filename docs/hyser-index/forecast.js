"use strict";
(() => {
  const first = 140,
    last = 2385,
    step = 5;
  const ceiling = (forceTick) => Math.ceil((forceTick * 512) / 25);
  const yieldFrame = () => new Promise((resolve) => setTimeout(resolve, 0));
  function observationAt(record, issue) {
    const value = record.force.voltage(issue + 12, 1);
    return Number.isFinite(value) ? value : null;
  }
  function logRms(sum, frames) {
    const n = frames * 64;
    return [...sum, sum.reduce((a, b) => a + b) / 4].map((power) =>
      Math.log(Math.max(1e-12, Math.sqrt(power / n))),
    );
  }
  function windowAt(record, issue, { observe = true, emgAt, skipMissing = false } = {}) {
    if (
      !Number.isInteger(issue) ||
      issue < first ||
      issue > last ||
      (issue - first) % step
    )
      throw new Error(
        "Select a scheduled cutoff between 1.40 and 23.85 seconds.",
      );
    const force = Array.from({ length: 41 }, (_, i) =>
      record.force.voltage(issue - 40 + i, 1),
    );
    if (!force.every(Number.isFinite)) {
      if (skipMissing) return null;
      throw new Error("The force history has missing samples at this cutoff.");
    }
    let emg = null;
    if (emgAt) {
      emg = emgAt(issue);
    } else if (record.raw) {
      const features = [];
      for (let bin = 0; bin < 4; bin++) {
        const begin = ceiling(issue - 42 + 10 * bin),
          end = ceiling(issue - 32 + 10 * bin);
        const sum = [0, 0, 0, 0];
        for (let frame = begin; frame < end; frame++) {
          for (let c = 0; c < 256; c++) {
            const v = record.raw.voltage(frame, c);
            sum[Math.floor(c / 64)] += v * v;
          }
        }
        features.push(...logRms(sum, end - begin));
      }
      if (features.every(Number.isFinite)) emg = features;
    }
    return {
      issue,
      force,
      emg,
      observed: observe ? observationAt(record, issue) : null,
    };
  }
  // Reuse 10 ms power blocks for a sweep of overlapping 100 ms EMG bins.
  // Each block uses the same half-open frame bounds as a single forecast.
  async function batchedEmg(raw, isCurrent) {
    if (!raw) return undefined;
    const start = first - 42;
    const end = last - 2;
    const powers = new Float64Array((end - start) * 4);
    for (let tick = start; tick < end; tick++) {
      const begin = ceiling(tick);
      const stop = ceiling(tick + 1);
      const offset = (tick - start) * 4;
      for (let frame = begin; frame < stop; frame++) {
        for (let c = 0; c < 256; c++) {
          const voltage = raw.voltage(frame, c);
          powers[offset + (c >> 6)] += voltage * voltage;
        }
      }
      if ((tick - start + 1) % 96 === 0) {
        await yieldFrame();
        if (!isCurrent()) return undefined;
      }
    }
    return (issue) => {
      const features = [];
      for (let bin = 0; bin < 4; bin++) {
        const begin = issue - 42 + 10 * bin;
        const sum = [0, 0, 0, 0];
        for (let tick = begin; tick < begin + 10; tick++) {
          const offset = (tick - start) * 4;
          for (let grid = 0; grid < 4; grid++) sum[grid] += powers[offset + grid];
        }
        features.push(...logRms(sum, ceiling(begin + 10) - ceiling(begin)));
      }
      return features.every(Number.isFinite) ? features : null;
    };
  }
  function validFit(weights) {
    const features = weights?.features;
    if (
      weights?.schema !== "hyser-index-release-voltage-weights-v1" ||
      weights.experiment !== "hyser-random-index-20261119-v1" ||
      features?.force_rate_hz !== 100 ||
      features?.emg_rate_hz !== 2048 ||
      features?.prediction_horizon_force_ticks !== 12 ||
      features?.force_history_unit !== "V" ||
      features?.target_unit !== "V" ||
      features?.emg_rms_floor_v !== 1e-12 ||
      JSON.stringify(features?.force_lags_ticks_ordered) !==
        JSON.stringify(Array.from({ length: 41 }, (_, i) => i - 40)) ||
      JSON.stringify(features?.aligned_emg_bin_boundaries_ticks) !==
        "[-42,-32,-22,-12,-2]" ||
      JSON.stringify(features?.emg_channel_groups_zero_based_half_open) !==
        "[[0,64],[64,128],[128,192],[192,256],[0,256]]"
    )
      return false;
    return [
      ["force", 41],
      ["aligned", 61],
    ].every(([arm, width]) => {
      const fit = weights.models?.[arm];
      return (
        fit &&
        Number.isFinite(fit.intercept) &&
        ["coef", "mean", "scale"].every(
          (key) =>
            Array.isArray(fit[key]) &&
            fit[key].length === width &&
            fit[key].every(Number.isFinite),
        ) &&
        fit.scale.every((value) => value > 0)
      );
    });
  }
  function linear(input, model, lastVoltage) {
    if (
      !model ||
      !Array.isArray(model.coef) ||
      model.coef.length !== input.length ||
      model.mean.length !== input.length ||
      model.scale.length !== input.length
    )
      throw new Error("Model weights do not match the input features.");
    const change = input.reduce(
      (acc, v, i) =>
        acc + ((v - model.mean[i]) / model.scale[i]) * model.coef[i],
      model.intercept,
    );
    const prediction = lastVoltage + change;
    if (!Number.isFinite(prediction))
      throw new Error("The selected model cannot produce a finite forecast.");
    return prediction;
  }
  function predict(row, weights) {
    const v = row.force.at(-1);
    const result = {
      force: linear(row.force, weights.models.force, v),
      persistence: v,
    };
    if (row.emg)
      result.aligned = linear(
        [...row.force, ...row.emg],
        weights.models.aligned,
        v,
      );
    return result;
  }
  function invented(variant = 0) {
    return {
      force: {
        voltage(i) {
          return (
            0.11 +
            (0.035 + 0.0018 * variant) * Math.sin(i / 56 + 0.17 * variant) +
            0.026 * Math.sin(i / 21.3 + 0.3 * variant) +
            0.012 * Math.cos(i / 9.8 + 0.1 * variant)
          );
        },
      },
      raw: {
        voltage(i, c) {
          const envelope = 0.00032 * (0.7 + 0.22 * Math.sin(i / 900 + c / 58));
          return (
            envelope *
            (Math.sin(i * (0.141 + c / 13000) + c * 0.16) +
              0.35 * Math.cos(i * 0.65 + c / 6))
          );
        },
      },
    };
  }
  globalThis.HyserForecast = {
    first,
    last,
    step,
    windowAt,
    observationAt,
    batchedEmg,
    yieldFrame,
    predict,
    invented,
    linear,
    validFit,
  };
})();
