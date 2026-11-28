'use strict';

{
  const frames = 101;
  const angles = 4;
  const channels = 20;
  const width = 24;
  const passes = 3;
  const arms = [
    { name: 'angle', first: 0, last: angles },
    { name: 'ultrasound', first: angles, last: channels },
    { name: 'joint', first: 0, last: channels },
  ];
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

  // The causal convolution and GRU use the finger-angle browser arithmetic.
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
    return output.map((value, i) => Math.fround(value) * scale[i]);
  }

  const payload = globalThis.NeuroTranslateGestureModelData;
  if (!payload || payload.frames !== frames || payload.seeds[0] !== 20261126 || payload.seeds[1] !== 20261127) {
    throw new Error('The fitted gesture weights could not be loaded.');
  }
  const calibration = {
    mean: decode(payload.mean, channels, 8),
    scale: decode(payload.scale, channels, 8),
    target: decode(payload.target_scale, angles, 8),
  };
  if (!calibration.scale.every(value => value > 0) || !calibration.target.every(value => value > 0)) {
    throw new Error('The fitted model file contains an invalid scale.');
  }
  const fitted = arms.map(arm => {
    const data = payload.arms[arm.name];
    const features = (arm.last - arm.first) * frames;
    const coefficients = decode(data.coefficients, (features + 1) * angles, 8);
    if (data.weights.length !== 2) throw new Error('Both fitted weights must be present.');
    const weights = data.weights.map(state => Object.fromEntries(Object.entries(dimensions).map(([tensor, count]) =>
      [tensor, decode(state[tensor], count, 4)])));
    return { ...arm, coefficients, weights };
  });

  function validate(history) {
    if (!Array.isArray(history) || history.length !== frames) {
      throw new TypeError('Expected 101 consecutive recorded frames.');
    }
    const columns = history[0]?.length;
    if (columns !== angles && columns !== channels) {
      throw new TypeError('Use four angles or four angles followed by 16 logged ultrasound tiles.');
    }
    for (let row = 0; row < frames; row++) {
      const values = history[row];
      if (!Array.isArray(values) || values.length !== columns) {
        throw new TypeError('Every frame must have the same number of fields.');
      }
      for (let col = 0; col < columns; col++) {
        if (!Number.isFinite(values[col])) throw new TypeError('Every input field must be a finite number.');
      }
    }
    return columns;
  }

  function trend(history, latest) {
    return latest.map((angle, finger) => {
      let total = 0;
      let weighted = 0;
      for (let k = 0; k < 5; k++) {
        const value = history[frames - 5 + k][finger];
        total += value;
        weighted += (k - 2) * value;
      }
      const change = total / 5 + (weighted / 10) * 10 - angle;
      return angle + change;
    });
  }

  function normalize(history, arm) {
    const values = new Float32Array(frames * channels);
    for (let row = 0; row < frames; row++) {
      for (let col = arm.first; col < arm.last; col++) {
        const centered = col < angles ? history[row][col] : history[row][col] - history[0][col];
        const normalized = Math.fround((centered - calibration.mean[col]) / calibration.scale[col]);
        if (!Number.isFinite(normalized)) throw new RangeError('The input magnitude exceeds the fitted model’s numerical range.');
        values[row * channels + col] = normalized;
      }
    }
    return values;
  }

  function ridge(inputs, arm) {
    const result = new Array(angles).fill(0);
    let index = angles;
    for (let row = 0; row < frames; row++) {
      for (let col = arm.first; col < arm.last; col++) {
        const value = inputs[row * channels + col];
        for (let finger = 0; finger < angles; finger++) {
          result[finger] += value * arm.coefficients[index++];
        }
      }
    }
    return result.map((value, i) => value + arm.coefficients[i]);
  }

  function forecast(history) {
    const columns = validate(history);
    const latest = history[frames - 1].slice(0, angles);
    const estimates = { past_angle_trend: trend(history, latest) };
    for (const arm of columns === angles ? fitted.slice(0, 1) : fitted) {
      const values = normalize(history, arm);
      const first = learned(values, arm.weights[0], calibration.target);
      const second = learned(values, arm.weights[1], calibration.target);
      const linear = ridge(values, arm);
      estimates[`${arm.name}_ridge`] = latest.map((angle, i) => angle + linear[i]);
      estimates[`${arm.name}_recurrent`] = latest.map((angle, i) => angle + (first[i] + second[i]) / 2);
    }
    if (Object.values(estimates).some(values => !values.every(Number.isFinite))) {
      throw new RangeError('The forecast exceeds the numerical range.');
    }
    return estimates;
  }

  globalThis.NeuroTranslateGestureModels = Object.freeze({ forecast });
}
