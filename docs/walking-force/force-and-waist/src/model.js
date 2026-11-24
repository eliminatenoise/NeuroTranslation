/* Single-history attention adapted from the NeuroSurge browser forecast runtime.
   Dense weights follow the published NeuroTranslate 0.0 checkpoint layout. */
const ForceWaist = (() => {
  const WIDTH = 32;
  const HEAD_WIDTH = 8;
  const STEPS = 10;
  const f32 = Math.fround;
  const methods = ['latest_mean', 'linear_trend', 'fit_ridge', 'joint_attention'];

  function unpack(record) {
    const bytes = Uint8Array.from(atob(record.data), value => value.charCodeAt(0));
    const binary = new DataView(bytes.buffer);
    const words = record.shape.reduce((extent, size) => extent * size, 1);
    const small = record.dtype === 'float32';
    const step = small ? 4 : 8;
    if ((!small && record.dtype !== 'float64') || bytes.length !== step * words) {
      throw new Error('The embedded checkpoint has an invalid tensor.');
    }
    const array = small ? new Float32Array(words) : new Float64Array(words);
    for (let i = 0; i < words; i++) {
      array[i] = small ? binary.getFloat32(step * i, true) : binary.getFloat64(step * i, true);
    }
    return array;
  }

  function create(payload) {
    const weights = Object.fromEntries(Object.entries(payload.tensors).map(([key, value]) => [key, unpack(value)]));
    const frequencies = Float32Array.from({ length: WIDTH / 2 }, (_, i) =>
      f32(Math.exp(f32(2 * i * f32(-Math.log(10000) / WIDTH)))));
    const positions = Array.from({length: STEPS}, (_, time) => Float32Array.from({length: WIDTH}, (_, i) => {
      const phase = f32((time + 1 - STEPS) * frequencies[Math.floor(i / 2)]);
      return i % 2 ? Math.cos(phase) : Math.sin(phase);
    }));

    function linear(name, input) {
      const matrix = weights[name + '.weight'];
      return weights[name + '.bias'].map((bias, output) => {
        let sum = 0;
        const row = output * input.length;
        for (let i = 0; i < input.length; i++) sum += input[i] * matrix[row + i];
        return f32(sum) + bias;
      });
    }

    function layerNorm(name, residual, update) {
      const values = residual.map((value, i) => value + update[i]);
      const mean = f32(values.reduce((sum, value) => sum + value, 0) / WIDTH);
      const centered = values.map(value => value - mean);
      const variance = f32(centered.reduce((sum, value) => sum + f32(value * value), 0) / WIDTH);
      const scale = f32(Math.sqrt(f32(variance + 1e-5)));
      return centered.map((value, i) =>
        f32(f32(value / scale) * weights[name + '.weight'][i]) + weights[name + '.bias'][i]);
    }

    function attention(task, tokens) {
      const sequence = tokens.map((row, time) =>
        linear('adapters.' + task, row).map((value, i) => value + positions[time][i]));
      const latest = sequence.at(-1);
      const query = linear('trunk.q', latest);
      const memory = [weights['trunk.null'], ...sequence];
      const keys = memory.map(row => linear('trunk.k', row));
      const values = memory.map(row => linear('trunk.v', row));
      const pooled = new Float32Array(WIDTH);
      for (let first = 0; first < WIDTH; first += HEAD_WIDTH) {
        const last = first + HEAD_WIDTH;
        const scores = keys.map(key => {
          let dot = 0;
          for (let i = first; i < last; i++) dot += f32(query[i] * key[i]);
          return f32(f32(dot) / f32(Math.sqrt(HEAD_WIDTH)));
        });
        const top = Math.max(...scores);
        const exponentials = scores.map(value => Math.exp(f32(value - top)));
        const denominator = exponentials.reduce((sum, value) => sum + value, 0);
        for (let i = first; i < last; i++) {
          pooled[i] = values.reduce((sum, value, j) => sum + f32(exponentials[j] * value[i] / denominator), 0);
        }
      }
      const attended = layerNorm('trunk.ln1', latest, linear('trunk.proj', pooled));
      const expanded = linear('trunk.ff1', attended).map(value => Math.max(value, 0));
      const encoded = layerNorm('trunk.ln2', attended, linear('trunk.ff2', expanded));
      return linear('outputs.' + task, encoded);
    }

    function predict(task, rows) {
      const schema = payload.schemas[task];
      if (!schema || !Array.isArray(rows) || rows.length !== STEPS) {
        throw new Error('Use one complete 10-row force or waist history.');
      }
      const channels = schema.channels.length;
      if (rows.some(row => !Array.isArray(row) || row.length !== channels ||
          row.some(value => typeof value !== 'number' || !Number.isFinite(f32(value))))) {
        throw new Error('Enter a finite number for every reading.');
      }
      const means = weights[task + '.xmean'];
      const scales = weights[task + '.xscale'];
      const normalize = (value, i) => f32((value - means[i]) / scales[i]);
      const tokens = rows.map(row => {
        const token = new Float32Array(channels * 2);
        row.forEach((value, i) => { token[i] = normalize(f32(value), i); });
        token.fill(1, channels);
        return token;
      });
      const design = [1, ...rows.flatMap(row => row.map(normalize))];
      const coefficients = weights[task + '.ridge'];
      const outs = schema.outputs.length;
      const restore = (value, i) => value * weights[task + '.yscale'][i] + weights[task + '.ymean'][i];
      const ridge = Array.from({length: outs}, (_, i) =>
        restore(design.reduce((sum, value, j) => sum + value * coefficients[j * outs + i], 0), i));
      const readout = Array.from(attention(task, tokens), restore);
      const endpoint = row => task === 'force' ? [row[0] / 10] : row.slice(3);
      const latest = endpoint(rows.at(-1));
      const before = endpoint(rows.at(-2));
      const trend = latest.map((value, i) => value + 3 * (value - before[i]));
      const forecasts = [latest, trend, ridge, readout];
      if (!forecasts.every(out => out.every(Number.isFinite))) {
        throw new Error('Input values exceed the numerical range of the forecast.');
      }
      return forecasts;
    }

    return { predict, methods };
  }

  return { create };
})();
if (typeof module === 'object') module.exports = ForceWaist;
