'use strict';

{
  const frames = 10;
  const angles = 4;
  const channels = 20;
  const width = 24;
  const passes = 3;
  const fingers = Object.freeze(['Index', 'Middle', 'Ring', 'Pinky']);
  const fields = Object.freeze([
    ...fingers.map(name => `${name.toLowerCase()}_angle_degrees`),
    ...Array.from({length: 16}, (_, tile) => `log_echo_tile_${tile + 1}`),
  ]);
  const methods = Object.freeze([
    {id: 'zero_change', label: 'No change', requiresUltrasound: false},
    {id: 'past_angle_trend', label: 'Recent angle trend', requiresUltrasound: false},
    {id: 'angle_ridge', label: 'Angle ridge', requiresUltrasound: false},
    {id: 'angle_recurrent', label: 'Angle recurrent', requiresUltrasound: false},
    ...['absolute', 'relative'].flatMap(mode => ['ultrasound', 'joint'].flatMap(arm =>
      ['ridge', 'recurrent'].map(family => ({
        id: `${arm}_${family}_${mode}`,
        label: `${arm === 'joint' ? 'Angle and ultrasound' : 'Ultrasound'} ${family}, ${mode === 'relative' ? 'centered tiles' : 'original tiles'}`,
        requiresUltrasound: true,
      })))),
  ].map(Object.freeze));
  const dimensions = {
    'conv.weight': width * channels * 3,
    'conv.bias': width,
    'recurrent.weight_ih_l0': 3 * width * width,
    'recurrent.weight_hh_l0': 3 * width * width,
    'recurrent.bias_ih_l0': 3 * width,
    'recurrent.bias_hh_l0': 3 * width,
    'shared_step.weight_ih': 3 * width * width,
    'shared_step.weight_hh': 3 * width * width,
    'shared_step.bias_ih': 3 * width,
    'shared_step.bias_hh': 3 * width,
    'out.weight': angles * width,
    'out.bias': angles,
  };

  // The FP64 arithmetic and FP32 state boundary follow the reaching browser runtime.
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
      state[cell] = candidate + retain * (state[cell] - candidate);
    }
  }

  function convolve(weights, padded, row, output) {
    const kernel = weights['conv.weight'];
    for (let channel = 0; channel < width; channel++) {
      let sum = 0;
      const start = channel * channels * 3;
      for (let col = 0; col < channels; col++) {
        const reading = row * channels + col;
        const coefficient = start + col * 3;
        sum += padded[reading] * kernel[coefficient];
        sum += padded[reading + channels] * kernel[coefficient + 1];
        sum += padded[reading + channels * 2] * kernel[coefficient + 2];
      }
      const linear = sum + weights['conv.bias'][channel];
      output[channel] = linear * sigmoid(linear);
    }
  }

  function learned(inputs, weights, scale) {
    const state = new Float32Array(width);
    const encoded = new Float64Array(width);
    const incoming = new Float64Array(3 * width);
    const hidden = new Float64Array(3 * width);
    const padded = new Float64Array(inputs.length + 2 * channels);
    padded.set(inputs, 2 * channels);
    for (let row = 0; row < frames; row++) {
      convolve(weights, padded, row, encoded);
      affine(weights['recurrent.weight_ih_l0'], weights['recurrent.bias_ih_l0'], encoded, incoming);
      step(incoming, state, weights['recurrent.weight_hh_l0'], weights['recurrent.bias_hh_l0'], hidden);
    }
    affine(weights['shared_step.weight_ih'], weights['shared_step.bias_ih'], state, incoming);
    for (let done = 0; done < passes; done++) {
      step(incoming, state, weights['shared_step.weight_hh'], weights['shared_step.bias_hh'], hidden);
    }
    const output = new Array(angles);
    affine(weights['out.weight'], weights['out.bias'], state, output);
    return output.map((value, i) => value * scale[i]);
  }

  function histories(history) {
    const cases = Array.isArray(history?.[0]?.[0]) ? history : [history];
    const columns = cases[0]?.[0]?.length;
    if (columns !== angles && columns !== channels) {
      throw new Error('Use ten rows with four angle fields or twenty angle and ultrasound fields.');
    }
    for (const one of cases) {
      if (!Array.isArray(one) || one.length !== frames || one.some(row => !Array.isArray(row) || row.length !== columns)) {
        throw new Error('Use ten rows with the same number of fields in every history.');
      }
      for (const row of one) {
        for (let col = 0; col < columns; col++) {
          if (!Number.isFinite(row[col])) throw new Error('Every input field needs a finite number.');
        }
      }
    }
    return {cases, columns};
  }

  function trend(history) {
    return Array.from({length: angles}, (_, finger) => {
      let total = 0;
      let slope = 0;
      for (let row = 5; row < 10; row++) {
        const value = history[row][finger];
        total += value;
        slope += (row - 7) * value;
      }
      // A centered fit on the last five frames, read eight intervals beyond the last angle.
      return total / 5 + slope - history[9][finger];
    });
  }

  function inputs(history, calibration, first, last, centered) {
    const values = new Float64Array(frames * channels);
    for (let row = 0; row < frames; row++) {
      for (let col = first; col < last; col++) {
        const origin = centered && col >= angles ? history[0][col] : 0;
        values[row * channels + col] = Math.fround((history[row][col] - origin - calibration.mean[col]) / calibration.scale[col]);
      }
    }
    return values;
  }

  function ridge(inputs, coefficients) {
    const result = new Array(angles).fill(0);
    for (let row = 0; row < inputs.length; row++) {
      for (let finger = 0; finger < angles; finger++) {
        result[finger] += inputs[row] * coefficients[(row + 1) * angles + finger];
      }
    }
    return result.map((value, i) => value + coefficients[i]);
  }

  const payload = globalThis.NeuroTranslateFingerAngleData;
  if (!payload) throw new Error('The finger-angle model file could not be loaded.');
  const groups = Object.fromEntries(Object.entries(payload.groups).map(([name, raw]) => [name, {
    calibration: raw.calibration,
    coefficient: decode(raw.coefficient, (frames * channels + 1) * angles, 8),
    weights: raw.weights.map(checkpoint => Object.fromEntries(Object.entries(dimensions).map(([key, count]) =>
      [key, decode(checkpoint[key], count, 4)]))),
  }]));

  function evaluate(group, one, estimates, seeds) {
    const {ridgeName, recurrentName, first, last, centered, name} = group;
    const {calibration, coefficient, weights} = groups[name];
    const past = inputs(one, calibration, first, last, centered);
    estimates[ridgeName].push(ridge(past, coefficient));
    const pair = weights.map((checkpoint, i) => {
      const result = learned(past, checkpoint, calibration.target_scale);
      seeds[`${recurrentName}_seed${payload.seeds[i]}`].push(result);
      return result;
    });
    estimates[recurrentName].push(pair[0].map((value, finger) => (value + pair[1][finger]) / 2));
  }

  const settings = [{name: 'angle', first: 0, last: angles, centered: false, ridgeName: 'angle_ridge', recurrentName: 'angle_recurrent'},
    ...['absolute', 'relative'].flatMap(mode => ['ultrasound', 'joint'].map(arm => ({
      name: `${arm}_${mode}`, first: arm === 'joint' ? 0 : angles, last: channels,
      centered: mode === 'relative', ridgeName: `${arm}_ridge_${mode}`, recurrentName: `${arm}_recurrent_${mode}`,
    })))];

  function forecast(history) {
    const {cases, columns} = histories(history);
    const applicable = methods.filter(method => columns === channels || !method.requiresUltrasound);
    const active = columns === channels ? settings : settings.slice(0, 1);
    const estimates = Object.fromEntries(applicable.map(method => [method.id, []]));
    const seeds = Object.fromEntries(active.flatMap(group => payload.seeds.map(seed =>
      [`${group.recurrentName}_seed${seed}`, []])));
    for (const one of cases) {
      estimates.zero_change.push([0, 0, 0, 0]);
      estimates.past_angle_trend.push(trend(one));
      for (const group of active) evaluate(group, one, estimates, seeds);
    }
    if ([...Object.values(estimates), ...Object.values(seeds)].some(rows => rows.some(row => !row.every(Number.isFinite)))) {
      throw new Error('The input values are too large to forecast.');
    }
    return {
      forecast_horizon_ms: 320,
      finger_order: fingers,
      change_in_angle_degrees: estimates,
      seed_change_in_angle_degrees: seeds,
    };
  }

  globalThis.NeuroTranslateFingerAngle = Object.freeze({forecast, methods, finger_order: fingers, field_order: fields});
}
