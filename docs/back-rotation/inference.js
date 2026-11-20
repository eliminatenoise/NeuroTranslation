/* One 10-bin history, row-major training weights. Also usable from Node. */
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
  function attention(embedded, weights, config) {
    const qkv = embedded.map(row => linear(row, weights, "qkv"));
    const width = config.width;
    const headWidth = width / config.heads;
    const output = [];
    for (let i = 0; i < embedded.length; i++) {
      const context = [];
      for (let h = 0; h < config.heads; h++) {
        const start = h * headWidth;
        const query = qkv[i].slice(start, start + headWidth);
        const scores = qkv.map(row => dot(query, row.slice(width + start, width + start + headWidth)) / Math.sqrt(headWidth));
        const highest = Math.max(...scores);
        const exps = scores.map(v => Math.exp(v - highest));
        const total = exps.reduce((s, v) => s + v, 0);
        for (let j = 0; j < headWidth; j++) {
          const index = 2 * width + start + j;
          context.push(qkv.reduce((sum, row, k) => sum + exps[k] / total * row[index], 0));
        }
      }
      output.push(linear(context, weights, "attn_out"));
    }
    return output;
  }
  function validatedTokens(rows) {
    if (!Array.isArray(rows) || rows.length !== 10 ||
        !rows.every(r => Array.isArray(r) && r.length === 9 && r.every(Number.isFinite))) {
      throw new TypeError("Each history needs ten rows of nine finite numbers.");
    }
    if (![0, 1].includes(rows[0][2]) || !rows.every(r => r[2] === rows[0][2])) {
      throw new TypeError("Each history needs one consistent standing or movement flag.");
    }
    return rows;
  }
  function inputFor(mode, original, donor) {
    validatedTokens(original);
    if (mode !== "wrong") return original;
    validatedTokens(donor);
    if (!donor.every((row, i) => row[2] === original[i][2])) throw new RangeError("The donor task must match.");
    return original.map((r, i) => r.slice(0, 3).concat(donor[i].slice(3)));
  }
  function predict(bundle, mode, original, donor) {
    const weights = bundle.models[mode === "wrong" ? "full" : mode];
    if (!weights) throw new RangeError("Choose a trained input set.");
    const input = inputFor(mode, original, donor);
    const norm = input.map(row => row.map((v, col) => {
      const voltageOmitted = col >= 3 && (mode === "motion" || (mode === "lower" && col < 6) || (mode === "upper" && col >= 6));
      if (voltageOmitted) return 0;
      return Math.min(8, Math.max(-8, (v - bundle.scaler.mean[col]) / bundle.scaler.scale[col]));
    }));
    const embedded = norm.map((row, i) => add(linear(row, weights, "embed"), weights.pos[i]));
    const layer = attention(embedded, weights, bundle.config);
    const eps = bundle.config.eps;
    const final = embedded.map((row, i) => {
      const z = normalize(add(row, layer[i]), weights, "norm1", eps);
      const hidden = linear(z, weights, "fc1").map(v => Math.max(0, v));
      return normalize(add(z, linear(hidden, weights, "fc2")), weights, "norm2", eps);
    });
    const estimate = original[9][1] + linear(final[9], weights, "readout")[0];
    if (!Number.isFinite(estimate)) throw new Error("The model produced an invalid forecast.");
    return Math.max(0, Math.min(180, estimate));
  }
  const api = {inputFor, predict};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.BackRotationModel = api;
})();
