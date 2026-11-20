"use strict";
const assert = require("node:assert/strict");
const {predict}=require("./model.js"), weights=require("./weights.json");
const input=require("./synthetic-event.json"), expected=require("./synthetic-reference.json");
for(const mode of ["joint","specialists"]) {
  const got=predict(weights,input,mode);
  assert.equal(got.future_rms_uv.length,8);
  assert.ok(got.future_rms_uv.every(x=>Number.isFinite(x)&&x>=0));
  assert.equal(got.future_path_mm.length,32);
  assert.ok(got.future_path_mm.every(row=>row.length===3&&row.every(Number.isFinite)));
  for(const k of ["future_rms_uv","future_path_mm"]) {
    const native=expected[mode][k].flat(), numbers=got[k].flat();
    const max=Math.max(...numbers.map((v,i)=>Math.abs(v-native[i])));
    assert.ok(max<0.0001, mode+" "+k+" differs from fitted model: "+max);
    console.log(mode,k,"max difference",max);
  }
  const shifted={...input,sacrum_mm:input.sacrum_mm.map(row=>row.map(v=>v+100))};
  const path=predict(weights,shifted,mode).future_path_mm.flat();
  assert.ok(path.every((x,i)=>Math.abs(x-got.future_path_mm.flat()[i])<1e-9));
}
assert.throws(()=>predict(weights,{...input,posture:9}));
assert.throws(()=>predict(weights,{...input,leg_uv:[]}));
assert.throws(()=>predict(weights,input,"missing"));
