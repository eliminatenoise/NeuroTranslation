// Single-window, double-precision inference. Each token describes four consecutive rows.
"use strict";
globalThis.CylinderForecast = (() => {
  const axes = [0, 1, 2];
  const mean = values => values.reduce((sum, x) => sum + x, 0) / values.length;
  const plus = (a, b) => a.map((x, i) => x + b[i]);
  function dot(a, b) {
    let sum = 0;
    for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
    return sum;
  }
  function axisMean(rows) {
    return axes.map(axis => mean(rows.map(row => row[axis])));
  }
  function makeTokens({gyro, accel, time, hand, target}) {
    const validSensor = rows => Array.isArray(rows) && rows.length === 20 &&
      rows.every(row => row.length === 3 && row.every(Number.isFinite));
    if (!validSensor(gyro) || !validSensor(accel) || !Array.isArray(time) || time.length !== 20 ||
        !time.every((t, i) => Number.isFinite(t) && (!i || t > time[i - 1]))) {
      throw new RangeError("Expected twenty consecutive three-axis sensor samples in time order.");
    }
    if (!['left', 'right'].includes(hand) || !Number.isInteger(target) || target < 1 || target > 9) {
      throw new RangeError("Unknown hand or target.");
    }
    const side = Number(hand === 'right'), handTarget = Array(18).fill(0);
    handTarget[9 * side + target - 1] = 1;
    const tokens = [];
    for (let start = 0; start < 20; start += 4) {
      const end = start + 3;
      tokens.push([...gyro[end], ...axisMean(gyro.slice(start, end + 1)),
        ...accel[end], ...axisMean(accel.slice(start, end + 1)),
        time[end] + .01, 1 - side, side, ...handTarget]);
    }
    return tokens;
  }
  function normalize(raw, model) {
    return raw.map(row => row.map((value, i) => {
      const mode = model.mode;
      if (i < 6 && (mode === 'accel_task' || mode === 'task')) return 0;
      if (i >= 6 && i < 12 && (mode === 'gyro_task' || mode === 'task')) return 0;
      if (i >= 15 && mode === 'sensors') return 0;
      return Math.max(-10, Math.min(10, (value - model.x_mean[i]) / model.x_scale[i]));
    }));
  }
  function transformer(tokens, p) {
    const dense = (row, name) => p[name + '.weight'].map((w, i) => dot(w, row) + p[name + '.bias'][i]);
    function layerNorm(row, name) {
      const m = mean(row);
      const sd = Math.sqrt(mean(row.map(x => (x - m) ** 2)) + 1e-5);
      return row.map((x, i) => (x - m) / sd * p[name + '.weight'][i] + p[name + '.bias'][i]);
    }
    const embedded = tokens.map((row, i) => plus(dense(row, 'embed'), p.position[i]));
    const qkv = embedded.map(row => dense(row, 'qkv'));
    const attended = qkv.map((item, i) => {
      const out = [];
      for (let head = 0; head < 2; head++) {
        const at = head * 8;
        const query = item.slice(at, at + 8);
        const logits = qkv.map(key => dot(query, key.slice(16 + at, 24 + at)) / Math.sqrt(8));
        const top = Math.max(...logits);
        const weights = logits.map(x => Math.exp(x - top));
        const total = weights.reduce((a, b) => a + b, 0);
        for (let k = 0; k < 8; k++) {
          out.push(weights.reduce((sum, w, j) => sum + w * qkv[j][32 + at + k], 0) / total);
        }
      }
      return layerNorm(plus(embedded[i], dense(out, 'project')), 'attention_norm');
    });
    const last = attended.at(-1);
    const hidden = dense(last, 'expand').map(x => Math.max(x, 0));
    return dense(layerNorm(plus(last, dense(hidden, 'reduce')), 'final_norm'), 'out');
  }
  function fromTokens(model, tokens) {
    const x = normalize(tokens, model);
    let out;
    if (model.family === 'ridge') {
      out = model.parameters.bias.slice();
      x.flat().forEach((value, i) => {
        model.parameters.coefficient[i].forEach((c, j) => { out[j] += c * value; });
      });
    } else if (model.family === 'transformer') {
      out = transformer(x, model.parameters);
    } else throw new TypeError("Unknown model family.");
    if (model.mode === 'gyro_loss') out = out.slice(0, 3);
    return out.map((value, i) => value * model.y_scale[i] + model.y_mean[i]);
  }
  function predict(model, history) {
    return fromTokens(model, makeTokens(history));
  }
  function simple(history) {
    const recent = ['gyro', 'accel'].flatMap(k => axisMean(history[k].slice(10)));
    const prior = ['gyro', 'accel'].flatMap(k => axisMean(history[k].slice(0, 10)));
    return {persistence: recent, linear_trend: recent.map((value, i) => 2 * value - prior[i])};
  }
  function runAll(weights, history, donor, trainingMean) {
    const tokens = makeTokens(history);
    const donorTokens = donor ? makeTokens({...history, accel: donor.accel}) : null;
    const values = {...simple(history), hand_target_time_mean: trainingMean};
    for (const [key, model] of Object.entries(weights)) {
      values[key] = fromTokens(model, tokens);
      if (model.mode === 'full') {
        values[key.replace('full-', 'wrong-')] = donorTokens ? fromTokens(model, donorTokens) : null;
      }
    }
    return values;
  }
  return {predict, makeTokens, fromTokens, simple, runAll};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = globalThis.CylinderForecast;
