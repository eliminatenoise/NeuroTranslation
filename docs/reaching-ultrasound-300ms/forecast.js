'use strict';

{
  const rows = 10;
  const fields = 26;
  const width = 48;
  const horizon = 0.300;
  const passCounts = [1, 3, 5, 8];
  const checkpointNames = ['20261126', '20261127'];
  const values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 22, 23];
  const observed = [12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 19, 20, 21, 24, 25];
  const flags = [12, 13, 14, 15, 19, 20, 21, 24, 25];
  const arrayLengths = Object.freeze({
    'conv.weight': width * fields * 3,
    'conv.bias': width,
    'recurrent.weight_ih_l0': 3 * width * width,
    'recurrent.weight_hh_l0': 3 * width * width,
    'recurrent.bias_ih_l0': 3 * width,
    'recurrent.bias_hh_l0': 3 * width,
    'shared_step.weight_ih': 3 * width * width,
    'shared_step.weight_hh': 3 * width * width,
    'shared_step.bias_ih': 3 * width,
    'shared_step.bias_hh': 3 * width,
    'out.weight': 2 * width,
    'out.bias': 2,
  });

  function decode(encoded, length, bytes) {
    const raw = Uint8Array.from(atob(encoded), word => word.charCodeAt(0));
    if (raw.byteLength !== length * bytes) throw new Error('The model file is incomplete.');
    const view = new DataView(raw.buffer);
    const result = new Float64Array(length);
    for (let i = 0; i < length; i++) {
      result[i] = bytes === 4 ? view.getFloat32(i * 4, true) : view.getFloat64(i * 8, true);
    }
    if (!result.every(Number.isFinite)) throw new Error('The model file contains an invalid number.');
    return result;
  }

  function upperBin(mode) {
    if (mode === 'full') return rows;
    if (mode === 'gap') return 5;
    if (mode === 'blind') return 0;
    throw new RangeError('Choose complete history, the recent gap or no ultrasound.');
  }

  function validate(sample, mode) {
    const cutoff = upperBin(mode);
    const history = sample?.history;
    const times = sample?.ultrasound_times_from_issue_s;
    if (!Array.isArray(history) || history.length !== rows || !Array.isArray(times) || times.length !== rows) {
      throw new Error('The input needs 10 rows and 10 ultrasound times.');
    }
    for (let i = 0; i < rows; i++) {
      const row = history[i];
      if (!Array.isArray(row) || row.length !== fields || !row.every(Number.isFinite)) {
        throw new Error('Each row needs 26 finite numbers.');
      }
      if (!flags.every(index => row[index] === 0 || row[index] === 1)) {
        throw new Error('Use 1 for an available reading and 0 for an absent reading.');
      }
      if (i < cutoff && (row[24] || row[25])) {
        const time = times[i];
        if (!Number.isFinite(time) || time >= 0 || time < (i - rows) * 0.02 - 1e-9 ||
            time >= (i + 1 - rows) * 0.02 + 1e-9) {
          throw new Error('Each visible ultrasound time must fall inside its past 20 ms slot.');
        }
      }
    }
    return {history, times};
  }

  function inputHistory(history, cutoff, norm) {
    const result = new Float64Array(rows * fields);
    for (let row = 0; row < rows; row++) {
      const start = row * fields;
      const visible = row < cutoff ? fields : 22;
      for (let col = 0; col < visible; col++) {
        result[start + col] = Math.fround(history[row][col]);
      }
      for (let i = 0; i < values.length && values[i] < visible; i++) {
        const col = values[i];
        result[start + col] = history[row][observed[i]]
          ? Math.fround((history[row][col] - norm.feature_mean[i]) / norm.feature_scale[i]) : 0;
      }
    }
    return result;
  }

  function reference(history, times, cutoff, median) {
    if (!cutoff) return median.slice();
    const start = cutoff - 5;
    return median.map((fallback, tissue) => {
      for (let i = start; i < cutoff; i++) {
        if (!history[i][24 + tissue]) return fallback;
      }
      const meanTime = times.slice(start, cutoff).reduce((sum, time) => sum + time, 0) / 5;
      let spread = 0, covariance = 0, variance = 0;
      for (let i = start; i < cutoff; i++) {
        const offset = times[i] - meanTime;
        const value = history[i][22 + tissue];
        spread += value;
        covariance += offset * value;
        variance += offset * offset;
      }
      if (variance <= 0) throw new Error('Visible ultrasound needs five distinct times.');
      return spread / 5 + covariance / Math.max(variance, 1e-12) * (horizon - meanTime);
    });
  }

  function affine(weight, bias, input, output) {
    for (let row = 0; row < output.length; row++) {
      let sum = 0;
      const start = row * input.length;
      for (let i = 0; i < input.length; i++) sum += weight[start + i] * input[i];
      output[row] = sum + bias[row];
    }
  }

  function sigmoid(value) {
    return 1 / (1 + Math.exp(-Math.max(-60, Math.min(60, value))));
  }

  function step(incoming, state, weight, bias, hidden) {
    affine(weight, bias, state, hidden);
    for (let cell = 0; cell < width; cell++) {
      const reset = sigmoid(incoming[cell] + hidden[cell]);
      const retain = sigmoid(incoming[cell + width] + hidden[cell + width]);
      const candidate = Math.tanh(incoming[cell + 2 * width] + reset * hidden[cell + 2 * width]);
      // The fitted runtime rounds the state after each update.
      state[cell] = candidate + retain * (state[cell] - candidate);
    }
  }

  function convolve(weights, padded, row, output) {
    const kernel = weights['conv.weight'];
    for (let channel = 0; channel < width; channel++) {
      let sum = 0;
      const start = channel * fields * 3;
      for (let col = 0; col < fields; col++) {
        const reading = row * fields + col;
        const coefficient = start + col * 3;
        sum += padded[reading] * kernel[coefficient];
        sum += padded[reading + fields] * kernel[coefficient + 1];
        sum += padded[reading + fields * 2] * kernel[coefficient + 2];
      }
      const linear = sum + weights['conv.bias'][channel];
      output[channel] = linear * sigmoid(linear);
    }
  }

  function learned(inputs, weights, base, scale, counts) {
    const state = new Float32Array(width);
    const encoded = new Float64Array(width);
    const incoming = new Float64Array(3 * width);
    const hidden = new Float64Array(3 * width);
    const padded = new Float64Array(inputs.length + 2 * fields);
    padded.set(inputs, 2 * fields);
    for (let row = 0; row < rows; row++) {
      convolve(weights, padded, row, encoded);
      affine(weights['recurrent.weight_ih_l0'], weights['recurrent.bias_ih_l0'], encoded, incoming);
      step(incoming, state, weights['recurrent.weight_hh_l0'], weights['recurrent.bias_hh_l0'], hidden);
    }
    affine(weights['shared_step.weight_ih'], weights['shared_step.bias_ih'], state, incoming);
    const result = {};
    let done = 0;
    for (const passes of counts) {
      while (done < passes) {
        step(incoming, state, weights['shared_step.weight_hh'], weights['shared_step.bias_hh'], hidden);
        done++;
      }
      const output = [0, 0];
      affine(weights['out.weight'], weights['out.bias'], state, output);
      result[passes] = output.map((value, i) => base[i] + value * scale[i]);
    }
    return result;
  }

  function linear(inputs, coefficient, base, mode) {
    const start = mode === 'full' ? 22 : 0;
    const limit = mode === 'blind' ? 16 : fields;
    let triceps = 0, brachialis = 0;
    for (let row = 0; row < rows; row++) {
      for (let field = start; field < limit; field++) {
        const index = row * fields + field;
        triceps += inputs[index] * coefficient[(index + 1) * 2];
        brachialis += inputs[index] * coefficient[(index + 1) * 2 + 1];
      }
    }
    return [base[0] + coefficient[0] + triceps, base[1] + coefficient[1] + brachialis];
  }

  function create(payload) {
    const norm = payload.normalizer;
    const weights = Object.fromEntries(checkpointNames.map(seed => [seed, Object.fromEntries(
      Object.entries(arrayLengths).map(([name, count]) => [name, decode(payload.weights[seed][name], count, 4)]))]));
    const coefficients = Object.fromEntries(Object.entries(payload.linear).map(
      ([mode, value]) => [mode, decode(value, (rows * fields + 1) * 2, 8)]));

    function compare(sample, {mode = 'full', passes = [3], seed = checkpointNames[0]} = {}) {
      if (!passes.length || !passes.every(value => passCounts.includes(value))) {
        throw new RangeError('Choose one, three, five or eight refinement passes.');
      }
      if (seed !== 'both' && !checkpointNames.includes(seed)) throw new RangeError('Choose a saved checkpoint.');
      const ordered = [...new Set(passes)].sort((a, b) => a - b);
      const cutoff = upperBin(mode);
      const {history, times} = validate(sample, mode);
      const base = reference(history, times, cutoff, norm.training_median);
      const inputs = inputHistory(history, cutoff, norm);
      const chosen = seed === 'both' ? checkpointNames : [seed];
      const models = chosen.map(name => learned(inputs, weights[name], base, norm.target_scale[mode], ordered));
      const readings = linear(inputs, coefficients[mode], base, mode);
      const forecast = Object.fromEntries(ordered.map(count => [count, [0, 1].map(tissue => Math.max(
        0, models.reduce((sum, result) => sum + result[count][tissue], 0) / models.length))]));
      const simple = base.map(value => Math.max(0, value));
      if (![...simple, ...readings, ...Object.values(forecast).flat()].every(Number.isFinite)) {
        throw new Error('The input values are too large to forecast.');
      }
      return {simple, linear: readings.map(value => Math.max(0, value)), forecast};
    }

    return {compare};
  }

  globalThis.ReachingForecast = Object.freeze({create, validate, upperBin});
}
