import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import vm from 'node:vm';

const context = vm.createContext({atob});
for (const name of ['weights.js', 'predict.js']) {
  vm.runInContext(readFileSync(new URL(name, import.meta.url), 'utf8'), context, {filename: name});
}
const predict = vm.runInContext('compactWalking.predict', context);
const noForce = Array.from({length: 10}, () => [0, 0]);
const seconds = Array.from({length: 10}, (_, i) => i * 0.02);
const averageTime = seconds.reduce((sum, t) => sum + t, 0) / seconds.length;
const centeredTime = seconds.map(time => time - averageTime);
const timeSquares = centeredTime.reduce((sum, t) => sum + t ** 2, 0);

function finiteMatrix(rows) {
  return Array.isArray(rows) && rows.length === 10 && rows.every(
    row => Array.isArray(row) && row.length === 6 && row.every(Number.isFinite)
  );
}

function averageForecast(heel) {
  const first = predict({heel, force: noForce}, false, 2731).heel.flat();
  const second = predict({heel, force: noForce}, false, 4119).heel.flat();
  return Array.from(first, (value, i) => (value + second[i]) / 2);
}

// `heel` is relative to each heel's first observation. Velocity is in mm/s.
export function compareProjected(heel, velocity) {
  if (!finiteMatrix(heel) || !heel[0].every(value => value === 0) ||
      !Array.isArray(velocity) || velocity.length !== 3 || !velocity.every(Number.isFinite) ||
      velocity[2] !== 0) {
    throw new TypeError('Expected ten relative heel positions and a finite horizontal velocity.');
  }
  const doubled = [...velocity, ...velocity];
  const relative = heel.map((row, k) => row.map((value, axis) => value - seconds[k] * doubled[axis]));
  const pelvis = doubled.map(value => 0.1 * value);
  const result = {
    stay: Array(6).fill(0),
    linear: heel[9].map((value, axis) => (value - heel[8][axis]) * 5),
    compact: averageForecast(heel),
    pelvis,
    centered: averageForecast(relative).map((value, axis) => value + pelvis[axis]),
  };
  if (!Object.values(result).every(vector => vector.every(Number.isFinite))) {
    throw new RangeError('The input did not yield finite movement estimates.');
  }
  return result;
}

export function forecastOverground({time_ms, heel_mm, pelvis_mm}) {
  if (!Array.isArray(time_ms) || time_ms.length !== 10 || !time_ms.every(
    (value, i) => Number.isSafeInteger(value) && value === time_ms[0] + 20 * i
  ) || !finiteMatrix(heel_mm) || !finiteMatrix(pelvis_mm)) {
    throw new TypeError('Supply ten observed pairs of heel and pelvis markers at exact 20 ms intervals.');
  }
  const heel = heel_mm.map(row => row.map((value, axis) => value - heel_mm[0][axis]));
  const velocity = [0, 1, 2].map(axis => {
    if (axis === 2) return 0;
    return pelvis_mm.reduce((sum, row, i) => (
      sum + centeredTime[i] * ((row[axis] + row[axis + 3]) / 2)
    ), 0) / timeSquares;
  });
  return {
    last_sample_ms: time_ms[9], target_ms: time_ms[9] + 100,
    axis_order: ['left', 'backward', 'up'],
    horizontal_pelvis_velocity_mm_s: velocity,
    predictions_mm: compareProjected(heel, velocity),
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 3) {
    process.stderr.write('Run node overground.mjs overground-example.json\n');
    process.exitCode = 2;
  } else {
    try {
      const input = JSON.parse(readFileSync(process.argv[2], 'utf8'));
      process.stdout.write(JSON.stringify(forecastOverground(input), null, 2) + '\n');
    } catch (error) {
      process.stderr.write(error.message + '\n');
      process.exitCode = 1;
    }
  }
}
