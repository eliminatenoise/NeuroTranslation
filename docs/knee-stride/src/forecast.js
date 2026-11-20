// Inputs end at the cutoff. The copied pair comes from 15 frames beyond
// the corresponding point in an earlier stride, still inside that history.
const methods = ["prior_stride", "ridge_residual", "transformer_residual"];
const labels = {prior_stride:"Repeat the stride", ridge_residual:"Linear correction", transformer_residual:"Transformer correction"};

function sampleStride(history) {
  if (history.length !== 240 || !history.every(row => row.length === 2 && row.every(Number.isFinite))) {
    throw Error("Each forecast needs 240 consecutive pairs of finite knee angles.");
  }
  let best = 45, least = Infinity;
  for (let lag = 45; lag <= 180; lag++) {
    let distance = 0;
    for (let i = 180; i < 240; i++) {
      const r = history[i][0] - history[i - lag][0];
      const l = history[i][1] - history[i - lag][1];
      distance += r*r + l*l;
    }
    if (distance < least) { least = distance; best = lag; }
  }
  return best;
}
function strideTokens(history, lag) {
  const diff = i => history[i].map((v,k) => v - history[i-3][k]);
  return [-54,-42,-30,-21,-15,-9,-6,-3,0].map(offset => {
    const j = 239 + offset, earlier = j - lag;
    return [...history[j], ...history[earlier], ...history[earlier+15], ...diff(j), ...diff(earlier), lag];
  });
}
function dot(a, b) {
  let result = 0;
  for (let i = 0; i < a.length; i++) result += a[i] * b[i];
  return result;
}
function add(a,b) { return a.map((v,i) => v+b[i]); }

function transformerCorrection(tokens, state) {
  function affine(row, name) {
    return state[name+".weight"].map((w, i) => dot(w, row) + state[name+".bias"][i]);
  }
  function normalize(row, name) {
    const mean = row.reduce((total, v) => total+v, 0) / row.length;
    const centered = row.map(v => v-mean);
    const sd = Math.sqrt(dot(centered,centered)/row.length + 1e-5);
    return centered.map((v,i) => v/sd*state[name+".weight"][i] + state[name+".bias"][i]);
  }
  const hidden = tokens.map((row,t) => add(affine(row,"project"), state.position[t]));
  const qkv = hidden.map(row => affine(normalize(row,"attention_norm"),"qkv"));
  // Only the final query reaches the one-block last-token readout.
  const mixed = [];
  for (let head = 0; head < 4; head++) {
    const start = head*6;
    const q = qkv[8].slice(start,start+6);
    const scores = qkv.map(token => dot(q,token.slice(24+start,30+start)) / Math.sqrt(6));
    const peak = Math.max(...scores);
    const exp = scores.map(v => Math.exp(v-peak));
    const total = exp.reduce((a,b) => a+b,0);
    for (let i = 0; i < 6; i++) mixed.push(qkv.reduce((sum,token,t) => sum+token[48+start+i]*exp[t]/total,0));
  }
  const attended = add(hidden[8],affine(mixed,"attention_out"));
  const ff = affine(normalize(attended,"ff_norm"),"ff_in").map(v => Math.max(0,v));
  return affine(normalize(add(attended, affine(ff,"ff_out")),"last_norm"),"readout").map(v => v*10);
}
function forecast(history, weights) {
  const period = sampleStride(history);
  const base = history[239+15-period].slice();
  const normalized = strideTokens(history,period).map(row => row.map((v,c) => (v-weights.mean[c])/weights.scale[c]));
  const fit = weights.ridge;
  const z = normalized.flat().map((v,i) => v-fit.center[i]);
  const linear = fit.intercept.map((v,c) => v+z.reduce((s,value,i) => s+value*fit.coef[i][c],0));
  const result = {period_frames:period, prior_stride:base, ridge_residual:add(base,linear),
    transformer_residual:add(base,transformerCorrection(normalized,weights.transformer))};
  if (!methods.every(m => result[m].every(Number.isFinite))) throw Error("The forecast exceeded the numeric range.");
  return result;
}
