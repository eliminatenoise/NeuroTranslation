// Offline command line for a single record in the browser API format.
import {readFile} from 'node:fs/promises';
import {forecastMovement} from './predictor.mjs';

try {
  if (process.argv.length !== 3) throw new Error('Usage: node predict.mjs INPUT.json');
  const input = JSON.parse(await readFile(process.argv[2], 'utf8'));
  console.log(JSON.stringify(await forecastMovement(input)));
} catch (error) {
  console.error(error.message);
  process.exitCode = 2;
}
