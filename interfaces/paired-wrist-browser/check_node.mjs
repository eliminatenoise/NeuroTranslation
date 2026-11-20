import fs from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
if (!globalThis.crypto) globalThis.crypto = webcrypto;
import {createPairedPredictor} from './public/predictor.mjs';
import {verify} from './check.mjs';
const cache = new Map();
async function readWeights(mode) {
  const data = await fs.readFile(new URL('./public/weights/' + mode + '.bin', import.meta.url));
  return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
}
const load = mode => {
  if (!cache.has(mode)) cache.set(mode, readWeights(mode).then(buf => createPairedPredictor(mode, buf)));
  return cache.get(mode);
};
const cases = JSON.parse(await fs.readFile(new URL('fixtures.json', import.meta.url)));
const results = await verify(load, cases);
const wrong = await readWeights('motion');
new Uint8Array(wrong)[0] ^= 1;
await createPairedPredictor('motion', wrong).then(() => { throw Error('Accepted corrupt weights'); }, () => {});
await createPairedPredictor('full', await readWeights('emg')).then(() => { throw Error('Accepted swapped weights'); }, () => {});
await createPairedPredictor('other', wrong).then(() => { throw Error('Accepted unknown mode'); }, () => {});
console.log(JSON.stringify({engine: process.version, corrupt_or_swapped_weights_rejected: true, ...results}, null, 2));
