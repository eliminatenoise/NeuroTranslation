#!/usr/bin/env node
'use strict';
const fs=require('node:fs');
const example=require('./src/example.js');
const model=require('./src/predict.js');
const {weights,signatures}=require('./src/bundle.json');
const file=process.argv[2];
try {
  const record=file?JSON.parse(fs.readFileSync(file==='-'?0:file,'utf8')):{
    method:'transformer',modality:'combined',edited_rows:example.history(720,example.defaults),
    reference_rows:example.history(720,example.reference(example.defaults))};
  const method=record.method||'transformer',modality=record.modality||'combined';
  const result={model_sha256:signatures[method+'-'+modality+'.npz'],method,modality};
  if(record.rows)result.forecast_N=model.predict(record.rows,weights,method,modality);
  else {
    result.edited_prediction_N=model.predict(record.edited_rows,weights,method,modality);
    result.reference_prediction_N=model.predict(record.reference_rows,weights,method,modality);
  }
  process.stdout.write(JSON.stringify(result)+'\n');
} catch(error) { console.error(error.message); process.exitCode=1; }
