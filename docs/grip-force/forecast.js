/* Feature order and source scales follow the frozen WAY-EEG-GAL package. */
"use strict";
const GripForecast = (() => {
  const H = 200, M = 1600, EEG_HZ = 500, EMG_HZ = 4000, EEG_CHANNELS = 32, EMG_CHANNELS = 5;
  const ISSUES = Array.from({ length: 29 }, (_, i) => 120 + 20 * i);
  const SERIES = ["weight", "friction", "mixed"];
  const TRACKERS = ["object", "index", "thumb", "wrist"];
  const AXES = ["x", "y", "z"];
  const TAPS_MS = [0, 20, 40, 80, 160, 320];
  const BANDS = ["7p5_to_12p5", "gt12p5_to_25", "gt25_to_35"];
  const BIN_GROUPS = [[3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14]];
  const WINDOW_FORMAT = "way-grip-window-v1";
  const HORIZON_MS = 120;
  const FIELDS = ["format", "issue_offset", "series_type", "trial_number", "time_from_cutoff_s",
    "grip_n", "load_n", "position", "eeg", "emg"];
  const timeIndex = Array.from({ length: H }, (_, n) => n - (H - 1) / 2);
  const taper = timeIndex.map((_, n) => 0.5 - 0.5 * Math.cos(2 * Math.PI * n / (H - 1)));
  const timeSquared = timeIndex.reduce((sum, n) => sum + n * n, 0);
  const powerScale = 2 / (H * taper.reduce((sum, t) => sum + t * t, 0));
  // Only the 12 frequency bins that contribute to the fitted features are needed.
  const spectralBasis = BIN_GROUPS.map(group => group.map(k => ({
    cos: taper.map((w, n) => w * Math.cos(2 * Math.PI * k * n / H)),
    sin: taper.map((w, n) => w * Math.sin(2 * Math.PI * k * n / H)),
  })));

  const contextNames = ISSUES.map(n => `LED_sample_${n}`).concat(
    SERIES.map(name => `series_type_${name}`), ["trial_number", "first_trial"]);
  const forceNames = ["GF", "LF"];
  const mechanicalNames = [
    ...forceNames.flatMap(f => TAPS_MS.map(ms => `${f}_lag_${ms}ms`)),
    ...forceNames.flatMap(f => TAPS_MS.slice(1).map(ms => `${f}_slope_${ms}ms`)),
    "aperture",
    ...["object", "wrist"].flatMap(t => AXES.map(a => `${t}_displacement_${a}_320ms`)),
    ...[80, 160].flatMap(ms => [
      ...TRACKERS.flatMap(t => AXES.map(a => `${t}_velocity_${a}_${ms}ms`)),
      `aperture_velocity_${ms}ms`,
    ]),
    "GF_squared", "LF_squared", "GF_slope_80ms_squared", "GF_by_LF", "GF_by_GF_slope_80ms", "LF_by_GF_slope_80ms",
  ];
  const channels = n => Array.from({ length: n }, (_, i) => i + 1);
  const eegNames = [
    ...[1, 2, 3, 4].flatMap(b => channels(EEG_CHANNELS).map(c =>
      `EEG_channel_${String(c).padStart(2, "0")}_mean_bin_${b}_relative_to_first`)),
    ...BANDS.flatMap(b => channels(EEG_CHANNELS).map(c =>
      `EEG_channel_${String(c).padStart(2, "0")}_log_power_${b}_Hz`)),
  ];
  const emgNames = [1, 2, 3, 4].flatMap(b => channels(EMG_CHANNELS).map(c => `EMG_channel_${c}_RMS_bin_${b}`));
  const strongNames = contextNames.concat(mechanicalNames);
  const branchNames = {
    context: contextNames,
    strong: strongNames,
    eeg: strongNames.concat(eegNames),
    emg: strongNames.concat(emgNames),
    emg_eeg: strongNames.concat(emgNames, eegNames),
  };

  function exactFields(value, names) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
      && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));
  }

  function numericShape(value, dims, axis = 0) {
    if (axis === dims.length) return Number.isFinite(value);
    return Array.isArray(value) && value.length === dims[axis]
      && value.every(child => numericShape(child, dims, axis + 1));
  }

  function validateClock(values, count, hz, name) {
    if (!numericShape(values, [count])) {
      throw new Error(`${name} needs ${count} finite time offsets in seconds.`);
    }
    for (let i = 1; i < values.length; i++) {
      const step = values[i] - values[i - 1];
      if (!(step > 0) || Math.abs(step - 1 / hz) > 1e-8) {
        throw new Error(`${name} offsets must be increasing at ${hz} Hz.`);
      }
    }
  }

  function validateWindow(input) {
    if (!exactFields(input, FIELDS) || input.format !== WINDOW_FORMAT) {
      throw new Error("Use the way-grip-window-v1 JSON fields from the example.");
    }
    if (!ISSUES.includes(input.issue_offset)) {
      throw new Error("Issue offset must be a 500 Hz sample count from 120 to 680 in steps of 20.");
    }
    if (!SERIES.includes(input.series_type) || !Number.isSafeInteger(input.trial_number) || input.trial_number < 1) {
      throw new Error("Use weight, friction or mixed and a positive whole trial number.");
    }
    const clocks = input.time_from_cutoff_s;
    if (!exactFields(clocks, ["main", "emg"])) {
      throw new Error("Supply the main and EMG time offsets on the same cutoff clock.");
    }
    validateClock(clocks.main, H, EEG_HZ, "Force, motion and EEG");
    validateClock(clocks.emg, M, EMG_HZ, "EMG");
    const mainEnd = clocks.main[H - 1], emgEnd = clocks.emg[M - 1];
    if (Math.abs(mainEnd) > 1e-10 || emgEnd - mainEnd > 1e-10
        || mainEnd - emgEnd >= 1 / EMG_HZ + 1e-10) {
      throw new Error("End the 500 Hz window at cutoff and use the last 4 kHz sample at or before it.");
    }
    const dimensions = { grip_n: [H], load_n: [H], position: [H, 4, 3], eeg: [H, EEG_CHANNELS], emg: [M, EMG_CHANNELS] };
    for (const [name, shape] of Object.entries(dimensions)) {
      if (!numericShape(input[name], shape)) {
        throw new Error(`${name} needs ${shape.join(" × ")} finite numbers in source order.`);
      }
    }
  }

  function contextFeatures(input) {
    return [
      ...ISSUES.map(n => Number(n === input.issue_offset)),
      ...SERIES.map(kind => Number(kind === input.series_type)),
      input.trial_number, Number(input.trial_number === 1),
    ];
  }

  function mechanicalFeatures(input) {
    const recent = H - 1;
    const tap = values => TAPS_MS.map(ms => values[recent - ms / 2]);
    const slope = taps => TAPS_MS.slice(1).map((ms, i) => (taps[0] - taps[i + 1]) / (ms / 1000));
    const grip = tap(input.grip_n), load = tap(input.load_n);
    const gripSlopes = slope(grip), loadSlopes = slope(load);
    const last = input.position[recent];
    const aperture = pose => Math.hypot(...pose[1].map((x, a) => x - pose[2][a]));
    const separation = aperture(last);
    const displacement = [0, 3].flatMap(t => last[t].map((v, a) => v - input.position[recent - 160][t][a]));
    const velocities = [40, 80].flatMap(samples => {
      const past = input.position[recent - samples], duration = samples / EEG_HZ;
      return [...last.flatMap((tracker, t) => tracker.map((v, a) => (v - past[t][a]) / duration)),
        (separation - aperture(past)) / duration];
    });
    const gf = grip[0], lf = load[0], s = gripSlopes[2];
    return [...grip, ...load, ...gripSlopes, ...loadSlopes, separation, ...displacement, ...velocities,
      gf * gf, lf * lf, s * s, gf * lf, gf * s, lf * s];
  }

  function eegFeatures(eeg) {
    const partialSums = new Float64Array(8);
    const referenced = eeg.map(row => {
      // Match the portable NumPy reduction on the contiguous 32-channel axis.
      // This order cancels an identical signal across all channels exactly.
      for (let i = 0; i < 8; i++) partialSums[i] = ((row[i] + row[i + 8]) + row[i + 16]) + row[i + 24];
      const [a, b, c, d, e, f, g, h] = partialSums;
      const average = (((a + b) + (c + d)) + ((e + f) + (g + h))) / EEG_CHANNELS;
      return row.map(value => value - average);
    });
    const means = Array.from({ length: 4 }, () => Array(EEG_CHANNELS).fill(0));
    const powers = Array.from({ length: 3 }, () => Array(EEG_CHANNELS).fill(0));
    const detrended = new Float64Array(H);
    for (let c = 0; c < EEG_CHANNELS; c++) {
      const blockSums = [0, 0, 0, 0];
      let average = 0;
      for (let i = 0; i < H; i++) {
        const sample = referenced[i][c];
        blockSums[Math.floor(i / 50)] += sample;
        average += sample;
      }
      for (let b = 0; b < 4; b++) means[b][c] = blockSums[b] / 50 - blockSums[0] / 50;
      average /= H;
      let slope = 0;
      for (let i = 0; i < H; i++) slope += timeIndex[i] * (referenced[i][c] - average);
      slope /= timeSquared;
      for (let i = 0; i < H; i++) detrended[i] = referenced[i][c] - average - timeIndex[i] * slope;
      for (const [b, group] of spectralBasis.entries()) {
        let sum = 0;
        for (const { cos, sin } of group) {
          let real = 0, imaginary = 0;
          for (let i = 0; i < H; i++) {
            real += detrended[i] * cos[i];
            imaginary += detrended[i] * sin[i];
          }
          sum += (real * real + imaginary * imaginary) * powerScale;
        }
        powers[b][c] = Math.log(sum + 1e-24);
      }
    }
    return means.flat().concat(powers.flat());
  }

  function emgFeatures(emg) {
    const averages = Array(EMG_CHANNELS).fill(0);
    const sums = Array.from({ length: 4 }, () => Array(EMG_CHANNELS).fill(0));
    for (const row of emg) {
      for (let c = 0; c < EMG_CHANNELS; c++) averages[c] += row[c];
    }
    const blockSize = M / 4;
    for (const [i, row] of emg.entries()) {
      const block = sums[Math.floor(i / blockSize)];
      for (let c = 0; c < EMG_CHANNELS; c++) {
        const centered = row[c] - averages[c] / M;
        block[c] += centered * centered;
      }
    }
    return sums.flat().map(v => Math.sqrt(v / blockSize));
  }

  function featuresFor(input) {
    validateWindow(input);
    const blocks = {
      context: contextFeatures(input),
      mechanical: mechanicalFeatures(input),
      eeg: eegFeatures(input.eeg),
      emg: emgFeatures(input.emg),
    };
    if (Object.values(blocks).some(block => !block.every(Number.isFinite))) {
      throw new Error("This window produced nonfinite features. Check the native source scales.");
    }
    return blocks;
  }

  function fromBundle(bundle) {
    if (bundle.format !== "way-grip-force-study-models-v1" || !exactFields(bundle.models, Object.keys(branchNames))) {
      throw new Error("The study model bundle is missing a frozen branch.");
    }
    for (const [branch, names] of Object.entries(branchNames)) {
      const model = bundle.models[branch];
      const size = names.length;
      const response = branch === "context" ? "future_grip_n" : "future_minus_present_grip_n";
      if (model.response !== response || model.feature_names.length !== size
        || names.some((name, i) => name !== model.feature_names[i])
        || [model.mean, model.scale, model.coefficient].some(array => !numericShape(array, [size]))
        || model.scale.some(value => value <= 0) || !Number.isFinite(model.intercept)
        || !Number.isFinite(model.penalty) || model.penalty <= 0) {
        throw new Error(`Frozen parameters for ${branch} do not match the feature schema.`);
      }
    }

    return input => {
      const blocks = featuresFor(input);
      const present = input.grip_n[H - 1];
      const oldGrip = input.grip_n[H - 1 - 40];
      const strong = blocks.context.concat(blocks.mechanical);
      const values = {
        context: blocks.context,
        strong,
        eeg: strong.concat(blocks.eeg),
        emg: strong.concat(blocks.emg),
        emg_eeg: strong.concat(blocks.emg, blocks.eeg),
      };
      const forecasts = {
        persistence: present,
        linear_extrapolate: present + 0.120 * (present - oldGrip) / 0.080,
      };
      for (const [branch, row] of Object.entries(values)) {
        const model = bundle.models[branch];
        const weighted = row.reduce((sum, v, i) => sum + (v - model.mean[i]) / model.scale[i] * model.coefficient[i], 0);
        forecasts[branch] = model.intercept + weighted + (branch === "context" ? 0 : present);
      }
      if (!Object.values(forecasts).every(Number.isFinite)) throw new Error("This window produced a nonfinite forecast.");
      return forecasts;
    };
  }

  function synthetic(issue = 420, effort = 1) {
    const main = Array.from({ length: H }, (_, i) => (i - H + 1) / EEG_HZ);
    const muscle = Array.from({ length: M }, (_, i) => (i - M + 1) / EMG_HZ);
    const shift = (issue - 420) / EEG_HZ;
    const motionTime = t => t - main[0] + shift;
    return {
      format: WINDOW_FORMAT, issue_offset: issue, series_type: "weight", trial_number: 2,
      time_from_cutoff_s: { main, emg: muscle },
      grip_n: main.map(t => (1.2 + 0.6 * motionTime(t)) * effort),
      load_n: main.map(t => (0.8 + 0.2 * motionTime(t)) * effort),
      position: main.map(t => [0, 0.7, -0.7, 0].map(x => [x, 0, 0.3 * motionTime(t) * effort])),
      eeg: main.map(t => channels(EEG_CHANNELS).map(c =>
        Math.sin(2 * Math.PI * 10 * (t + shift)) * (-0.3 + (c - 1) * 0.6 / 31) * effort)),
      emg: muscle.map(t => Array(EMG_CHANNELS).fill(Math.sin(2 * Math.PI * 41 * (t + shift)) * effort)),
    };
  }

  return { fromBundle, synthetic, featuresFor, HORIZON_MS, TRACKERS };
})();
