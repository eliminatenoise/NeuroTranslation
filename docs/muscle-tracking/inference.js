/* Standardized five-bin forecasts. Runs in a browser or Node. */
(() => {
  "use strict";
  const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);
  const add = (a, b) => a.map((value, i) => value + b[i]);
  function linear(x, weights, name) {
    const bias = weights[name + ".bias"];
    return weights[name + ".weight"].map((row, i) => dot(x, row) + bias[i]);
  }
  function normalize(x, weights, name, eps) {
    const mean = x.reduce((sum, v) => sum + v, 0) / x.length;
    const variance = x.reduce((sum, v) => sum + (v - mean) ** 2, 0) / x.length;
    const scale = 1 / Math.sqrt(variance + eps);
    return x.map((v, i) => (v - mean) * scale * weights[name + ".weight"][i] + weights[name + ".bias"][i]);
  }
  function finalAttention(embedded, weights, config) {
    const qkv = embedded.map(row => linear(row, weights, "qkv"));
    const width = config.width;
    const headWidth = width / config.heads;
    const last = qkv.at(-1);
    const context = [];
    for (let head = 0; head < config.heads; head++) {
      const offset = head * headWidth;
      const query = last.slice(offset, offset + headWidth);
      const scores = qkv.map(row => dot(query, row.slice(width + offset, width + offset + headWidth)) / Math.sqrt(headWidth));
      const max = Math.max(...scores);
      const exps = scores.map(v => Math.exp(v - max));
      const total = exps.reduce((s, v) => s + v, 0);
      for (let j = 0; j < headWidth; j++) {
        const index = 2 * width + offset + j;
        context.push(qkv.reduce((sum, row, i) => sum + exps[i] / total * row[index], 0));
      }
    }
    return linear(context, weights, "attn_out");
  }

  function validate(history) {
    for (const [key, count] of [["length", 21], ["angle", 20], ["alternate", 20]]) {
      const values = history[key];
      if (!Array.isArray(values) || values.length !== count || !values.every(Number.isFinite)) {
        throw new RangeError(`Enter ${count} finite numbers for the ${key} history.`);
      }
      if (key === "length" && values.some(value => value <= 0)) {
        throw new RangeError("Lengths must be greater than zero.");
      }
    }
  }

  function tokenize(length, angle) {
    return Array.from({length: 5}, (_, i) => {
      const start = i * 4;
      const end = start + 4;
      const mean = angle.slice(start, end).reduce((sum, value) => sum + value, 0) / 4;
      return [length[end], length[end] - length[start], mean, angle[end - 1] - angle[start]];
    });
  }

  function standardize(tokens, scaler) {
    return tokens.map(row => row.map((value, j) => (value - scaler.x_mean[j]) / scaler.x_sd[j]));
  }

  function transformer(tokens, weights, config) {
    const embedded = tokens.map((row, i) => add(linear(row, weights, "embed"), weights.pos[i]));
    const attended = finalAttention(embedded, weights, config);
    // A single encoder block. Only its final token enters the readout.
    const last = embedded.length - 1;
    const z = normalize(add(embedded[last], attended), weights, "norm1", config.eps);
    const hidden = linear(z, weights, "fc1").map(value => Math.max(0, value));
    return linear(normalize(add(z, linear(hidden, weights, "fc2")), weights, "norm2", config.eps), weights, "readout")[0];
  }

  function predict(bundle, history) {
    validate(history);
    const {length, angle, alternate} = history;
    const {scaler, baselines, models, config} = bundle;
    const full = standardize(tokenize(length, angle), scaler);
    const swapped = standardize(tokenize(length, alternate), scaler);
    const lengthOnly = full.map(row => [row[0], row[1], 0, 0]);
    const unscale = value => value * scaler.y_sd + scaler.y_mean;
    const cosine = degrees => Math.cos(degrees * (Math.PI / 180));
    const lastCos = cosine(angle[19]);
    const forecasts = {
      full: unscale(transformer(full, models.full, config)),
      length: unscale(transformer(lengthOnly, models.length, config)),
      wrong: unscale(transformer(swapped, models.full, config)),
      zero: 0,
      recent: length[20] - length[10],
      typical: baselines.typical,
      ridge: unscale(dot(full.flatMap(row => row.slice(0, 2)), baselines.ridge.weight) + baselines.ridge.bias),
      projection: Math.abs(lastCos) < 0.1 ? null : (length[19] * lastCos - length[9] * cosine(angle[9])) / lastCos
    };
    if (Object.values(forecasts).some(v => v !== null && !Number.isFinite(v))) {
      throw new RangeError("The calculation exceeds the available numeric precision. Use smaller values.");
    }
    return forecasts;
  }

  const api = {validate, tokenize, predict};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.FascicleModel = api;
})();
