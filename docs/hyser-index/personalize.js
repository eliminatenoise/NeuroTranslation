"use strict";
(() => {
  const forecast = globalThis.HyserForecast;
  const arms = ["force", "aligned"];
  const windowsPerTrial = (forecast.last - forecast.first) / forecast.step + 1;
  const dayOneTrialCount = 5;
  const ridge = 0.1;
  const minScaleV = 1e-12;

  function identifySession(entries) {
    const parents = new Set();
    for (const { files } of entries) {
      for (const file of Object.values(files)) {
        const parts = (file.webkitRelativePath || "").split("/");
        if (parts.pop() !== file.name || !parts.length) return null;
        parents.add(parts.join("/"));
      }
    }
    if (parents.size !== 1) return null;
    const folder = Array.from(parents)[0].split("/").at(-1);
    const match = /^subject(0[1-9]|1[0-9]|20)_session([12])$/.exec(folder);
    return match ? { subject: match[1], day: Number(match[2]), folder } : null;
  }

  function pairProblem(dayOne, dayTwo) {
    if (!dayOne || !dayTwo) {
      return "Choose both original session folders. The browser needs their subject and session labels.";
    }
    if (dayOne.day !== 1 || dayTwo.day !== 2) {
      return "Put session1 in the Day 1 picker and session2 in the Day 2 picker.";
    }
    if (dayOne.subject !== dayTwo.subject) {
      return "These folders name different Hyser participants. Choose both sessions for the same participant.";
    }
    return "";
  }

  function fit(rows) {
    if (!rows.length) throw new Error("Day 1 supplied no calibration windows.");
    let sumChangeSquared = 0;
    for (const { currentV, pooledV, targetV } of rows) {
      if (![currentV, pooledV, targetV].every(Number.isFinite)) {
        throw new Error("Day 1 voltage values could not produce a finite calibration.");
      }
      const change = pooledV - currentV;
      sumChangeSquared += change * change;
    }
    const scale = Math.max(minScaleV, Math.sqrt(sumChangeSquared / rows.length));
    let sumQ = 0, sumQSquared = 0, sumError = 0, sumQError = 0;
    for (const { currentV, pooledV, targetV } of rows) {
      const q = (pooledV - currentV) / scale;
      const error = targetV - pooledV;
      sumQ += q;
      sumQSquared += q * q;
      sumError += error;
      sumQError += q * error;
    }
    const a = 1 + ridge;
    const b = sumQ / rows.length;
    const c = sumQSquared / rows.length + ridge;
    const e = sumError / rows.length;
    const f = sumQError / rows.length;
    const determinant = a * c - b * b;
    const offsetV = (c * e - b * f) / determinant;
    const slope = (a * f - b * e) / determinant / scale;
    if (!Number.isFinite(scale) || !Number.isFinite(offsetV) || !Number.isFinite(slope)) {
      throw new Error("Day 1 voltage values could not produce a finite calibration.");
    }
    return Object.freeze({ offsetV, slope });
  }

  function apply(currentV, pooledV, { offsetV, slope }) {
    const adapted = pooledV + offsetV + slope * (pooledV - currentV);
    if (!Number.isFinite(adapted)) throw new Error("The personalized forecast is outside the numeric range.");
    return adapted;
  }

  async function calibrate(loadDayOneTrial, useEmg, weights, isCurrent, progress) {
    const rows = { force: [], aligned: [] };
    for (let trial = 1; trial <= dayOneTrialCount; trial++) {
      progress(trial);
      const source = await loadDayOneTrial(trial, isCurrent);
      if (!isCurrent()) return null;
      const record = { force: source.force, raw: useEmg ? source.raw : null };
      const emgAt = await forecast.batchedEmg(record.raw, isCurrent);
      if (!isCurrent()) return null;
      for (let issue = forecast.first; issue <= forecast.last; issue += forecast.step) {
        const row = forecast.windowAt(record, issue, { emgAt, skipMissing: true });
        if (!row) {
          throw new Error("Day 1 trial " + trial + " is missing a force sample required for calibration.");
        }
        if (row.observed === null) {
          throw new Error("Day 1 trial " + trial + " is missing a later voltage required for calibration.");
        }
        const predictions = forecast.predict(row, weights);
        const currentV = predictions.persistence;
        const targetV = row.observed;
        rows.force.push({ currentV, pooledV: predictions.force, targetV });
        if (predictions.aligned !== undefined) {
          rows.aligned.push({ currentV, pooledV: predictions.aligned, targetV });
        }
      }
      await forecast.yieldFrame();
      if (!isCurrent()) return null;
    }
    const fits = { force: fit(rows.force) };
    if (useEmg && rows.aligned.length === rows.force.length) fits.aligned = fit(rows.aligned);
    return Object.freeze({
      fits: Object.freeze(fits),
      count: rows.force.length,
      emgIssue: !useEmg ? "Day 1 needs all five raw EMG pairs to personalize the EMG forecast."
        : !fits.aligned ? "Day 1 has missing EMG windows. Only the force forecast was personalized." : "",
    });
  }

  async function scoreTrial(record, { fits }, weights, isCurrent) {
    const score = {};
    const emgAt = fits.aligned ? await forecast.batchedEmg(record.raw, isCurrent) : undefined;
    if (!isCurrent()) return null;
    const applicable = record.raw && fits.aligned ? arms : ["force"];
    const finalRecord = { force: record.force, raw: emgAt ? record.raw : null };
    for (const arm of applicable) {
      score[arm] = { count: 0, baseAbs: 0, ownAbs: 0, baseSq: 0, ownSq: 0 };
    }
    for (let issue = forecast.first; issue <= forecast.last; issue += forecast.step) {
      const row = forecast.windowAt(finalRecord, issue, { emgAt, skipMissing: true });
      if (!row || row.observed === null) continue;
      const predictions = forecast.predict(row, weights);
      for (const arm of applicable) {
        const base = predictions[arm];
        if (base === undefined) continue;
        const adapted = apply(predictions.persistence, base, fits[arm]);
        const metrics = score[arm];
        const baseError = base - row.observed;
        const ownError = adapted - row.observed;
        metrics.count++;
        metrics.baseAbs += Math.abs(baseError);
        metrics.ownAbs += Math.abs(ownError);
        metrics.baseSq += baseError * baseError;
        metrics.ownSq += ownError * ownError;
      }
    }
    for (const metrics of Object.values(score)) {
      if (!metrics.count) continue;
      metrics.baseMae = metrics.baseAbs / metrics.count;
      metrics.ownMae = metrics.ownAbs / metrics.count;
      metrics.baseRmse = Math.sqrt(metrics.baseSq / metrics.count);
      metrics.ownRmse = Math.sqrt(metrics.ownSq / metrics.count);
      if (![metrics.baseMae, metrics.ownMae, metrics.baseRmse, metrics.ownRmse].every(Number.isFinite)) {
        throw new Error("Day 2 voltage errors are outside the numeric range.");
      }
    }
    return score;
  }

  globalThis.HyserPersonalize = {
    identifySession, pairProblem, fit, apply, calibrate, scoreTrial,
    windowsPerTrial, dayOneTrialCount,
  };
})();
