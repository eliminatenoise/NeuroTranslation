import fs from 'node:fs';
import {predict} from './fit/predict.mjs';
const [weights,input]=process.argv.slice(2);
if (!weights || !input){console.error('Usage: node launch.mjs weights.json history.json');process.exitCode=2;}
else{
  const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
  console.log(JSON.stringify({displacement_cm:predict(load(weights),load(input))}));
}
