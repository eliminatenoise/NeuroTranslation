/* Single-block temporal attention for ten chronological 20 ms bins. */
'use strict';
const compactWalking = (() => {
  const f32 = Math.fround;
  const {layout, models, reference, scale} = compactModelWeights;
  const cache = new Map();

  function parameters(key) {
    if (!Object.hasOwn(models, key)) throw new RangeError('Unknown model setting.');
    if (cache.has(key)) return cache.get(key);
    const bytes = Uint8Array.from(atob(models[key]), c => c.charCodeAt(0));
    const source = new DataView(bytes.buffer);
    const values = new Float32Array(bytes.length / 4);
    for (let i = 0; i < values.length; i++) values[i] = source.getFloat32(i * 4, true);
    const tensors = {};
    for (const [name, {offset, shape}] of Object.entries(layout)) {
      tensors[name] = values.subarray(offset, offset + shape.reduce((a, b) => a * b, 1));
    }
    cache.set(key, tensors);
    return tensors;
  }
  function linear(tensors, name, input) {
    const w = tensors[name + '.weight'], bias = tensors[name + '.bias'];
    const out = new Float32Array(bias.length);
    for (let i = 0; i < out.length; i++) {
      let sum = 0, start = i * input.length;
      for (let j = 0; j < input.length; j++) sum = f32(sum + w[start + j] * input[j]);
      out[i] = sum + bias[i];
    }
    return out;
  }
  function residualNorm(tensors, name, a, b) {
    const z = a.map((v, i) => v + b[i]);
    let sum = 0;
    for (const v of z) sum += v;
    const mean = f32(sum / z.length);
    let variance = 0;
    for (const v of z) variance += (v - mean) ** 2;
    const inverse = f32(1 / Math.sqrt(variance / z.length + 1e-5));
    const weight = tensors[name + '.weight'], bias = tensors[name + '.bias'];
    return z.map((v, i) => f32((v - mean) * inverse) * weight[i] + bias[i]);
  }
  const positions = Array.from({length: 10}, (_, t) => {
    const values = new Float32Array(32);
    for (let d = 0; d < values.length; d += 2) {
      const omega = f32(Math.exp(f32(d * f32(-Math.log(10000) / 32))));
      const phase = f32((t - 9) * omega);
      values[d] = Math.sin(phase);
      values[d + 1] = Math.cos(phase);
    }
    return values;
  });
  function checkMatrix(matrix, width) {
    return Array.isArray(matrix) && matrix.length === 10 && matrix.every(row =>
      Array.isArray(row) && row.length === width && row.every(Number.isFinite));
  }
  function predict(history, useForce, seed) {
    if (typeof useForce !== 'boolean' || ![2731, 4119].includes(seed)) throw new RangeError('Unknown model setting.');
    if (!checkMatrix(history.heel, 6) || !checkMatrix(history.force, 2)) throw new TypeError('Expected ten finite heel and force rows.');
    const name = 'attention_camera' + (useForce ? '_force' : '') + '__' + seed;
    const weights = parameters(name);
    const encoded = history.heel.map((xyz, t) => {
      const input = [...xyz.map(v => v / 200), ...history.force[t].map(v => useForce ? v / 500 : 0),
        1, 1, 1, 1, 1, 1, Number(useForce), Number(useForce)];
      return linear(weights, '0', Float32Array.from(input)).map((v, i) => v + positions[t][i]);
    });
    const last = encoded[9];
    const memory = [weights['1.null'], ...encoded];
    const q = linear(weights, '1.q', last);
    const keys = memory.map(x => linear(weights, '1.k', x));
    const values = memory.map(x => linear(weights, '1.v', x));
    const mixed = new Float32Array(32);
    for (let h = 0; h < 4; h++) {
      const first = h * 8;
      const scores = keys.map(k => {
        let dot = 0;
        for (let j = first; j < first + 8; j++) dot += f32(q[j] * k[j]);
        return f32(f32(dot) / Math.sqrt(8));
      });
      const peak = Math.max(...scores);
      const exp = scores.map(s => f32(Math.exp(f32(s - peak))));
      const total = f32(exp.reduce((a, b) => a + b, 0));
      const probabilities = exp.map(v => f32(v / total));
      for (let j = first; j < first + 8; j++) {
        let sum = 0;
        for (let t = 0; t < memory.length; t++) sum += f32(probabilities[t] * values[t][j]);
        mixed[j] = sum;
      }
    }
    const hidden = residualNorm(weights, '1.ln1', last, linear(weights, '1.proj', mixed));
    const activated = linear(weights, '1.ff1', hidden).map(v => Math.max(0, v));
    const state = residualNorm(weights, '1.ln2', hidden, linear(weights, '1.ff2', activated));
    const raw = Array.from(linear(weights, '2', state));
    const offsets = lastHeelChange(history).concat(reference);
    const natural = raw.map((v, i) => f32(f32(v * scale[i]) + f32(offsets[i])));
    for (let i = 6; i < 8; i++) natural[i] = Math.max(0, natural[i]);
    for (let i = 8; i < 10; i++) natural[i] = 1 / (1 + Math.exp(-Math.max(-700, Math.min(700, natural[i]))));
    return {raw, heel: [natural.slice(0, 3), natural.slice(3, 6)], impulse: natural.slice(6, 8), loadStart: natural.slice(8)};
  }
  function lastHeelChange(history) {
    return history.heel[9].map((v, i) => (v - history.heel[8][i]) * 5);
  }
  return Object.freeze({predict});
})();
