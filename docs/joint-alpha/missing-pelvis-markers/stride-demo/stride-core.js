/* Frozen stride forecast. This script uses only the history supplied at issue. */
(() => {
  "use strict";

  const CHECKPOINT = "2960e3f5b075118d071c42375bf34c099011f63da1c61c5d03f179bd34d46add";
  const MARKERS = 4;
  const TOKENS = 16;
  const WIDTH = 32;
  const HEADS = 4;
  const HEAD_WIDTH = WIDTH / HEADS;
  // Keep the native sample counts and reference rounding for each camera rate.
  const PROFILES = new Map([
    [100, {history: 80, horizon: 10, tail: 20, minLag: 22, maxLag: 60, sharedMinimum: 15}],
    [150, {history: 120, horizon: 15, tail: 30, minLag: 33, maxLag: 90, sharedMinimum: 22}],
    [250, {history: 200, horizon: 25, tail: 50, minLag: 55, maxLag: 150, sharedMinimum: 38}],
  ]);

  function addSquares(history, recentStart, lag, squares) {
    const perMarker = [0, 0, 0, 0];
    let count = 0;
    let index = 0;
    for (let frame = recentStart; frame < history.length; frame++) {
      const recent = history[frame];
      const old = history[frame - lag];
      for (let marker = 0; marker < MARKERS; marker++) {
        let square = 0;
        if (recent[marker] !== null && old[marker] !== null) {
          const difference = recent[marker] - old[marker];
          square = difference * difference;
          count++;
          perMarker[marker]++;
        }
        squares[index++] = square;
      }
    }
    return {count, perMarker};
  }

  // Match the contiguous Float64 reduction used by the reference cycle matcher.
  function pairwiseSum(values, start, length) {
    if (length < 8) {
      let sum = -0;
      for (let i = 0; i < length; i++) sum += values[start + i];
      return sum;
    }
    if (length <= 128) {
      const accumulators = Array.from({length: 8}, (_, i) => values[start + i]);
      const end = length - (length % 8);
      for (let i = 8; i < end; i += 8) {
        for (let lane = 0; lane < 8; lane++) accumulators[lane] += values[start + i + lane];
      }
      let sum = ((accumulators[0] + accumulators[1]) + (accumulators[2] + accumulators[3]))
        + ((accumulators[4] + accumulators[5]) + (accumulators[6] + accumulators[7]));
      for (let i = end; i < length; i++) sum += values[start + i];
      return sum;
    }
    const split = Math.floor(length / 16) * 8;
    return pairwiseSum(values, start, split) + pairwiseSum(values, start + split, length - split);
  }

  function matchCycle(history, profile) {
    const issue = history.length - 1;
    if (history[issue].filter(value => value !== null).length < 2) {
      return {stride: [null, null], cycleFrames: 0, issued: false};
    }
    const {horizon, tail, minLag, maxLag, sharedMinimum} = profile;
    const recentStart = history.length - tail;
    let bestError = Infinity;
    let cycleFrames = 0;
    const squares = new Float64Array(tail * MARKERS);

    for (let lag = minLag; lag <= maxLag; lag++) {
      const earlier = history[issue - lag];
      const later = history[issue - lag + horizon];
      const hasRearMovement = (earlier[2] !== null && later[2] !== null)
        || (earlier[3] !== null && later[3] !== null);
      if (!hasRearMovement) continue;

      const {count, perMarker} = addSquares(history, recentStart, lag, squares);
      if (perMarker.filter(samples => samples >= sharedMinimum).length < 2) continue;
      const error = pairwiseSum(squares, 0, squares.length) / count;
      if (error < bestError) {
        bestError = error;
        cycleFrames = lag;
      }
    }
    if (!cycleFrames) return {stride: [0, 0], cycleFrames, issued: true};

    const earlier = history[issue - cycleFrames];
    const later = history[issue - cycleFrames + horizon];
    let count = 0;
    let rearCount = 0;
    const movement = earlier.map((value, marker) => {
      if (value === null || later[marker] === null) return 0;
      count++;
      if (marker >= 2) rearCount++;
      return later[marker] - value;
    });
    const rear = pairwiseSum(movement, 2, 2);
    return {
      stride: [pairwiseSum(movement, 0, MARKERS) / count, rear / rearCount],
      cycleFrames,
      issued: true,
    };
  }

  function linear(input, kernel, bias) {
    return bias.map((offset, output) => {
      let value = offset;
      for (let i = 0; i < input.length; i++) value += input[i] * kernel[output * input.length + i];
      return value;
    });
  }

  function inputs(history, rate, stride, lag, scale) {
    const anchor = Array(MARKERS).fill(null);
    for (let frame = history.length - 1; frame >= 0; frame--) {
      for (let marker = 0; marker < MARKERS; marker++) {
        if (anchor[marker] === null) anchor[marker] = history[frame][marker];
      }
      if (anchor.every(value => value !== null)) break;
    }
    const sequence = [];
    for (let token = 0; token < TOKENS; token++) {
      const age = (TOKENS - 1 - token) * 50;
      const frame = history.length - 1 - Math.ceil(age * rate / 1000);
      const current = history[frame];
      const old = history[frame - lag];
      const nowAvailable = current.map(value => value !== null);
      const pairAvailable = current.map((value, marker) => Boolean(old && old[marker] !== null && value !== null));
      const positions = [
        ...current.map((value, marker) => value - anchor[marker]),
        ...current.map((value, marker) => old ? value - old[marker] : 0),
      ];
      const available = nowAvailable.concat(pairAvailable);
      sequence.push(positions.map((value, feature) => available[feature]
        ? (value - scale.position_center[feature]) / scale.position_scale[feature]
        : 0).concat(available.map(Number)));
    }
    const context = [...stride, lag / rate].map((value, feature) =>
      (value - scale.context_center[feature]) / scale.context_scale[feature]);
    return {sequence, context};
  }

  function selfAttention(packed) {
    return packed.map(query => {
      const output = new Array(WIDTH).fill(0);
      for (let head = 0; head < HEADS; head++) {
        const headStart = head * HEAD_WIDTH;
        const logits = packed.map(key => {
          let dot = 0;
          for (let d = headStart; d < headStart + HEAD_WIDTH; d++) dot += query[d] * key[WIDTH + d];
          return dot / Math.sqrt(HEAD_WIDTH);
        });
        const peak = Math.max(...logits);
        const exp = logits.map(value => Math.exp(value - peak));
        const total = exp.reduce((sum, value) => sum + value, 0);
        for (let i = 0; i < TOKENS; i++) {
          const share = exp[i] / total;
          for (let d = headStart; d < headStart + HEAD_WIDTH; d++) output[d] += share * packed[i][2 * WIDTH + d];
        }
      }
      return output;
    });
  }

  // Positive-term series for erf keeps the frozen GELU, rather than replacing
  // GELU with the common tanh approximation.
  function erf(x) {
    const absolute = Math.abs(x);
    if (absolute >= 6) return Math.sign(x);
    const squared = x * x;
    let term = 1;
    let sum = 1;
    for (let n = 1; n <= 160; n++) {
      term *= 2 * squared / (2 * n + 1);
      sum += term;
      if (term <= Number.EPSILON * sum && n > squared) break;
    }
    return 2 * x * Math.exp(-squared) * sum / Math.sqrt(Math.PI);
  }

  function learnedCorrection(sequence, context, state) {
    const contextToken = linear(context, state["context.weight"], state["context.bias"]);
    const positioned = sequence.map((row, token) => linear(row, state["token.weight"], state["token.bias"])
      .map((value, feature) => value + state.positions[token * WIDTH + feature] + contextToken[feature]));
    const packed = positioned.map(row => linear(row, state["attention.in_proj_weight"], state["attention.in_proj_bias"]));
    const normalized = selfAttention(packed).map((row, token) => {
      const residual = linear(row, state["attention.out_proj.weight"], state["attention.out_proj.bias"])
        .map((value, feature) => value + positioned[token][feature]);
      const mean = residual.reduce((sum, value) => sum + value, 0) / WIDTH;
      const centered = residual.map(value => value - mean);
      const variance = centered.reduce((sum, value) => sum + value * value, 0) / WIDTH;
      const denominator = Math.sqrt(variance + 1e-5);
      return centered.map((value, feature) =>
        (value / denominator) * state["norm.weight"][feature] + state["norm.bias"][feature]);
    });
    const average = normalized[0].map((_, feature) => normalized
      .reduce((sum, row) => sum + row[feature], 0) / TOKENS);
    const hidden = linear([...normalized[TOKENS - 1], ...average], state["readout.0.weight"], state["readout.0.bias"]);
    const activated = hidden.map(value => 0.5 * value * (1 + erf(value / Math.sqrt(2))));
    return linear(activated, state["readout.2.weight"], state["readout.2.bias"]);
  }

  function predict(historyRows, rateHz, weights) {
    const profile = PROFILES.get(rateHz);
    if (!profile) throw new RangeError("Use 100, 150 or 250 camera frames per second.");
    if (!Array.isArray(historyRows) || historyRows.length < profile.history) {
      throw new RangeError("Provide at least 800 milliseconds of camera readings.");
    }
    for (const row of historyRows) {
      if (!Array.isArray(row) || row.length !== MARKERS || [...row].some(value => value !== null && !Number.isFinite(value))) {
        throw new TypeError("Give four heights in millimetres per row. Use null for a missing height.");
      }
    }
    if (!weights || weights.sha256 !== CHECKPOINT) throw new Error("The frozen stride checkpoint is missing.");
    const matched = matchCycle(historyRows, profile);
    if (!matched.cycleFrames) return {...matched, prediction: matched.stride.slice()};
    const {stride, cycleFrames} = matched;
    const {sequence, context} = inputs(historyRows, rateHz, stride, cycleFrames, weights.scale);
    const adjustment = learnedCorrection(sequence, context, weights.state);
    return {...matched, prediction: stride.map((value, target) => value + adjustment[target] * weights.scale.target_scale[target])};
  }

  globalThis.StrideCore = Object.freeze({predict});
})();
