import fs from 'node:fs';
import {predictCount} from './fit/predict.mjs';
const [weights, input]=process.argv.slice(2);
if(!weights || !input){console.error('Usage: node launch.mjs weights.json five-bins.json');process.exitCode=2;}
else{
  const load=name=>JSON.parse(fs.readFileSync(name,'utf8'));
  console.log(JSON.stringify({expected_spikes_next_20ms:predictCount(load(weights),load(input))}));
}
