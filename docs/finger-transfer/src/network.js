// SPDX-License-Identifier: CC0-1.0
"use strict";
const study = JSON.parse(document.getElementById("study").textContent);
const fingers = ["Thumb", "Index", "Middle", "Ring", "Little"];
const areas = [
  [1, "Dorsal motor"], [2, "Rolandic"], [3, "Dorsal sensory"], [4, "Ventral sensorimotor"],
  [6, "Other frontal"], [7, "Other parietal"], [8, "Temporal"], [9, "Occipital"]
];
const fields = {cue: [0, 60], cortex: [60, 85], aligned: [0, 85]};
const gains = [12, 20, 15, 16, 10];  // Invented scales from the public example.
function unpack([width, encoded]) {
  const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
  const view = new DataView(bytes.buffer);
  return Float64Array.from({length: bytes.length / width}, (_, i) =>
    width === 8 ? view.getFloat64(i*width, true) : view.getFloat32(i*width, true));
}
const weights = Object.fromEntries(Object.entries(study.weights).map(([key, packed]) =>
  [key, Object.fromEntries(Object.entries(packed).map(([name, array]) => [name, unpack(array)]))]));

function tokensFor(s) {
  const area = areas.findIndex(([code]) => code === s.region);
  return [-120, -80, -40, 0].map((lag, time) => {
    const token = new Float32Array(85);
    const at = 6 * (5*s.phase + s.digit - 1);
    const elapsed = (s.tick*40 + lag) / 1000;
    token[at] = 1;
    token[at+1] = elapsed;
    [0.4, 0.8, 1.2, 1.6].forEach((k, j) => { token[at+2+j] = Math.max(0, elapsed-k); });
    if (s.mask[area]) {
      token[60+area] = s.low*(time+1)/4;
      token[68+area] = s.high*(time+1)/4;
    }
    s.mask.forEach((present, j) => { token[76+j] = Number(present); });
    token[84] = Number(s.unknown);
    return token;
  });
}
function ridge(tokens, mode, w) {
  const [lo, hi] = fields[mode];
  const out = Array.from(w.intercept);
  let col = 0;
  for (const token of tokens) for (let i=lo; i<hi; i++, col++) {
    const value = (token[i] - w.mean[col]) / w.sd[col];
    for (let j=0; j<5; j++) out[j] += value*w.beta[col*5+j];
  }
  return out.map(v => Math.max(0,v));
}
function linear(x, matrix, bias) {
  return Array.from(bias, (offset, j) => {
    let sum = offset;
    for (let i=0; i<x.length; i++) sum += matrix[j*x.length+i]*x[i];
    return sum;
  });
}
function norm(x, scale, shift) {
  const mean = x.reduce((a,b) => a+b, 0) / x.length;
  const variance = x.reduce((a,b) => a+(b-mean)**2, 0) / x.length;
  return x.map((v,i) => (v-mean)/Math.sqrt(variance + 1e-5)*scale[i] + shift[i]);
}
function gelu(x) {
  const a=Math.abs(x)/Math.SQRT2, t=1/(1+0.3275911*a);
  const poly = (((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t;
  return 0.5*x*(1+Math.sign(x)*(1-poly*Math.exp(-a*a)));
}
function lastAttention(qkv) {
  const result = new Array(16);
  for (let head=0; head<2; head++) {
    const start=head*8;
    const logits=qkv.map(row => {
      let sum=0;
      for (let i=start; i<start+8; i++) sum += qkv[3][i]*row[16+i];
      return sum/Math.sqrt(8);
    });
    const peak=Math.max(...logits);
    const exp=logits.map(a => Math.exp(a-peak));
    const total=exp.reduce((a,b) => a+b, 0);
    for (let i=start; i<start+8; i++) {
      result[i]=qkv.reduce((sum,row,t) => sum+row[32+i]*exp[t]/total, 0);
    }
  }
  return result;
}
function transformer(tokens, mode, w) {
  const [lo, hi]=fields[mode];
  const param=name => w["param."+name];
  const project=(x,name) => linear(x,param(name+".weight"),param(name+".bias"));
  const hidden=tokens.map((token,t) => {
    const x=new Float32Array(85);
    for (let i=lo; i<hi; i++) x[i]=(token[i]-w.mean[i-lo])/w.sd[i-lo];
    return project(x,"project").map((v,i) => v+param("pos")[t*16+i]);
  });
  const qkv=hidden.map(x => linear(x,param("layer.self_attn.in_proj_weight"),param("layer.self_attn.in_proj_bias")));
  // Earlier tokens supply keys and values. Only the last token reaches the readout.
  const attn=project(lastAttention(qkv),"layer.self_attn.out_proj");
  const x=norm(hidden[3].map((v,i) => v+attn[i]),param("layer.norm1.weight"),param("layer.norm1.bias"));
  const feed=project(project(x,"layer.linear1").map(gelu),"layer.linear2");
  const encoded=norm(x.map((v,i) => v+feed[i]),param("layer.norm2.weight"),param("layer.norm2.bias"));
  return project(encoded,"out").map(v => Math.max(0,v));
}
function predictStudy(s, mode="aligned") {
  const tokens=tokensFor(s);
  const cell=((s.digit-1)*68 + s.phase*34 + s.tick-9)*5;
  return {
    transformer: transformer(tokens,mode,weights["transformer_"+mode]),
    ridge: ridge(tokens,mode,weights["ridge_"+mode]),
    table: Array.from(weights.cue_table.table.subarray(cell,cell+5))
  };
}
