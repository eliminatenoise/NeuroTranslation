/* Three day-one movement forecasts share a measured body history. */
"use strict";
const WeekMovement = (() => {
  function linear(input, weights, layer) {
    const matrix = weights[layer + ".weight"], bias = weights[layer + ".bias"];
    return matrix.map((row, i) => {
      let sum = bias[i];
      for (let j = 0; j < row.length; j++) sum += row[j] * input[j];
      return sum;
    });
  }

  function normalize(input, weights, layer) {
    const average = input.reduce((sum, x) => sum + x, 0) / input.length;
    const variance = input.reduce((sum, x) => sum + (x - average) ** 2, 0) / input.length;
    const denominator = Math.sqrt(variance + 1e-5);
    return input.map((x, i) => (x - average) / denominator * weights[layer + ".weight"][i] + weights[layer + ".bias"][i]);
  }

  const add = (left, right) => left.map((v, i) => v + right[i]);
  const difference = (left, right) => left.map((v, i) => v - right[i]);
  const relu = input => input.map(v => Math.max(v, 0));
  const standardize = (row, mean, scale) => row.map((v, i) => (v - mean[i]) / scale[i]);

  function chunks(values, size) {
    const result = [];
    for (let i = 0; i < values.length; i += size) result.push(values.slice(i, i + size));
    return result;
  }

  // A single attention block feeds one readout. Compute that token's query
  // against every history key and value. Other output tokens are unused.
  function attend(rows, token, heads, weights) {
    const width = heads * 8, qkv = rows.map(row => linear(row, weights, "qkv"));
    const selected = qkv[token];
    const mixed = [];
    for (let head = 0; head < heads; head++) {
      const offset = head * 8;
      const logits = qkv.map(row => {
        let product = 0;
        for (let j = 0; j < 8; j++) product += selected[offset + j] * row[width + offset + j];
        return product / Math.sqrt(8);
      });
      const max = Math.max(...logits);
      const exponents = logits.map(value => Math.exp(value - max));
      const total = exponents.reduce((a, b) => a + b, 0);
      for (let j = 0; j < 8; j++) {
        mixed.push(qkv.reduce((sum, row, i) => sum + exponents[i] / total * row[2 * width + offset + j], 0));
      }
    }
    return linear(mixed, weights, "project");
  }

  function project(values, mean, scale, matrix) {
    const z = standardize(values, mean, scale), out = new Array(matrix[0].length).fill(0);
    for (let j = 0; j < z.length; j++) {
      for (let k = 0; k < out.length; k++) out[k] += z[j]*matrix[j][k];
    }
    return out;
  }
  function dense(x, w, bias) {
    return w.map((row, i) => row.reduce((sum, v, j) => sum + v*x[j], bias[i]));
  }
  function seed(history, cue, features, base, adapter) {
    const rows = history.map((pose, i) => {
      const body = [...pose, ...difference(pose, history[Math.max(0, i-1)])];
      const normalized = [...standardize(body, base.x_mean, base.x_scale),
        ...new Array(23).fill(0), ...standardize(cue[i], base.x_mean.slice(39), base.x_scale.slice(39))];
      return add(linear(normalized, base, "embed"), base.position[i]);
    });
    const attended = normalize(add(rows[19], attend(rows, 19, 3, base)), base, "attention_norm");
    const readout = normalize(add(attended, linear(relu(linear(attended, base, "expand")), base, "reduce")), base, "final_norm");
    const forecast = linear(readout, base, "out");
    const hidden = dense(features, adapter.in_weight, adapter.in_bias).map(Math.tanh);
    const correction = dense(hidden, adapter.out_weight, adapter.out_bias);
    return chunks(add(forecast, correction), 8)
      .map((row, t) => row.map((v, j) => v * base.y_scale[j] + base.y_mean[t][j]));
  }
  function predict(model, record, history) {
    const cfg = model.features;
    const body = [...history[19], ...history.slice(1).flatMap((row, i) => difference(row, history[i])),
      ...[4,9,14,19].flatMap(t => record.cueHistory[t])];
    const features = add(project(body,cfg.body_mean,cfg.body_scale,cfg.body_projection),
      project(record.pooledBins.flat().map(Math.log1p),cfg.count_mean,cfg.count_scale,cfg.count_projection));
    const paths = model.seeds.map(s => seed(history, record.cueHistory, features, s.base, s.adapter));
    return paths[0].map((row, t) => row.map((_, j) => history[19][j] + paths.reduce((sum, a) => sum + a[t][j], 0)/paths.length));
  }
  return {predict};
})();
