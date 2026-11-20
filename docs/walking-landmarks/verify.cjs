const fs = require('node:fs');
const path = require('node:path');
const {models,predict} = require('./src/predict.js');
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname,'data', name),'utf8'));
const fixture=read('example.json'), expected=read('example-results.json'), w=read('weights.json');
let worst=0;
for(const model of models) {
  const y=predict(fixture.markers_mm,fixture.emg_rms_uv,model,w);
  const error=Math.max(...y.flat().map((v,i)=>Math.abs(v-expected[model].flat()[i])));
  if(!Number.isFinite(error)||error>0.001)throw Error(model+' differs from Python by '+error+' mm');
  worst=Math.max(error,worst);
}
console.log('Six models passed. Largest difference from saved Python prediction: '+worst.toPrecision(4)+' mm.');
