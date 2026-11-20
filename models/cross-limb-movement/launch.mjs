import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {predict} from './inference.mjs';
const base = (name)=>fileURLToPath(new URL(name,import.meta.url));
const [input=base('synthetic-upper.json'),weights=base('model-joint.json')]=process.argv.slice(2);
const read=(f)=>JSON.parse(readFileSync(f,'utf8'));
console.log(JSON.stringify(predict(read(weights),read(input)),null,2));
