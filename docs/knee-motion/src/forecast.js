// Five past observations per joint. The reference implementation is predict.py.
const methods = ["persistence", "slope", "knee_ridge", "all_ridge", "transformer"];
const labels = {
  persistence: "Keep last angle",
  slope: "Continue last slope",
  knee_ridge: "Linear · knees",
  all_ridge: "Linear · all joints",
  transformer: "Transformer",
};
const channels = ["right hip", "left hip", "right knee", "left knee", "right ankle", "left ankle"];
const lags = [24, 18, 12, 6, 0];

function historyRows(history) {
  if (!Array.isArray(history) || history.length !== 5 ||
      !history.every(row => Array.isArray(row) && row.length === 6 && row.every(Number.isFinite))) {
    throw Error("Use five rows of six finite numbers in degrees, from oldest to newest.");
  }
  return history;
}

function dot(a, b) {
  let result = 0;
  for (let i = 0; i < a.length; i++) result += a[i] * b[i];
  return result;
}

function sumVectors(a, b) {
  return a.map((value, i) => value + b[i]);
}

function attentionForecast(x, fit) {
  const state = fit.state;
  function affine(row, name) {
    return state[name + ".weight"].map((w, i) => dot(w, row) + state[name + ".bias"][i]);
  }
  function normalize(row, name) {
    const mean = row.reduce((total, v) => total + v, 0) / row.length;
    const centered = row.map(v => v - mean);
    const sd = Math.sqrt(dot(centered, centered) / row.length + 1e-5);
    return centered.map((v, i) => v / sd * state[name + ".weight"][i] + state[name + ".bias"][i]);
  }
  const hidden = x.map((row, t) => {
    const z = row.map((v, i) => (v - fit.mean[i]) / fit.scale[i]);
    return sumVectors(affine(z, "project"), state.position[t]);
  });
  const qkv = hidden.map(row => affine(normalize(row, "attention_norm"), "qkv"));
  // With one block and a last-token readout, only the last attention query
  // contributes. Keys and values from all five historical tokens still enter.
  const mixed = [];
  for (let head = 0; head < 4; head++) {
    const start = head * 6;
    const q = qkv[4].slice(start, start + 6);
    const scores = qkv.map(token => dot(q, token.slice(24 + start, 30 + start)) / Math.sqrt(6));
    const maxScore = Math.max(...scores);
    const exp = scores.map(v => Math.exp(v - maxScore));
    const total = exp.reduce((a, b) => a + b, 0);
    for (let i = 0; i < 6; i++) {
      mixed.push(qkv.reduce((sum, token, t) => sum + token[48 + start + i] * exp[t] / total, 0));
    }
  }
  const attended = sumVectors(hidden[4], affine(mixed, "attention_out"));
  const ff = affine(normalize(attended, "ff_norm"), "ff_in").map(v => Math.max(0, v));
  return affine(normalize(sumVectors(attended, affine(ff, "ff_out")), "last_norm"), "readout").map(v => v * 20);
}

function kneeForecast(history, weights, method) {
  const x = historyRows(history);
  const last = x[4].slice(2, 4);
  let result;
  switch (method) {
    case "persistence": result = last; break;
    case "slope": result = last.map((v, i) => v + 2.5 * (v - x[3][i + 2])); break;
    case "transformer": result = sumVectors(last, attentionForecast(x, weights.transformer)); break;
    case "knee_ridge":
    case "all_ridge": {
      const fit = weights[method];
      const features = method === "knee_ridge" ? x.flatMap(row => row.slice(2, 4)) : x.flat();
      const z = features.map((v, i) => (v - fit.mean[i]) / fit.scale[i]);
      result = last.map((v, i) => v + fit.intercept[i] + z.reduce((sum, fv, j) => sum + fv * fit.coef[j][i], 0));
      break;
    }
    default: throw Error("Unrecognized forecast method.");
  }
  if (!result.every(Number.isFinite)) throw Error("These numbers exceed the supported calculation range.");
  return result;
}
