import { readFileSync } from 'node:fs';
import { predict } from './inference.mjs';

if (process.argv.length !== 4) throw Error('Supply a checkpoint JSON file and an event JSON file');
const [weights,event] = process.argv.slice(2).map(path => JSON.parse(readFileSync(path,'utf8')));
console.log(JSON.stringify(predict(weights,event)));
