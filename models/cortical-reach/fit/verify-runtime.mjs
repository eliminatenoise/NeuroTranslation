import fs from 'node:fs';
import path from 'node:path';
import {predict} from './predict.mjs';
const f=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const cases=f.histories;
const load=n=>JSON.parse(fs.readFileSync(path.join(process.argv[3],n),'utf8'));
let worst=0, compared=0, rejected=0;
for (const [file,reference] of Object.entries(f.expected)) {
  const w=load(file);
  for(let i=0;i<cases.length;i++) {
    const output=predict(w,cases[i]);
    worst=Math.max(worst,...output.map((v,j)=>Math.abs(v-reference[i][j])));
    compared++;
  }
}
const joint=load('weights-all-17.json');
const clone=()=>structuredClone(cases[0]);
const invalid=[
  h=>{delete h.cue;}, h=>{h.session='other_day';}, h=>{h.unit_ids.reverse();},
  h=>{delete h.unit_ids;},h=>{h.neural[0][0]=0.5;},h=>{h.neural[0][0]=-1;},
  h=>{h.cue[0][0]=0;h.cue[0][1]=1;},h=>{h.cue[0][6]=2;},
  h=>{h.movement[1][2]=NaN;},h=>{h.movement.pop();},h=>{h.movement[0][0]=true;}
];
for (const alter of invalid) {
  const h=clone();alter(h);
  try {predict(joint,h);} catch {rejected++;continue;}
  throw new Error('invalid history accepted');
}
for (const change of [w=>w.x_scale[0]=0,w=>w.parameters.position[0].pop(),
  w=>w.parameters['readout.weight'][0][0]=Infinity,w=>w.unit_ids.reverse()]) {
  const w=structuredClone(joint);change(w);
  try {predict(w,clone());} catch {rejected++;continue;}
  throw new Error('invalid weights accepted');
}
const only=load('weights-movement_only-17.json'),full=clone();
const minimal={session:full.session,movement:full.movement};
if (JSON.stringify(predict(only,full))!==JSON.stringify(predict(only,minimal))) throw new Error('masked input changed result');
if (worst>=1e-4) throw new Error('reference mismatch '+worst);
console.log(JSON.stringify({n_forecasts:compared,n_rejected_invalid:rejected,max_absolute_error_cm:worst,masked_equality:true}));
