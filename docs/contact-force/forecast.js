/* Browser port of the two checksum-bound Python preview readers. */
((root) => {
  "use strict";

  const OFFSETS = Object.freeze([0, 100, 200, 300, 400]);
  const HISTORY = 200;
  const HORIZON = 60;
  const RATE = 500;
  const EMG_HISTORY = 1600;
  const EMG_RATE = 4000;
  const THRESHOLD = 0.5;
  const DWELL = 10;
  const CAPTURE_KEYS = ["clock_s", "led_on_s", "grip_n", "load_n", "position",
    "rate_hz", "eeg", "emg_clock_s", "emg"];
  const WINDOW_KEYS = ["rate_hz", "offset_from_confirmation_ms", "elapsed_since_go_cue_s",
    "issue_time_s", "grip_n", "load_n", "position", "eeg", "emg_clock_s", "emg"];

  const grid = (length, fn) => Array.from({ length }, (_, i) => fn(i));
  const sum = (values) => values.reduce((total, value) => total + value, 0);
  const vector = (value, count) => Array.isArray(value) && value.length === count &&
    value.every(Number.isFinite);

  function check(condition, message) {
    if (!condition) throw new Error(message);
  }

  function checkClock(values, step, max, label) {
    check(Array.isArray(values) && values.length > 0 && values.length <= max &&
      values.every((value, i) => Number.isFinite(value) &&
        (i === 0 || Math.abs(value - values[i - 1] - step) <= 1e-6)),
      `Supply an evenly spaced ${label} clock in seconds, with up to ${max} samples.`);
  }

  function validate(raw) {
    check(raw && Object.getPrototypeOf(raw) === Object.prototype, "Supply one JSON object.");
    const window = Object.hasOwn(raw, "offset_from_confirmation_ms");
    check(Object.keys(raw).every((key) => (window ? WINDOW_KEYS : CAPTURE_KEYS).includes(key)),
      "Use only the fields listed in the input guide.");
    let issueTime;
    let elapsed;
    if (window) {
      check(raw.rate_hz === RATE && OFFSETS.includes(raw.offset_from_confirmation_ms),
        "A prepared window requires 500 Hz and an offset of 0, 100, 200, 300 or 400 ms.");
      elapsed = raw.elapsed_since_go_cue_s;
      check(Number.isFinite(elapsed) && elapsed >= raw.offset_from_confirmation_ms / 1000,
        "Elapsed time since the go cue must cover the confirmation offset.");
      issueTime = Object.hasOwn(raw, "issue_time_s") ? raw.issue_time_s : elapsed;
      check(Number.isFinite(issueTime), "The issue time must be finite.");
    } else {
      check(!Object.hasOwn(raw, "rate_hz") || raw.rate_hz === RATE, "The capture must use a 500 Hz clock.");
      checkClock(raw.clock_s, 1 / RATE, 16000, "500 Hz");
      check(Number.isFinite(raw.led_on_s) && raw.led_on_s >= raw.clock_s[0] &&
        raw.led_on_s <= raw.clock_s.at(-1), "The capture must include the LED go time.");
    }
    const length = window ? HISTORY : raw.clock_s.length;
    check(vector(raw.grip_n, length) && vector(raw.load_n, length),
      `Supply ${length} finite grip_n and load_n samples.`);
    check(Array.isArray(raw.position) && raw.position.length === length &&
      raw.position.every((row) => Array.isArray(row) && row.length === 4 &&
        row.every((tracker) => vector(tracker, 3))),
      `Supply ${length} position rows in object, index, thumb and wrist XYZ order.`);
    if (Object.hasOwn(raw, "eeg")) {
      check(Array.isArray(raw.eeg) && raw.eeg.length === length && raw.eeg.every((row) => vector(row, 32)),
        `Supply ${length} EEG rows of 32 finite values in the listed channel order.`);
    }
    if (Object.hasOwn(raw, "emg") || Object.hasOwn(raw, "emg_clock_s")) {
      checkClock(raw.emg_clock_s, 1 / EMG_RATE, 128000, "4 kHz EMG");
      check(Array.isArray(raw.emg) && raw.emg.length === raw.emg_clock_s.length &&
        raw.emg.every((row) => vector(row, 5)),
        "Supply one finite five-channel EMG row per muscle-clock sample.");
    }
    if (!window) return { ...raw, kind: "capture", event: confirm(raw) };
    const clock = grid(HISTORY, (i) => issueTime + (i - HISTORY + 1) / RATE);
    const cue = issueTime - elapsed;
    const confirmation = issueTime - raw.offset_from_confirmation_ms / 1000;
    check(Number.isFinite(cue) && Number.isFinite(confirmation) && clock.every((value, i) =>
      i === 0 || Math.abs(value - clock[i - 1] - 1 / RATE) <= 1e-6),
      "Use a time origin close enough to resolve the 2 ms sample spacing.");
    return {
      ...raw, kind: "window", clock_s: clock,
      led_on_s: cue, event: { reason: "supplied", time: confirmation },
    };
  }

  function confirm({ grip_n: grip, clock_s: clock, led_on_s: led }) {
    const go = clock.findIndex((time) => time >= led);
    if (grip[go] >= THRESHOLD) return { reason: "left_censored" };
    let run = 0;
    for (let sample = go + 1; sample < grip.length; sample += 1) {
      run = grip[sample] >= THRESHOLD ? run + 1 : 0;
      if (run === DWELL) return { reason: "confirmed", index: sample, time: clock[sample] };
    }
    return { reason: run ? "right_censored_incomplete_run" : "right_censored_below_at_end" };
  }

  function upperBound(clock, time) {
    let low = 0;
    let high = clock.length;
    while (low < high) {
      const mid = (low + high) >>> 1;
      if (clock[mid] <= time) low = mid + 1;
      else high = mid;
    }
    return low;
  }

  function throughIssue(input, offset) {
    check(OFFSETS.includes(offset), "Choose a scheduled issue time.");
    const { event, kind, clock_s: clock } = input;
    if (kind === "window" && offset !== input.offset_from_confirmation_ms) {
      return { status: "different_window_offset" };
    }
    if (!Number.isFinite(event.time)) return { status: event.reason };
    const end = kind === "window" ? HISTORY - 1 : event.index + offset / 2;
    if (end >= clock.length) return { status: "issue_outside_recording" };
    const start = end - HISTORY + 1;
    if (start < 0) return { status: "short_history" };
    const issue = clock[end];
    const elapsed = kind === "window" ? input.elapsed_since_go_cue_s : issue - input.led_on_s;
    const data = { status: "ok", start, end, issue, elapsed, target: issue + HORIZON / RATE,
      phase: [...OFFSETS.map((ms) => Number(offset === ms)), elapsed] };
    for (const key of ["grip_n", "load_n", "position", "eeg", "clock_s"]) {
      if (Object.hasOwn(input, key)) data[key] = input[key].slice(start, end + 1);
    }
    if (input.emg_clock_s) {
      const emgEnd = upperBound(input.emg_clock_s, issue);
      if (emgEnd >= EMG_HISTORY && issue - input.emg_clock_s[emgEnd - 1] <= 1 / EMG_RATE + 1e-6) {
        data.emg = input.emg.slice(emgEnd - EMG_HISTORY, emgEnd);
        data.emg_clock_s = input.emg_clock_s.slice(emgEnd - EMG_HISTORY, emgEnd);
      }
    }
    return data;
  }

  function dot(left, right) {
    let total = 0;
    for (let i = 0; i < left.length; i += 1) total += left[i] * right[i];
    return total;
  }

  function mechanical({ grip_n: grip, load_n: load, position, phase }) {
    const gf = grip.at(-1);
    const lf = load.at(-1);
    const tap = (values, ms) => values.at(-1 - ms / 2);
    const lags = (values) => [0, 20, 40, 80, 160, 320].map((ms) => tap(values, ms));
    const g20 = (gf - tap(grip, 20)) / 0.020;
    const g80 = (gf - tap(grip, 80)) / 0.080;
    const l20 = (lf - tap(load, 20)) / 0.020;
    const l80 = (lf - tap(load, 80)) / 0.080;
    const last = position.at(-1);
    const delta = (ms, trackers, scale) => trackers.flatMap((t) =>
      last[t].map((value, axis) => (value - tap(position, ms)[t][axis]) / scale));
    const aperture = Math.hypot(...last[1].map((value, axis) => value - last[2][axis]));
    return {
      slope: gf + 0.120 * g80,
      design: [...phase, ...lags(grip), ...lags(load), g20, g80, l20, l80, aperture,
        ...delta(320, [0, 3], 1), ...delta(80, [0, 1, 2, 3], 0.08),
        ...delta(160, [0, 1, 2, 3], 0.16), gf ** 2, lf ** 2, g80 ** 2, gf * lf, gf * g80, lf * g80,
        ...phase.slice(0, -1).flatMap((flag) => [flag * gf, flag * lf, flag * g80])],
    };
  }

  const centeredTime = grid(HISTORY, (i) => i - (HISTORY - 1) / 2);
  const trendDenominator = dot(centeredTime, centeredTime);
  const hann = grid(HISTORY, (i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (HISTORY - 1)));
  const bandBins = [[3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14]];
  const basis = bandBins.map((bins) => bins.map((k) => ({
    cosine: grid(HISTORY, (i) => Math.cos(-2 * Math.PI * k * i / HISTORY)),
    sine: grid(HISTORY, (i) => Math.sin(-2 * Math.PI * k * i / HISTORY)),
  })));
  const periodogramFactor = 2 / (HISTORY * dot(hann, hann));

  function ridgeReference(row) {
    // NumPy reduces this contiguous 32-channel axis in eight summed lanes.
    const [a, b, c, d, e, f, g, h] = grid(8, (i) =>
      ((row[i] + row[i + 8]) + row[i + 16]) + row[i + 24]);
    const mean = (((a + b) + (c + d)) + ((e + f) + (g + h))) / 32;
    return row.map((value) => value - mean);
  }

  function cnnReference(row) {
    // The current CPython float sum uses a running correction.
    let total = 0;
    let correction = 0;
    for (const value of row) {
      const next = total + value;
      correction += Math.abs(total) >= Math.abs(value) ? (total - next) + value : (value - next) + total;
      total = next;
    }
    const mean = (Number.isFinite(correction) ? total + correction : total) / 32;
    return row.map((value) => value - mean);
  }

  function ridgeScalp(referenced) {
    const averages = grid(4, (block) => grid(32, (channel) => {
      let total = 0;
      for (let i = block * 50; i < (block + 1) * 50; i += 1) total += referenced[i][channel];
      return total / 50;
    }));
    const byChannel = grid(32, (channel) => {
      const trace = referenced.map((row) => row[channel]);
      const mean = sum(trace) / HISTORY;
      const centered = trace.map((value) => value - mean);
      const slope = dot(centeredTime, centered) / trendDenominator;
      return centered.map((value, i) => (value - centeredTime[i] * slope) * hann[i]);
    });
    const powers = basis.flatMap((band) => byChannel.map((trace) => {
      let power = 0;
      for (const { cosine, sine } of band) power += dot(trace, cosine) ** 2 + dot(trace, sine) ** 2;
      return Math.log(Math.max(power * periodogramFactor, 1e-12));
    }));
    return [...averages.flatMap((block) => block.map((value, i) => value - averages[0][i])), ...powers];
  }

  function ridgeMuscle(rows) {
    const means = grid(5, (channel) => sum(rows.map((row) => row[channel])) / EMG_HISTORY);
    return grid(4, (block) => grid(5, (channel) => {
      let squares = 0;
      for (let i = block * 400; i < (block + 1) * 400; i += 1) {
        squares += (rows[i][channel] - means[channel]) ** 2;
      }
      return Math.sqrt(squares / 400);
    })).flat();
  }

  function linear(branch, design, currentGrip) {
    const values = design.map((value, i) => (value - branch.means[i]) / branch.scales[i]);
    return (branch.add_present_grip_n ? currentGrip : 0) + branch.intercept_n +
      dot(values, branch.coefficients_n);
  }

  function temporalBins(data, referenced) {
    const { grip_n: grip, load_n: load, position } = data;
    const subtract = (point, baseline) => point.map((value, i) => value - baseline[i]);
    const inputs = position.map(([object, index, thumb, wrist], i) => [
      grip[i], load[i], ...subtract(object, position[0][0]), ...subtract(index, object),
      ...subtract(thumb, object), ...subtract(wrist, position[0][3]), ...(referenced?.[i] || []),
    ]);
    return grid(inputs[0].length, (c) => grid(50, (b) => {
      const i = b * 4;
      return (inputs[i][c] + inputs[i + 1][c] + inputs[i + 2][c] + inputs[i + 3][c]) / 4;
    }));
  }

  function silu(x) {
    if (x >= 0) return x / (1 + Math.exp(-x));
    const exp = Math.exp(x);
    return x * exp / (1 + exp);
  }

  function convolution(signal, weights, biases, dilation) {
    const width = weights[0][0].length;
    const count = signal[0].length - dilation * (width - 1);
    return weights.map((output, o) => grid(count, (t) => {
      let product = 0;
      for (let c = 0; c < output.length; c += 1) {
        for (let k = 0; k < width; k += 1) product += output[c][k] * signal[c][t + k * dilation];
      }
      return silu(biases[o] + product);
    }));
  }

  function temporal(branch, bins, phase, grip) {
    const normalize = (value, mean, scale) => (value - mean) / scale;
    const maskAfter = { phase: 0, mechanics: 14, aligned: 46 }[branch.mode];
    let hidden = branch.temporal_means[0].map(([mean], c) =>
      grid(50, (b) => normalize(c < maskAfter ? bins[c][b] : 0, mean, branch.temporal_scales[0][c][0])));
    for (const [layer, dilation] of [[0, 1], [2, 4], [4, 9]]) {
      hidden = convolution(hidden, branch[`tensor.history.${layer}.weight`],
        branch[`tensor.history.${layer}.bias`], dilation);
    }
    const context = phase.map((value, i) => normalize(value, branch.phase_means[0][i], branch.phase_scales[0][i]));
    const head = [...hidden.map((channel) => channel[0]), ...context];
    const first = branch["tensor.head.0.weight"].map((row, i) =>
      silu(branch["tensor.head.0.bias"][i] + dot(row, head)));
    return branch["tensor.head.2.bias"][0] + dot(branch["tensor.head.2.weight"][0], first) +
      (branch.mode === "phase" ? 0 : grip);
  }

  function forecast(input, offset, { ridge, cnn }) {
    const data = throughIssue(input, offset);
    if (data.status !== "ok") return data;
    const grip = data.grip_n.at(-1);
    const { design, slope } = mechanical(data);
    const scalp = data.eeg && ridgeScalp(data.eeg.map(ridgeReference));
    const muscle = data.emg && ridgeMuscle(data.emg);
    const bins = temporalBins(data, data.eeg?.map(cnnReference));
    const values = {
      persistence: grip, backward_slope: slope,
      ridge_time: linear(ridge.time_only, data.phase, grip),
      ridge_mechanics: linear(ridge.mechanics, design, grip),
      cnn_time: temporal(cnn.phase, bins, data.phase, grip),
      cnn_mechanics: temporal(cnn.mechanics, bins, data.phase, grip),
    };
    if (scalp) {
      values.ridge_eeg = linear(ridge.aligned_eeg, [...design, ...scalp], grip);
      values.cnn_eeg = temporal(cnn.aligned, bins, data.phase, grip);
    }
    if (muscle) {
      values.ridge_emg = linear(ridge.emg, [...design, ...muscle], grip);
      if (scalp) values.ridge_emg_eeg = linear(ridge.emg_aligned_eeg, [...design, ...scalp, ...muscle], grip);
    }
    const invalid = Object.keys(values).filter((key) => !Number.isFinite(values[key]));
    for (const key of invalid) delete values[key];
    return { ...data, values, invalid };
  }

  function comparisonTarget(input, data) {
    if (input.kind !== "capture" || data.status !== "ok") return undefined;
    return input.grip_n[data.end + HORIZON];
  }

  function synthetic(mode = "pinch") {
    const slow = mode === "slow";
    const retry = mode === "brief";
    const time = grid(740, (i) => i / RATE);
    const emgTime = grid(5920, (i) => i / EMG_RATE);
    const riseAt = slow ? .72 : .60;
    const rise = (t, start, tau) => -Math.expm1(-Math.max(t - start, 0) / tau);
    const load = time.map((t) => (slow ? 2.1 : 3) * rise(t, riseAt + .08, slow ? .24 : .15));
    return {
      rate_hz: RATE, led_on_s: .20, clock_s: time,
      grip_n: time.map((t, i) => (slow ? 4.4 : 5) * rise(t, riseAt, slow ? .27 : .12) +
        (retry && i >= 238 && i < 245 ? .64 : 0)),
      load_n: load,
      position: time.map((t, i) => {
        const reach = rise(t, .30, .09);
        const lift = 1.5 * load[i];
        return [[0, 0, lift], [2.3 - 1.3 * reach, 0.11, lift + .02 * reach],
          [-2.3 + 1.3 * reach, -.08, lift], [-.5, 1.1 - .5 * reach, .86 * lift]];
      }),
      eeg: time.map((t) => grid(32, (c) => 3 * Math.sin(2 * Math.PI * 10 * t + c / 6) +
        .7 * Math.sin(2 * Math.PI * 21 * t + c / 11) * rise(t, .28, .2))),
      emg_clock_s: emgTime,
      emg: emgTime.map((t) => grid(5, (c) => (9 + 41 * rise(t, riseAt - .09, .064)) *
        Math.sin(2 * Math.PI * (45 + c * 2) * t + c))),
    };
  }

  const api = Object.freeze({ OFFSETS, HISTORY, HORIZON, THRESHOLD, DWELL, validate,
    forecast, throughIssue, comparisonTarget, synthetic });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ContactForecast = api;
})(globalThis);
