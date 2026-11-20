/* Portable, single-event inference. Weights follow the published [out, in] layout. */
"use strict";
const CervicalModel = (() => {
  const channels = ["Biceps", "SC6", "Thumb", "CP4", "ECG"];

  function inputRows(rows, count) {
    if (!Array.isArray(rows) || rows.length !== count ||
        !rows.every(row => Array.isArray(row) && row.length === channels.length && row.every(Number.isFinite))) {
      throw new TypeError("Expected " + count + " rows of five finite voltages.");
    }
  }
  function meanRows(rows) {
    return rows[0].map((_, column) => rows.reduce((sum, row) => sum + row[column], 0) / rows.length);
  }
  function toTokens(baseline, early) {
    inputRows(baseline, 50);
    inputRows(early, 30);
    const result = [];
    for (const window of [baseline, early]) {
      for (let start = 0; start < window.length; start += 5) {
        result.push(meanRows(window.slice(start, start + 5)));
      }
    }
    return result;
  }
  function dot(left, right) {
    let sum = 0;
    for (let i = 0; i < left.length; i++) sum += left[i] * right[i];
    return sum;
  }
  function linear(row, model, name) {
    return model[name + ".weight"].map((weights, i) => dot(row, weights) + model[name + ".bias"][i]);
  }
  function normalized(row, model, name) {
    const mean = row.reduce((sum, value) => sum + value, 0) / row.length;
    const variance = row.reduce((sum, value) => sum + (value - mean) ** 2, 0) / row.length;
    const scale = Math.sqrt(variance + 1e-5);
    return row.map((value, i) => (value - mean) / scale * model[name + ".weight"][i] + model[name + ".bias"][i]);
  }
  // erf power series near zero and the upper incomplete gamma continued fraction in the tail.
  function erf(value) {
    const magnitude = Math.abs(value);
    const z = magnitude * magnitude;
    if (magnitude > 7) return Math.sign(value);
    if (magnitude < 3) {
      let term = magnitude, sum = term;
      for (let n = 1; n < 90; n++) {
        term *= -z / n;
        const delta = term / (2 * n + 1);
        sum += delta;
        if (Math.abs(delta) < 1e-17) break;
      }
      return Math.sign(value) * 2 / Math.sqrt(Math.PI) * sum;
    }
    let b = z + 0.5, c = 1e30, d = 1 / b, fraction = d;
    for (let i = 1; i < 100; i++) {
      const a = -i * (i - 0.5);
      b += 2;
      d = 1 / (a * d + b);
      c = b + a / c;
      const delta = c * d;
      fraction *= delta;
      if (Math.abs(delta - 1) < 3e-15) break;
    }
    return Math.sign(value) * (1 - Math.exp(-z) * magnitude / Math.sqrt(Math.PI) * fraction);
  }
  function attend(queryRow, qkv) {
    const heads = [];
    for (let head = 0; head < 2; head++) {
      const offset = head * 8;
      const scores = qkv.map(keyRow => {
        let score = 0;
        for (let d = 0; d < 8; d++) score += queryRow[offset + d] * keyRow[16 + offset + d];
        return score / Math.sqrt(8);
      });
      const max = Math.max(...scores);
      const exps = scores.map(score => Math.exp(score - max));
      const total = exps.reduce((sum, x) => sum + x, 0);
      for (let d = 0; d < 8; d++) {
        heads.push(qkv.reduce((sum, valueRow, t) => sum + exps[t] / total * valueRow[32 + offset + d], 0));
      }
    }
    return heads;
  }
  function predict(tokens, eventIndex, weights, modelName) {
    inputRows(tokens, 16);
    if (!Number.isInteger(eventIndex) || eventIndex < 0 || eventIndex > 79) throw new RangeError("Event index must be 0–79.");
    if (!["eng", "noneng"].includes(modelName) || weights.schema_version !== 1 ||
        weights.channels.join("/") !== channels.join("/")) throw new Error("Unsupported model export.");
    const {transform} = weights;
    const model = weights.models[modelName];
    const embeddings = tokens.map((row, t) => {
      const p = t < 10 ? 0 : 1;
      const scaled = row.map((value, c) => c === 0 && (p === 0 || modelName === "noneng")
        ? 0 : (value - transform.mean[p][c]) / transform.sd[p][c]);
      scaled.push(eventIndex / 79);
      return linear(scaled, model, "embed").map((value, d) => value + model.position[t][d]);
    });
    const qkv = embeddings.map(row => linear(normalized(row, model, "norm1"), model, "qkv"));
    const outputs = embeddings.map((row, t) => {
      const attended = linear(attend(qkv[t], qkv), model, "mix").map((v, d) => v + row[d]);
      const hidden = linear(normalized(attended, model, "norm2"), model, "ff1");
      const activated = hidden.map(v => 0.5 * v * (1 + erf(v / Math.SQRT2)));
      const result = linear(activated, model, "ff2").map((v, d) => v + attended[d]);
      return normalized(result, model, "outnorm");
    });
    const result = linear(meanRows(outputs), model, "readout")[0] * transform.target_sd + transform.target_mean;
    if (!Number.isFinite(result)) throw new RangeError("The numerical result is outside the model’s range.");
    return result;
  }
  return {channels, toTokens, predict};
})();
if (typeof module !== "undefined" && module.exports) module.exports = CervicalModel;
