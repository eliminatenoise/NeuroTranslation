// SPDX-License-Identifier: CC0-1.0
"use strict";
const data = JSON.parse(document.getElementById("study").textContent);
const fingers = ["Thumb", "Index", "Middle", "Ring", "Little"];
const modes = ["cue", "cortex", "aligned"];
const times = [-120, -80, -40, 0];
const fields = {cue:[0,60], cortex:[60,152], aligned:[0,152]};
function decodeArray(spec) {
  const bytes = Uint8Array.from(atob(spec.bytes), s => s.charCodeAt(0));
  const view = new DataView(bytes.buffer);
  const size = spec.width;
  return Float64Array.from({length:bytes.byteLength / size}, (_, i) =>
    size === 8 ? view.getFloat64(size*i, true) : view.getFloat32(size*i, true));
}
const weights = Object.fromEntries(Object.entries(data.models).map(([k, arrays]) =>
  [k, Object.fromEntries(Object.entries(arrays).map(([name, spec]) => [name, decodeArray(spec)]))]));

function tokensFor(digit, phase, level) {
  const powers = data.powers[level];
  return times.map((lag,t) => {
    const seconds = (data.age + lag) / 1000, start = (phase * 5 + digit) * 6;
    const cue = Array(60).fill(0);
    cue[start] = 1;
    cue[start+1] = seconds;
    [0.4, 0.8, 1.2, 1.6].forEach((k, i) => { cue[start+2+i] = Math.max(0, seconds-k); });
    return cue.concat(powers[t]);
  });
}
// PyTorch linear-layer weights are stored in output-major order.
function linear(input, matrix, bias) {
  return Array.from(bias, (offset, j) => {
    let sum = offset;
    for (let i=0; i<input.length; i++) sum += matrix[j*input.length+i] * input[i];
    return sum;
  });
}
function ridge(tokens, mode, w) {
  const [lo,hi] = fields[mode], v = Array.from(w.intercept);
  let j = 0;
  for (const token of tokens) for (let i=lo; i<hi; i++, j++) {
    const x = (token[i] - w.mean[j]) / w.sd[j];
    for (let f=0; f<5; f++) v[f] += x * w.weights[j*5+f];
  }
  return v;
}
function norm(input, scale, shift) {
  const mean = input.reduce((a,b) => a+b, 0) / input.length;
  const variance = input.reduce((a,b) => a+(b-mean)**2, 0) / input.length;
  const inverseSD = 1 / Math.sqrt(variance + 1e-5);
  return input.map((v,i) => (v-mean)*inverseSD*scale[i]+shift[i]);
}
function gelu(x) {
  // Gaussian CDF via the five-term erf approximation (max erf error 1.5e-7).
  const a = Math.abs(x)/Math.SQRT2, t = 1/(1+0.3275911*a);
  const poly = (((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t;
  const erf = Math.sign(x)*(1-poly*Math.exp(-a*a));
  return x*0.5*(1+erf);
}
function attention(qkv, t) {
  const result = new Array(24);
  for (let head=0; head<2; head++) {
    const start = head*12;
    const logits = qkv.map(other => {
      let dot=0;
      for (let k=start; k<start+12; k++) dot += qkv[t][k]*other[24+k];
      return dot/Math.sqrt(12);
    });
    const peak = Math.max(...logits), exp = logits.map(x=>Math.exp(x-peak));
    const denominator = exp.reduce((a,b)=>a+b,0);
    for (let k=start; k<start+12; k++) {
      result[k] = qkv.reduce((sum, row, i) => sum+row[48+k]*exp[i]/denominator, 0);
    }
  }
  return result;
}
function transformer(tokens, mode, w) {
  const [lo,hi] = fields[mode];
  const p = name => w["param."+name];
  const project = (input,name) => linear(input,p(name+".weight"),p(name+".bias"));
  const hidden = tokens.map((token, t) => {
    const x = new Float32Array(152);
    for (let i=lo; i<hi; i++) x[i] = (token[i]-w.mean[i-lo])/w.sd[i-lo];
    return project(x,"project").map((v,i)=>v+p("pos")[t*24+i]);
  });
  const qkv = hidden.map(x => linear(x,p("layer.self_attn.in_proj_weight"),p("layer.self_attn.in_proj_bias")));
  // The readout uses only the last position. Earlier positions still contribute keys and values.
  const attended = project(attention(qkv,3),"layer.self_attn.out_proj");
  const layer1 = norm(hidden[3].map((v,i)=>v+attended[i]),p("layer.norm1.weight"),p("layer.norm1.bias"));
  const ff = project(project(layer1,"layer.linear1").map(gelu),"layer.linear2");
  const layer2 = norm(layer1.map((v,i)=>v+ff[i]),p("layer.norm2.weight"),p("layer.norm2.bias"));
  return project(layer2,"out");
}
function predict(digit, phase, level, family) {
  const tokens = tokensFor(digit, phase, level);
  return modes.map(mode => {
    const w = weights[family+"_"+mode];
    const z = family === "ridge" ? ridge(tokens,mode,w) : transformer(tokens,mode,w);
    return z.map((v,f)=>Math.max(0,v*w.ys[f]+w.ym[f]));
  });
}
