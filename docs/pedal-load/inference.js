/* Single-block encoder. Each call forecasts one endpoint from the preceding 201 samples. */
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

  function transformer(tokens, weights, config) {
    const embedded = tokens.map((row, i) => add(linear(row, weights, "embed"), weights.pos[i]));
    const attended = finalAttention(embedded, weights, config);
    // A single encoder block. Only its final token enters the readout.
    const last = embedded.length - 1;
    const z = normalize(add(embedded[last], attended), weights, "norm1", config.eps);
    const hidden = linear(z, weights, "fc1").map(value => Math.max(0, value));
    return linear(normalize(add(z, linear(hidden, weights, "fc2")), weights, "norm2", config.eps), weights, "readout")[0];
  }

  function validate(history) {
    for (const key of ["load", "emg", "donor"]) {
      if (!Array.isArray(history[key]) || history[key].length !== 201 || !history[key].every(Number.isFinite)) {
        throw new RangeError(`Enter exactly 201 finite readings for the ${key} trace.`);
      }
    }
    if (history.angle5 !== 0 && history.angle5 !== 1) throw new RangeError("Choose one of the two pedal settings.");
  }
  function tokens(load, emg, angle5) {
    return Array.from({length: 10}, (_, bin) => {
      const start = bin * 20, end = start + 20;
      const readings = emg.slice(start, end + 1);
      const mean = readings.reduce((s, x) => s + x, 0) / 21;
      const sd = Math.sqrt(readings.reduce((s, x) => s + (x - mean) ** 2, 0) / 21);
      let diffSquares = 0;
      for (let i = start + 1; i <= end; i++) diffSquares += (emg[i] - emg[i - 1]) ** 2;
      const step = load[end] - load[start];
      return [load[end], step, load[end] - load[0], angle5, mean, sd, Math.sqrt(diffSquares / 20), sd * step];
    });
  }
  function scale(raw, scaler) {
    return raw.map(row => row.map((x, k) => {
      if (!Number.isFinite(x)) throw new RangeError("These readings exceed the calculation’s numeric range.");
      return k === 3 ? x : Math.max(-8, Math.min(8, (x - scaler.mean[k]) / scaler.scale[k]));
    }));
  }
  function predict(bundle, history) {
    validate(history);
    const {load, emg, donor, angle5} = history;
    const {scaler, config, baselines, models, variants} = bundle;
    const original = scale(tokens(load, emg, angle5), scaler);
    const alternate = scale(tokens(load, donor, angle5), scaler);
    const unscale = x => x * scaler.y_scale + scaler.y_mean;
    const fitted = (rows, key) => {
      const keep = variants[key];
      const masked = rows.map(row => row.map((v, j) => keep.includes(j) ? v : 0));
      return unscale(transformer(masked, models[key], config));
    };
    const loadTerms = original.flatMap(row => row.slice(0, 3));
    const ridge = (values, fit) => unscale(dot(values, fit.weight) + fit.bias);
    const estimates = {
      full: fitted(original, "full"), load_condition: fitted(original, "load_condition"),
      emg_condition: fitted(original, "emg_condition"), load: fitted(original, "load"),
      wrong: fitted(alternate, "full"), ridge_load: ridge(loadTerms, baselines.ridge_load),
      ridge_condition: ridge([...loadTerms, angle5], baselines.ridge_condition),
      zero: 0, continue: load[200] - load[100], typical: baselines.typical,
      typical_condition: baselines.typical_condition[angle5]
    };
    if (!Object.values(estimates).every(Number.isFinite)) throw new RangeError("These readings exceed the calculation’s numeric range.");
    return estimates;
  }
  const api = {predict, validate, tokens};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.PedalForecast = api;
})();
