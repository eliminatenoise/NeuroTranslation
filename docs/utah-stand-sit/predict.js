/* Force history and temporal attention for ten chronological 20 ms bins. */
'use strict';
globalThis.standSitForce = (() => {
  const f32 = Math.fround;
  const config = globalThis.standSitForceWeights;
  const parameters = config.models.map(encoded => {
    const bytes = Uint8Array.from(atob(encoded), letter => letter.charCodeAt(0));
    const source = new DataView(bytes.buffer);
    const values = new Float32Array(bytes.length / 4);
    for (let i = 0; i < values.length; i++) values[i] = source.getFloat32(i * 4, true);
    const result = {};
    for (const [key, [offset, length]] of Object.entries(config.layout)) {
      result[key] = values.subarray(offset, offset + length);
    }
    return result;
  });

  function linear(tensors, name, input) {
    const weights = tensors[name + '.weight'];
    const bias = tensors[name + '.bias'];
    const output = new Float32Array(bias.length);
    for (let i = 0; i < output.length; i++) {
      let sum = 0;
      for (let j = 0; j < input.length; j++) sum = f32(sum + weights[i * input.length + j] * input[j]);
      output[i] = sum + bias[i];
    }
    return output;
  }

  function residualNorm(tensors, name, a, b) {
    const z = a.map((value, i) => value + b[i]);
    const mean = f32(z.reduce((sum, value) => sum + value, 0) / z.length);
    const variance = z.reduce((sum, value) => sum + (value - mean) ** 2, 0) / z.length;
    const inverse = f32(1 / Math.sqrt(variance + 1e-5));
    const weight = tensors[name + '.weight'], bias = tensors[name + '.bias'];
    return z.map((value, i) => f32((value - mean) * inverse) * weight[i] + bias[i]);
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

  function residual(history, weights) {
    const encoded = history.map((row, t) => {
      const input = Float32Array.from(row.map((value, i) => (value - config.centerN[i]) / config.scaleN[i]));
      return linear(weights, 'force', input).map((value, i) => value + positions[t][i]);
    });
    const last = encoded[9];
    const memory = [weights['temporal.null'], ...encoded];
    const query = linear(weights, 'temporal.q', last);
    const keys = memory.map(row => linear(weights, 'temporal.k', row));
    const values = memory.map(row => linear(weights, 'temporal.v', row));
    const mixture = new Float32Array(32);
    for (let head = 0; head < 4; head++) {
      const start = head * 8;
      const scores = keys.map(key => {
        let dot = 0;
        for (let i = start; i < start + 8; i++) dot += f32(query[i] * key[i]);
        return f32(f32(dot) / Math.sqrt(8));
      });
      const peak = Math.max(...scores);
      const exponentials = scores.map(value => f32(Math.exp(f32(value - peak))));
      const total = f32(exponentials.reduce((a, b) => a + b, 0));
      const probabilities = exponentials.map(value => f32(value / total));
      for (let i = start; i < start + 8; i++) {
        let sum = 0;
        for (let t = 0; t < memory.length; t++) sum += f32(probabilities[t] * values[t][i]);
        mixture[i] = sum;
      }
    }
    const hidden = residualNorm(weights, 'temporal.ln1', last, linear(weights, 'temporal.proj', mixture));
    const active = linear(weights, 'temporal.ff1', hidden).map(value => Math.max(0, value));
    const state = residualNorm(weights, 'temporal.ln2', hidden, linear(weights, 'temporal.ff2', active));
    return linear(weights, 'output', state);
  }

  function predict(history) {
    if (!Array.isArray(history) || history.length !== 10 || !history.every(row =>
      Array.isArray(row) && row.length === 2 && row.every(Number.isFinite))) {
      throw new TypeError('Enter ten pairs of finite force readings.');
    }
    const persistence = history[9].map(value => value * 0.1);
    const dampedTrend = persistence.map((value, plate) => {
      const dot = config.trend.centred.reduce((sum, time, i) => sum + history[i + 5][plate] * time, 0);
      return value + (dot / config.trend.denominator) * config.trend.meanGrowth * 0.1;
    });
    const meanTotal = at => (history[at][0] + history[at + 1][0]) / 2 + (history[at][1] + history[at + 1][1]) / 2;
    const loadChangeN = meanTotal(8) - meanTotal(0);
    const rising = loadChangeN > 50;
    const attention = dampedTrend.slice();
    if (rising) {
      const bySeed = parameters.map(weights => residual(history, weights));
      for (let plate = 0; plate < 2; plate++) {
        attention[plate] += config.residualNs * (bySeed[0][plate] + bySeed[1][plate]) / 2;
      }
    }
    if (![...persistence, ...dampedTrend, ...attention, loadChangeN].every(Number.isFinite)) {
      throw new RangeError('These force readings are outside the numeric range.');
    }
    return {persistence, dampedTrend, attention, rising, loadChangeN};
  }
  return Object.freeze({predict});
})();
