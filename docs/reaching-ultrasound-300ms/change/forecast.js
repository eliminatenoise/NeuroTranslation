'use strict';

{
  const rows = 10;
  const inputFields = 22;
  const fields = 26;
  const width = 48;
  const tissueOrder = Object.freeze(['triceps', 'brachialis']);
  const values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18];
  const observed = [12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 19, 20, 21];
  const flags = [12, 13, 14, 15, 19, 20, 21];
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
  const methods = Object.freeze([
    {id: 'zero_change', label: 'No change'},
    {id: 'absolute_motion_ridge', label: 'Motion-only ridge'},
    {id: 'relative_motion_u800_p1', label: 'Motion-only recurrent model'},
    {id: 'absolute_motion_emg_u1600_p3', label: 'Absolute motion and EMG'},
    {id: 'relative_motion_emg_u1600_p3', label: 'Relative motion and EMG'},
  ].map(Object.freeze));

  // Numeric kernels match the verified absolute reaching browser runner.
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

  function learned(inputs, weights, scale, passes) {
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
    for (let done = 0; done < passes; done++) {
      step(incoming, state, weights['shared_step.weight_hh'], weights['shared_step.bias_hh'], hidden);
    }
    const output = [0, 0];
    affine(weights['out.weight'], weights['out.bias'], state, output);
    return output.map((value, i) => value * scale[i]);
  }

  function histories(history) {
    const cases = Array.isArray(history?.[0]?.[0]) ? history : [history];
    const count = cases[0]?.[0]?.length;
    if (count !== inputFields && count !== fields) {
      throw new Error('Supply ten history rows with 22 or 26 numbers per row.');
    }
    for (const one of cases) {
      if (!Array.isArray(one) || one.length !== rows || one.some(row => !Array.isArray(row) || row.length !== count)) {
        throw new Error('Supply ten history rows with 22 or 26 numbers per row.');
      }
      for (const row of one) {
        if (!Array.from({length: inputFields}, (_, col) => row[col]).every(Number.isFinite)) {
          throw new Error('Motion and muscle inputs need finite numbers.');
        }
        if (!flags.every(col => row[col] === 0 || row[col] === 1)) {
          throw new Error('Use 0 for an absent reading and 1 for an available reading.');
        }
      }
    }
    return cases;
  }

  function inputHistory(history, norm, relative, motionOnly) {
    const result = new Float64Array(rows * fields);
    const anchors = relative ? [12, 13, 14, 15].map(flag => history.find(row => row[flag] === 1)) : [];
    const used = motionOnly ? 12 : values.length;
    for (let t = 0; t < rows; t++) {
      const row = history[t];
      const start = t * fields;
      for (let i = 0; i < used; i++) {
        const col = values[i];
        const flag = observed[i];
        if (!row[flag]) continue;
        const origin = relative && col < 12 ? anchors[Math.floor(col / 3)][col] : 0;
        result[start + col] = Math.fround((row[col] - origin - norm.mean[i]) / norm.scale[i]);
        result[start + flag] = 1;
      }
    }
    return result;
  }

  function ridge(inputs, coefficient) {
    let triceps = 0;
    let brachialis = 0;
    for (let row = 0; row < rows; row++) {
      for (let field = 0; field < 16; field++) {
        const index = row * fields + field;
        triceps += inputs[index] * coefficient[(index + 1) * 2];
        brachialis += inputs[index] * coefficient[(index + 1) * 2 + 1];
      }
    }
    return [coefficient[0] + triceps, coefficient[1] + brachialis];
  }

  const payload = globalThis.NeuroTranslateReachingChangeData;
  if (!payload) throw new Error('The reaching change model file could not be loaded.');
  const {configuration, normalizer} = payload;
  const scale = normalizer.target_scale_mm;
  const coefficient = decode(payload.ridge, (rows * fields + 1) * 2, 8);
  const trained = configuration.learned.map(method => ({
    ...method,
    weights: method.files.map(file => Object.fromEntries(Object.entries(arrayLengths).map(([name, count]) =>
      [name, decode(payload.weights[file][name], count, 4)]))),
  }));

  function forecast(history) {
    const cases = histories(history);
    const estimates = Object.fromEntries(methods.map(method => [method.id, []]));
    const seeds = Object.fromEntries(trained.flatMap(method => configuration.seeds.map(seed =>
      [`${method.name}_seed${seed}`, []])));
    for (const one of cases) {
      estimates[configuration.zero].push([0, 0]);
      const control = inputHistory(one, normalizer.features.absolute, false, true);
      estimates[configuration.linear.name].push(ridge(control, coefficient));
      for (const method of trained) {
        const input = inputHistory(one, normalizer.features[method.representation],
          method.representation === 'relative', method.motion_only);
        const predictions = method.weights.map((weights, i) => {
          const change = learned(input, weights, scale, method.passes);
          seeds[`${method.name}_seed${configuration.seeds[i]}`].push(change);
          return change;
        });
        estimates[method.name].push(predictions[0].map((value, tissue) => (value + predictions[1][tissue]) / 2));
      }
    }
    if ([...Object.values(estimates), ...Object.values(seeds)].some(cases => cases.some(pair => !pair.every(Number.isFinite)))) {
      throw new Error('The input values are too large to forecast.');
    }
    return {
      forecast_horizon_ms: 300,
      tissue_order: tissueOrder,
      change_in_spread_mm: estimates,
      seed_change_in_spread_mm: seeds,
    };
  }

  globalThis.NeuroTranslateReachingChange = Object.freeze({
    forecast,
    methods,
    tissue_order: tissueOrder,
    field_order: Object.freeze([...configuration.field_order]),
    example: Object.freeze(payload.example.map(row => Object.freeze([...row]))),
  });
}
