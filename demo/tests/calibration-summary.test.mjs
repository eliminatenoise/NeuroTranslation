import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import test from 'node:test';

test('the companion projects only the matching archived calibration and evaluation results', async () => {
  const study = new URL('../../benchmarks/scalp-eeg-personal-calibration/', import.meta.url);
  const [bytes, manifest, projected] = await Promise.all([
    readFile(new URL('RESULT.json', study)),
    readFile(new URL('SHA256SUMS.txt', study), 'utf8'),
    readFile(new URL('../src/calibration-summary.json', import.meta.url), 'utf8')
  ]);
  const result = JSON.parse(bytes);
  const summary = JSON.parse(projected);
  const digest = createHash('sha256').update(bytes).digest('hex');
  assert.ok(manifest.split(/\r?\n/).includes(`${digest}  RESULT.json`));
  assert.deepEqual(Object.keys(summary), [
    'schemaVersion', 'study', 'resultSha256', 'terminologyRegistry', 'equalPerson', 'participants'
  ]);
  assert.equal(summary.schemaVersion, 1);
  assert.equal(summary.resultSha256, digest);
  assert.equal(summary.study, result.study);
  assert.deepEqual(summary.terminologyRegistry, result.terminology_registry);
  assert.deepEqual(Object.keys(summary.participants).sort(), Object.keys(result.metrics.per_person).sort());

  const methods = [
    'time_palm_frozen', 'time_palm_ridge', 'time_palm_eeg_frozen', 'time_palm_eeg_ridge'
  ];
  const comparison = result.comparisons.primary_adaptation;
  const scopeRows = [
    [summary.equalPerson, result.counts, result.metrics.equal_person, comparison.pooled_paired_trials],
    ...Object.entries(summary.participants).map(([id, row]) => [
      row, result.trial_support[id], result.metrics.per_person[id], comparison.per_person_paired_trials[id]
    ])
  ];
  for (const [row, counts, metrics, trials] of scopeRows) {
    assert.deepEqual(Object.keys(row), ['calibration', 'evaluation', 'clockExclusions', 'rmseMm', 'eegCalibrationTrials']);
    for (const role of ['calibration', 'evaluation']) {
      assert.deepEqual(row[role], {
        eligible: counts[role].eligible_trials,
        released: counts[role].released_trials,
        positions: counts[role].scored_rows
      });
    }
    assert.equal(row.clockExclusions, row.evaluation.released - row.evaluation.eligible);
    assert.deepEqual(row.rmseMm, Object.fromEntries(methods.map(method => [method, metrics[method].rmse_mm])));
    assert.deepEqual(row.eegCalibrationTrials, {lower: trials.candidate, higher: trials.reference, tied: trials.tied});
  }

  const people = Object.values(summary.participants);
  for (const method of methods) {
    const equalWeightRootMeanSquare = Math.hypot(...people.map(row => row.rmseMm[method])) / Math.sqrt(people.length);
    assert.ok(Math.abs(summary.equalPerson.rmseMm[method] - equalWeightRootMeanSquare) < 1e-14);
  }
});
