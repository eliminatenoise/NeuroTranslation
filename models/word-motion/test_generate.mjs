import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {actionFor, generateMotion} from './inference.mjs';
const read = name => JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'));
const weights = read('weights.json');
assert.equal(actionFor('RUN/JOG'), 'run');
for (const s of ['', null, 'walk and run', 'do not walk', 'jump', 'walk backward', '__proto__']) {
  assert.equal(generateMotion(s, weights), null);
}
for (const action of ['walk', 'run']) {
  const py = read(action + '.json');
  const browser = generateMotion(action, weights);
  assert.equal(browser.rateHz, 40);
  assert.equal(browser.positionsMm.length, 25);
  assert(browser.positionsMm.every(f => f.length === 18 && f.every(v => v.length === 3)));
  assert.deepEqual(browser.rootMm[0], [0,0,0]);
  const actual = [...browser.positionsMm.flat(2), ...browser.rootMm.flat()];
  const reference = [...py.positionsMm.flat(2), ...py.rootMm.flat()];
  const error = Math.max(...actual.map((v, i) => Math.abs(v - reference[i])));
  assert(error < 0.002, 'Browser output differs by ' + error + ' mm');
  console.log(action, actual.length, 'coordinates; worst CPU-Python/browser difference', error, 'mm');
}
