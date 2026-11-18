(function () {
  "use strict";

  const payload = /* PUBLIC_UJI_PAYLOAD */ null;
  const model = payload.model;
  const BINS = 16;
  const SPOTS = 7;
  const TASKS = 26;
  const HISTORY_MS = 500;
  const BIN_WIDTH_MS = HISTORY_MS / BINS;
  const MIN_SAMPLES = 25;
  const MAX_GAP_MS = 5;
  const HORIZON_MS = 250;
  const MAX_CLOCK_MS = 2 ** 40;
  const MAX_MAGNITUDE = Math.sqrt(Number.MAX_VALUE / 32);
  const AMPLITUDE_SCALE = "kin-mus-uji-v1.0-native-amplitude";
  const SPOT_ORDER = Object.freeze([1, 2, 3, 4, 5, 6, 7]);
  const AXES = Object.freeze(model.axes);
  const KNOTS = Object.freeze(model.knots_seconds);
  const HEADS = Object.freeze(["task_time", "task_time_emg"]);

  const contract = Object.freeze({
    axes: AXES,
    prediction_heads: HEADS,
    task_count: TASKS,
    spot_order: SPOT_ORDER,
    bins: BINS,
    history_ms: HISTORY_MS,
    bin_width_ms: BIN_WIDTH_MS,
    min_samples_per_bin: MIN_SAMPLES,
    max_internal_sample_gap_ms: MAX_GAP_MS,
    min_elapsed_anchor_s: 0.5,
    max_time_basis_s: 30,
    knots_seconds: KNOTS,
    amplitude_scale: AMPLITUDE_SCALE,
    output_offset_from_anchor_ms: HORIZON_MS,
    max_amplitude_magnitude: MAX_MAGNITUDE,
    source: Object.freeze(payload.source)
  });

  function requireInput(condition, message) {
    if (!condition) throw new Error(message);
  }

  function validateClockPair(window) {
    const hasStart = Object.hasOwn(window, "segment_start_ms");
    const hasAnchor = Object.hasOwn(window, "anchor_ms");
    requireInput(hasStart === hasAnchor, "Supply the segment start and EMG cutoff together.");
    if (!hasStart) return;

    const start = window.segment_start_ms;
    const anchor = window.anchor_ms;
    requireInput(Number.isInteger(start) && Math.abs(start) < MAX_CLOCK_MS &&
      Number.isInteger(anchor) && Math.abs(anchor) < MAX_CLOCK_MS,
    "Use integer milliseconds on the same source clock for segment_start_ms and anchor_ms.");
    const elapsedMs = anchor - start;
    requireInput(elapsedMs >= HISTORY_MS &&
      Math.abs(elapsedMs - window.elapsed_anchor_s * 1000) <= 1e-6,
    "The EMG cutoff must be at least 500 ms after the segment start and match elapsed_anchor_s.");
  }

  function checkSpotRow(row, message) {
    requireInput(Array.isArray(row) && row.length === SPOTS, message);
  }

  function validateRms(rows) {
    requireInput(Array.isArray(rows) && rows.length === BINS, "Supply 16 chronological RMS bins.");
    const bins = [];
    for (const row of rows) {
      checkSpotRow(row, "Supply seven RMS amplitudes per bin in source spot order.");
      for (const value of row) {
        requireInput(Number.isFinite(value) && value >= 0 && value <= MAX_MAGNITUDE,
          "Each RMS amplitude must be a finite, nonnegative number within the supported range.");
      }
      bins.push(row.slice());
    }
    return bins;
  }

  function binRawWindow(clock, raw) {
    requireInput(Array.isArray(clock) && clock.length >= 1 && clock.length <= HISTORY_MS,
      "Supply between 1 and 500 raw sample timestamps.");
    requireInput(Array.isArray(raw) && raw.length === clock.length,
      "Supply one EMG row for each timestamp.");
    const counts = Array(BINS).fill(0);
    const sums = Array.from({ length: BINS }, () => Array(SPOTS).fill(0));
    let previous = -HISTORY_MS;
    for (let index = 0; index < clock.length; index++) {
      const time = clock[index];
      requireInput(Number.isInteger(time) && time > -HISTORY_MS && time <= 0,
        "Use integer timestamps greater than −500 ms and at or before the cutoff (0 ms).");
      requireInput(time > previous, "Raw timestamps must increase strictly.");
      requireInput(index === 0 || time - previous <= MAX_GAP_MS,
        "A gap between raw samples exceeds 5 ms.");
      previous = time;
      // Multiples of 31.25 ms are exact in binary64. Boundaries belong to the earlier bin.
      const bin = Math.ceil((time + HISTORY_MS) / BIN_WIDTH_MS) - 1;
      const row = raw[index];
      checkSpotRow(row, "Supply seven raw amplitudes per timestamp in source spot order.");
      for (let spot = 0; spot < SPOTS; spot++) {
        const value = row[spot];
        requireInput(Number.isFinite(value) && Math.abs(value) <= MAX_MAGNITUDE,
          "Each raw amplitude must be a finite number that can be squared and summed safely.");
        sums[bin][spot] += value * value;
      }
      counts[bin]++;
    }
    requireInput(counts.every(count => count >= MIN_SAMPLES),
      "Each 31.25 ms bin needs at least 25 raw samples.");
    const bins = sums.map((row, bin) => row.map(sum => Math.sqrt(sum / counts[bin])));
    requireInput(bins.every(row => row.every(Number.isFinite)),
      "The squared raw amplitudes exceed the supported range.");
    return { bins, counts };
  }

  function prepare(window) {
    requireInput(window !== null && typeof window === "object" && !Array.isArray(window),
      "Supply one window as a JSON object.");
    const task = window.task_id;
    const elapsed = window.elapsed_anchor_s;
    requireInput(window.amplitude_scale === AMPLITUDE_SCALE,
      "Declare the KIN-MUS UJI v1.0 raw amplitude scale.");
    requireInput(Number.isInteger(task) && task >= 1 && task <= TASKS,
      "Choose a source activity ID from 1 to 26.");
    requireInput(Number.isFinite(elapsed) && elapsed >= 0.5,
      "The cutoff needs at least half a second of elapsed time.");
    if (Object.hasOwn(window, "spot_order")) {
      const order = window.spot_order;
      requireInput(Array.isArray(order) && order.length === SPOTS &&
        SPOT_ORDER.every((spot, index) => order[index] === spot),
      "Keep the original spot order from 1 through 7.");
    }
    if (Object.hasOwn(window, "input_provenance")) {
      requireInput(typeof window.input_provenance === "string",
        "Describe the source of the input as text.");
    }
    validateClockPair(window);

    const hasRms = Object.hasOwn(window, "rms_bins");
    const hasClock = Object.hasOwn(window, "clock_ms_from_anchor");
    const hasRaw = Object.hasOwn(window, "emg");
    requireInput(hasRms ? !hasClock && !hasRaw : hasClock && hasRaw,
      "Supply either RMS bins or raw timestamps with their EMG rows.");
    const { bins, counts } = hasRms
      ? { bins: validateRms(window.rms_bins), counts: null }
      : binRawWindow(window.clock_ms_from_anchor, window.emg);
    const clippedElapsed = Math.min(elapsed, 30);
    return {
      task_id: task,
      elapsed_anchor_s: elapsed,
      clipped_elapsed_anchor_s: clippedElapsed,
      time_basis: [clippedElapsed, ...KNOTS.map(knot => Math.max(clippedElapsed - knot, 0))],
      input_kind: hasRms ? "rms" : "raw",
      input_provenance: window.input_provenance ?? "unspecified",
      amplitude_scale: AMPLITUDE_SCALE,
      output_offset_from_anchor_ms: HORIZON_MS,
      rms_bins: bins,
      raw_bin_counts: counts
    };
  }

  function standardize(value, scale) {
    return scale > 0 ? value / scale : 0;
  }

  function predict(head, taskIndex, timeBasis, rmsBins) {
    const timeOffset = taskIndex * timeBasis.length;
    const timePrediction = [0, 0];
    for (let index = 0; index < timeBasis.length; index++) {
      const value = standardize(timeBasis[index], head.time_scale[taskIndex][index]);
      const [extension, radialDeviation] = head.time_beta[timeOffset + index];
      timePrediction[0] += extension * value;
      timePrediction[1] += radialDeviation * value;
    }
    let extension = head.intercept[taskIndex][0] + timePrediction[0];
    let radialDeviation = head.intercept[taskIndex][1] + timePrediction[1];

    if (head.emg_beta.length !== 0) {
      let emgExtension = 0;
      let emgRadialDeviation = 0;
      for (let bin = 0; bin < BINS; bin++) {
        for (let spot = 0; spot < SPOTS; spot++) {
          const index = bin * SPOTS + spot;
          const value = standardize(rmsBins[bin][spot], head.emg_scale[index]);
          const coefficients = head.emg_beta[index];
          emgExtension += coefficients[0] * value;
          emgRadialDeviation += coefficients[1] * value;
        }
      }
      extension += emgExtension;
      radialDeviation += emgRadialDeviation;
    }
    requireInput(Number.isFinite(extension) && Number.isFinite(radialDeviation),
      "This input falls outside the estimator’s finite numerical range.");
    // The fitted state already uses positive extension and positive radial deviation.
    return { [AXES[0]]: extension, [AXES[1]]: radialDeviation };
  }

  function infer(window) {
    const prepared = prepare(window);
    const taskIndex = prepared.task_id - 1;
    const predictions = Object.fromEntries(HEADS.map(name => [
      name, predict(model.models[name], taskIndex, prepared.time_basis, prepared.rms_bins)
    ]));
    return {
      estimator: model.estimator,
      output_offset_from_anchor_ms: HORIZON_MS,
      reference: "offline archive-angle predictions in degree coordinates",
      amplitude_scale: AMPLITUDE_SCALE,
      input_provenance: prepared.input_provenance,
      predictions
    };
  }

  function syntheticExample(name = "patterned") {
    requireInput(Object.hasOwn(payload.examples, name), "Choose the patterned or zero synthetic example.");
    const example = payload.examples[name];
    return { ...example, rms_bins: example.rms_bins.map(row => row.slice()) };
  }

  globalThis.UJIEngine = Object.freeze({ contract, infer, prepare, syntheticExample });
})();
