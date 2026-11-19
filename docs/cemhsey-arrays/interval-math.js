"use strict";

(() => {
  const protocol = "44bc615272587c66b90a10be4208168501539d0ab3eb10a929040a80a3848082";
  const format = "cemhsey-pinch-interval-profile-v1";
  const phaseEdges = [0, 1000, 2000, 4000, 5000, 6000];
  const phases = ["initial_rest", "ramp_up", "hold", "release", "final_rest"];
  const issuesPerPhase = [94, 100, 200, 100, 98];
  const nIssues = 592;
  const horizon = 24;
  const models = ["persistence", "history_phase", "history_phase_paired_grid"];
  const schemes = ["pooled", "by_issue_phase"];
  const origins = {
    invented_signals: "Invented calibration trials",
    measured_cal_local: "Separate study calibration panel",
    user_supplied_local: "Your selected calibration packets"
  };
  const api = globalThis.ArrayPinch;
  const sha256 = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
  const fields = (object, keys) => object && typeof object === "object" &&
    !Array.isArray(object) && Object.keys(object).length === keys.length &&
    keys.every(key => Object.hasOwn(object, key));
  const finiteRadius = n => Number.isFinite(n) && n >= 0 && Number.isFinite(2 * n);

  function phaseAt(tick) {
    return phases[phaseEdges.findIndex((edge, index) => index > 0 && tick < edge) - 1];
  }

  async function digest(bytes) {
    if (!globalThis.crypto?.subtle) throw Error("This browser can’t verify calibration files from this address.");
    return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
      byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function validate(profile) {
    const keys = ["format", "reader_fit_sha256", "protocol_sha256", "timing_mode",
      "profile_origin", "nominal_coverage", "pooled_count", "phase_counts", "half_widths"];
    const tracksCalibration = profile?.profile_origin === "user_supplied_local" &&
      Object.hasOwn(profile, "calibration_packet_sha256");
    if (tracksCalibration) keys.push("calibration_packet_sha256");
    if (!fields(profile, keys) || profile.format !== format || !sha256(profile.reader_fit_sha256) ||
      profile.protocol_sha256 !== protocol || profile.timing_mode !== "nominal_release_index" ||
      profile.nominal_coverage !== 0.9 || !Object.hasOwn(origins, profile.profile_origin)) {
      throw Error("Choose a 90% profile made for this calibration protocol.");
    }
    const nTrials = profile.pooled_count / nIssues;
    if (!Number.isSafeInteger(profile.pooled_count) || !Number.isInteger(nTrials) || nTrials < 1 ||
      (profile.profile_origin !== "user_supplied_local" && nTrials !== 8) ||
      !fields(profile.phase_counts, phases) ||
      !phases.every((phase, index) => profile.phase_counts[phase] === nTrials * issuesPerPhase[index]) ||
      !fields(profile.half_widths, models)) {
      throw Error("The profile’s model list or calibration counts are inconsistent.");
    }
    if (tracksCalibration) {
      const members = profile.calibration_packet_sha256;
      if (!Array.isArray(members) || members.length !== nTrials ||
        !members.every(sha256) || new Set(members).size !== nTrials) {
        throw Error("The profile needs one unique packet fingerprint for each calibration trial.");
      }
    }
    for (const radii of Object.values(profile.half_widths)) {
      if (!fields(radii, schemes) || !finiteRadius(radii.pooled) ||
        !fields(radii.by_issue_phase, phases) || !Object.values(radii.by_issue_phase).every(finiteRadius)) {
        throw Error("The profile has invalid band widths.");
      }
    }
    return profile;
  }

  function matches(profile, fit, identity) {
    return Boolean(identity && profile.reader_fit_sha256 === identity && (
      profile.profile_origin === "user_supplied_local" ||
      (profile.profile_origin === "invented_signals" && fit.fit_origin === "invented_signals") ||
      (profile.profile_origin === "measured_cal_local" && fit.fit_origin === "measured_train_local")));
  }

  function compatibleTrial(profile, invented) {
    return invented === (profile.profile_origin === "invented_signals");
  }

  function band(profile, model, scheme, point, tick) {
    const radii = profile.half_widths[model];
    const radius = scheme === "pooled" ? radii.pooled : radii.by_issue_phase[phaseAt(tick)];
    const lower = point - radius;
    const upper = point + radius;
    if (![lower, upper, upper - lower].every(Number.isFinite)) throw Error("The band exceeds the numerical range.");
    return {lower, upper};
  }

  function cache(trial, fit) {
    const bins = [];
    const forecasts = [];
    const cachedBin = index => bins[index] ?? (bins[index] = api.bin(trial.rms, index));
    return index => {
      if (!forecasts[index]) {
        const row = api.features(trial, index, cachedBin(index), cachedBin(index + 2));
        forecasts[index] = {tick: row.tick, estimates: api.forecast(fit, row)};
      }
      return forecasts[index];
    };
  }

  const pause = () => new Promise(resolve => setTimeout(resolve, 0));
  const rank90 = values => values.sort((a, b) => a - b)[Math.min(values.length, Math.ceil(.9 * (values.length + 1))) - 1];

  async function calibrate(trials, fit, identity, origin, isCurrent = () => true) {
    const allErrors = Object.fromEntries(models.map(key => [key, Object.fromEntries(phases.map(p => [p, []]))]));
    let nTrials = 0;
    for await (const trial of trials) {
      const read = cache(trial, fit);
      nTrials++;
      for (let index = 0; index < nIssues; index++) {
        if (!isCurrent()) return null;
        const {tick, estimates} = read(index);
        const target = trial.force[tick + horizon];
        const phase = phaseAt(tick);
        for (const key of models) {
          const error = Math.abs(target - estimates[key]);
          if (!Number.isFinite(error)) throw Error("A calibration residual exceeds the numerical range.");
          allErrors[key][phase].push(error);
        }
        if (index % 48 === 47) await pause();
      }
    }
    if (!isCurrent()) return null;
    return validate({
      format, reader_fit_sha256: identity, protocol_sha256: protocol,
      timing_mode: "nominal_release_index", profile_origin: origin, nominal_coverage: .9,
      pooled_count: nTrials * nIssues,
      phase_counts: Object.fromEntries(phases.map((phase, i) => [phase, nTrials * issuesPerPhase[i]])),
      half_widths: Object.fromEntries(models.map(key => {
        const errors = allErrors[key];
        return [key, {
          pooled: rank90(Object.values(errors).flat()),
          by_issue_phase: Object.fromEntries(phases.map(phase => [phase, rank90(errors[phase])]))
        }];
      }))
    });
  }

  async function score(trial, read, profile, isCurrent) {
    let bandError = "";
    const point = Object.fromEntries(Object.keys(api.labels).map(key => [key, {abs: 0, square: 0}]));
    const intervals = profile ? models.flatMap(model => schemes.map(scheme => ({
      model, scheme, below: 0, above: 0, width: 0, penalty: 0
    }))) : [];
    for (let index = 0; index < nIssues; index++) {
      if (!isCurrent()) return null;
      const {tick, estimates} = read(index);
      const target = trial.force[tick + horizon];
      for (const [key, estimate] of Object.entries(estimates)) {
        const error = Math.abs(estimate - target);
        point[key].abs += error;
        point[key].square += error ** 2;
      }
      if (!bandError) {
        try {
          for (const row of intervals) {
            const {lower, upper} = band(profile, row.model, row.scheme, estimates[row.model], tick);
            row.width += upper - lower;
            if (target < lower) {
              row.below++;
              row.penalty += 20 * (lower - target);
            } else if (target > upper) {
              row.above++;
              row.penalty += 20 * (target - upper);
            }
          }
        } catch (error) {
          bandError = error.message;
        }
      }
      if (index % 24 === 23) await pause();
    }
    if (!isCurrent()) return null;
    const predictions = Object.entries(point).map(([key, values]) => [
      key, values.abs / nIssues, Math.sqrt(values.square / nIssues)
    ]);
    const bands = intervals.map(row => ({
      model: row.model, scheme: row.scheme,
      covered: nIssues - row.below - row.above, below: row.below, above: row.above,
      width: row.width / nIssues, penalty: row.penalty / nIssues, score: (row.width + row.penalty) / nIssues
    }));
    if (!predictions.every(row => row.slice(1).every(Number.isFinite))) {
      throw Error("Trial errors exceed the numerical range.");
    }
    const validBands = bands.every(row => [row.width, row.penalty, row.score].every(Number.isFinite));
    if (!validBands) bandError = "Band scores exceed the numerical range.";
    return {predictions, bands: bandError ? [] : bands, bandError};
  }

  async function packetIdentity(record) {
    const buffer = new ArrayBuffer((record.force.length + record.rms.length) * 8);
    const view = new DataView(buffer);
    let offset = 0;
    for (const values of [record.force, record.rms]) {
      for (const value of values) {
        view.setFloat64(offset, value === 0 ? 0 : value, true);
        offset += 8;
      }
    }
    return digest(buffer);
  }

  globalThis.PinchIntervals = {
    phases, phaseEdges, issuesPerPhase, nIssues, horizon, models, schemes, origins,
    phaseAt, digest, validate, matches, compatibleTrial, band, cache, calibrate, score, packetIdentity
  };
})();
