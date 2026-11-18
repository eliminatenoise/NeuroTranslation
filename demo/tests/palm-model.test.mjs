import assert from 'node:assert/strict';
import test from 'node:test';
import { parsePacket } from '../src/core.mjs';
import { scoreEegReplay, validateEegReplayModel } from '../src/palm-model.mjs';

const offsets = [200, 250, 300, 350, 400, 450, 500, 550, 600];
const releaseUrl = 'https://doi.org/10.18112/openneuro.ds006840.v1.0.0';
const modelFile = {
  schema_version: 1, kind: 'offline_scalp_eeg_palm_ridge',
  analysis: 'iackd_r1_conditional_palm_availability_grid',
  model_id: 'iackd-r1-conditional-palm-availability-grid-v1',
  design_sha256: 'ccaff2ccda3a32ba182c78c0a111fd36295f5bb8b2b400acc46faa1436433fc9',
  source_sha256: 'b'.repeat(64), train_participants: ['sub-07', 'sub-08', 'sub-09'],
  train_asset_sha256: { 'sub-07': 'a'.repeat(64), 'sub-08': 'b'.repeat(64), 'sub-09': 'c'.repeat(64) },
  dev_asset_sha256: { 'sub-10': 'a'.repeat(64), 'sub-11': 'd'.repeat(64), 'sub-12': 'e'.repeat(64) },
  target: { field: 'x_mm', units: 'mm', axis: 'device_horizontal_positive_right' },
  clock: { step_ms: 10, tolerance_ms: 0.01, score_offsets_ms: offsets,
    anchor: 'first_finite_palm_at_or_after_native_cue' },
  features: { palm_lags_ms: [100, 150], eeg_bins_ms: [[-190, -140], [-140, -90]], channels: ['C3', 'Cz', 'C4'],
    order: ['palm_position_mm', 'palm_velocity_mm_s', 'eeg_older_C3_uv', 'eeg_older_Cz_uv',
      'eeg_older_C4_uv', 'eeg_newer_C3_uv', 'eeg_newer_Cz_uv', 'eeg_newer_C4_uv'] },
  global_mean_mm: 9,
};
function regression(featureIndices, intercept) {
  const center = [1, 100, -1, -1, 1, 0, -1, 2];
  const scale = [2, 50, 2, 4, 3, 2, 2, 3];
  const coefficients = [2, 3, 4, 5, 6, 7, 8, 9];
  return { feature_indices: featureIndices, center: featureIndices.map(index => center[index]),
    scale: featureIndices.map(index => scale[index]), coefficients: featureIndices.map(index => coefficients[index]),
    intercepts_mm: offsets.map((_, index) => intercept + index * 7) };
}
modelFile.models = {
  time: regression([], 1), time_eeg: regression([2, 3, 4, 5, 6, 7], 70),
  time_palm: regression([0, 1], 20), time_palm_eeg: regression([0, 1, 2, 3, 4, 5, 6, 7], 100),
};

// Invented inputs exercise the release packet shape and arithmetic, never the empirical claims.
function packetFixture({ anchor = 4, subjectId = 'sub-10', trialNo = 0 } = {}) {
  const indices = Array.from({ length: 83 }, (_, index) => index - 12);
  const times = indices.map(index => index * 10 + anchor);
  const channels = ['C3', 'Cz', 'C4'];
  const signals = [index => index, index => index * 2 + 1, index => 6 - index];
  const parent = `${subjectId}_task-ihc_acq-right_run-01`;
  return { schemaVersion: 1,
    dataset: { id: `synthetic-${subjectId}-${trialNo}`, name: 'Synthetic test of a packet declaration',
      sourceUrl: releaseUrl, license: 'CC0', organism: 'Homo sapiens', subjectId,
      recordingId: `${parent} · derivative trial ${trialNo + 1} (EEG segment ${trialNo + 1}, Leap trial ${trialNo})`,
      task: 'IACKD right-hand movement execution with screen feedback',
      timebase: 'IACKD event 14 · cue disappearance', split: 'validation', origin: 'derived',
      provenance: { datasetVersion: '1.0.0', releaseCommit: '0c701aadfa562b8662e76ca0dd6831788e02e8b6',
        derivativePath: `derivatives/movement-execution/${subjectId}/ihc/${subjectId}_task-ihc_run-01_eeg_leap_R1.mat`,
        derivativeSha256: 'a'.repeat(64), parentRecordingId: parent, archiveHand: 'right', archiveRun: '01',
        trial: { outIndexZeroBased: trialNo, eeg_seg_idx: trialNo + 1, lm_trial: trialNo },
        selection: { rowStartZeroBased: 0, rowEndExclusive: times.length, sourceTrialRowCount: times.length },
        clock: { sourceField: 'OUT.t_ms', sourceUnit: 'ms', packetUnit: 's',
          sourceStepMs: 10, timestampMilliseconds: times } } },
    streams: [...channels.map((channel, index) => ({ id: `eeg-${channel.toLowerCase()}`, label: `${channel} scalp EEG`,
      modality: 'neural', region: 'brain', signalType: 'EEG', origin: 'derived', unit: 'µV', rateHz: 100,
      t: times.map(time => time / 1000), values: indices.map(row => signals[index](row - 10)),
      provenance: { sourceField: 'OUT.EEG', sourceColumnZeroBased: 11 + index, channel } })),
    { id: 'leap-palm-x', label: 'Right palm x · Leap Motion', modality: 'displacement', origin: 'derived',
      unit: 'mm', frame: 'Leap Motion device frame, right positive', rateHz: 100,
      t: times.map(time => time / 1000), values: indices.map(index => 2 * (index - 10) + 11),
      provenance: { sourceField: 'OUT.x_mm' } }],
  };
}

function parsed(packet) {
  return parsePacket(JSON.stringify(packet));
}

function clip(packet, start, stop, withPredecessor = false) {
  const { clock, selection } = packet.dataset.provenance;
  if (withPredecessor) clock.previousTimestampMilliseconds = clock.timestampMilliseconds[start - 1];
  clock.timestampMilliseconds = clock.timestampMilliseconds.slice(start, stop);
  selection.rowStartZeroBased = start;
  selection.rowEndExclusive = stop;
  for (const stream of packet.streams) {
    stream.t = stream.t.slice(start, stop);
    stream.values = stream.values.slice(start, stop);
  }
  return packet;
}

test('frozen method math has independently worked first-offset estimates on real packet format', () => {
  const raw = packetFixture();
  raw.streams.reverse();
  const packet = parsed(raw);
  const before = JSON.stringify(packet);
  const result = scoreEegReplay(modelFile, packet, { modelStateSha256: '0'.repeat(64) });
  assert.equal(validateEegReplayModel(modelFile), modelFile);
  assert.equal(JSON.stringify(packet), before);
  assert.equal(result.status, 'scored');
  assert.equal(result.modelId, modelFile.model_id);
  assert.equal(result.modelStateSha256, '0'.repeat(64));
  assert.equal(result.scope, 'offline_recorded_regression');
  assert.equal(result.officialCohortScore, null);
  assert.equal(result.measurementsAuthenticated, false);
  const [trial] = result.trials;
  assert.equal(trial.cohortRole, 'DEV');
  assert.equal(trial.anchorMs, 4);
  assert.equal(trial.coverage, 'full_source_trial');
  assert.equal(trial.completeForProtocol, true);
  assert.deepEqual(trial.rows.map(row => row.offsetMs), offsets);
  const first = trial.rows[0];
  assert.equal(first.timeMs, 204);
  assert.equal(first.sourceRowIndex, 32);
  assert.equal(first.targetMm, 31);
  assert.equal(first.estimateMm, 116);
  assert.equal(first.baselineMm, 36);
  assert.equal(first.errorMm, 85);
  assert.equal(first.baselineErrorMm, 5);
  assert.deepEqual(first.predictionsMm, { time: 1, time_eeg: 70, time_palm: 36, time_palm_eeg: 116,
    global_mean: 9, persistence: 11, velocity_extrapolation: 31 });
  assert.deepEqual(first.missingReasons, []);
  assert.equal(trial.rows[8].timeMs, 604);
  assert.equal(trial.rows[8].predictionsMm.time, 57);
  assert.equal(result.summary.matchedRows, 9);
  assert.equal(result.summary.requestedRows, 9);
  const independentRmse = Math.sqrt(trial.rows.reduce((sum, row) => sum + row.errorMm ** 2, 0) / 9);
  assert.ok(Math.abs(result.summary.estimate.rmseMm - independentRmse) < 1e-12);
});

test('future source rows cannot change a prediction and a missing target yields no matched error', () => {
  const original = scoreEegReplay(modelFile, parsed(packetFixture())).trials[0].rows;
  const replacement = packetFixture();
  replacement.streams[0].values[23] = 999;
  replacement.streams[3].values[32] = 888;
  const changed = scoreEegReplay(modelFile, parsed(replacement)).trials[0].rows;
  assert.equal(changed[0].estimateMm, original[0].estimateMm);
  assert.equal(changed[0].baselineMm, original[0].baselineMm);
  assert.equal(changed[0].targetMm, 888);
  assert.notEqual(changed[1].estimateMm, original[1].estimateMm);
  const lostTarget = packetFixture();
  lostTarget.streams[3].values[72] = null;
  const result = scoreEegReplay(modelFile, parsed(lostTarget));
  assert.equal(result.status, 'partial');
  assert.equal(result.trials[0].completeForProtocol, false);
  assert.equal(result.summary.matchedRows, 8);
  const last = result.trials[0].rows.at(-1);
  assert.equal(last.estimateMm, original.at(-1).estimateMm);
  assert.equal(last.targetMm, null);
  assert.equal(last.errorMm, null);
  assert.equal(last.missingReasons[0].code, 'source_value_missing');
});

test('null EEG and palm inputs exclude both methods on exactly the affected rows', () => {
  const raw = packetFixture();
  raw.streams[0].values[13] = null;
  raw.streams[3].values[22] = null;
  const result = scoreEegReplay(modelFile, parsed(raw));
  const { rows } = result.trials[0];
  assert.equal(result.summary.matchedRows, 7);
  assert.deepEqual(rows[0].missingReasons.map(reason => [reason.signal, reason.relativeOffsetMs]), [
    ['Past palm', 100], ['C3', 10],
  ]);
  assert.equal(rows[0].targetMm, 31);
  assert.equal(rows[0].estimateMm, null);
  assert.equal(rows[0].baselineMm, null);
  assert.equal(rows[1].estimateMm, null);
  assert.equal(rows[1].baselineMm, null);
  assert.equal(rows[1].missingReasons[0].relativeOffsetMs, 100);
  assert.ok(rows[2].estimateMm !== null);
});

test('positive-only selected source window requires a recorded predecessor and keeps local scope', () => {
  const clipped = clip(packetFixture(), 12, 63);
  let result = scoreEegReplay(modelFile, parsed(clipped));
  assert.equal(result.status, 'no_matched_rows');
  assert.equal(result.trials[0].issues[0].code, 'anchor_predecessor_missing');
  assert.ok(result.trials[0].rows.every(row => row.estimateMm === null));
  const verifiedWindow = clip(packetFixture({ subjectId: 'sub-02' }), 12, 63, true);
  result = scoreEegReplay(modelFile, parsed(verifiedWindow));
  assert.equal(result.status, 'partial');
  assert.equal(result.officialCohortScore, null);
  assert.equal(result.trials[0].cohortRole, 'outside_cohort');
  assert.equal(result.trials[0].anchorMs, 4);
  assert.equal(result.trials[0].coverage, 'source_window');
  assert.equal(result.summary.matchedRows, 7);
  assert.equal(result.trials[0].rows.at(-1).missingReasons[0].code, 'outside_source_window');
  verifiedWindow.dataset.provenance.clock.previousTimestampMilliseconds = -5;
  assert.equal(scoreEegReplay(modelFile, parsed(verifiedWindow)).diagnostics[0].code, 'anchor_predecessor');
});

test('a positive-only window outside the fitted cohort reports missing cue history', () => {
  const window = clip(packetFixture({ subjectId: 'sub-02' }), 18, 63);
  const result = scoreEegReplay(modelFile, parsed(window));
  assert.equal(result.status, 'no_matched_rows');
  assert.equal(result.trials[0].cohortRole, 'outside_cohort');
  assert.equal(result.trials[0].issues[0].code, 'anchor_outside_window');
});

test('event anchor at zero works and selected source ranges preserve actual within-tolerance times', () => {
  const raw = packetFixture({ anchor: 0 });
  raw.dataset.provenance.clock.timestampMilliseconds[32] += 0.005;
  for (const stream of raw.streams) stream.t[32] = 200.005 / 1000;
  const result = scoreEegReplay(modelFile, parsed(raw));
  assert.equal(result.status, 'scored');
  assert.equal(result.trials[0].anchorMs, 0);
  assert.equal(result.trials[0].rows[0].nominalTimeMs, 200);
  assert.equal(result.trials[0].rows[0].timeMs, 200.005);
  assert.equal(result.trials[0].rows[0].inputThroughMs, 100);
  assert.ok(Math.abs(result.trials[0].rows[0].sampleLeadMs - 100.005) < 1e-12);
  assert.equal(result.trials[0].rows[0].estimateMm, 116);
});

test('availability protocol anchors on the first recorded post-cue palm row and enforces stock source hashes', () => {
  const raw = packetFixture();
  const palm = raw.streams[3];
  palm.values.fill(null, 12, 15);
  const result = scoreEegReplay(modelFile, parsed(raw));
  const [trial] = result.trials;
  assert.equal(result.status, 'scored');
  assert.equal(result.clockReference, 'first_finite_palm_at_or_after_native_cue');
  assert.equal(trial.sourceAssetMatchesStudy, true);
  assert.equal(trial.anchorMs, 4);
  assert.equal(trial.timeReferenceMs, 34);
  assert.equal(trial.rows[0].offsetMs, 200);
  assert.equal(trial.rows[0].timeMs, 234);
  assert.equal(trial.rows[0].inputThroughMs, 134);
  assert.equal(trial.rows[0].sampleLeadMs, 100);
  assert.equal(trial.rows[0].targetMm, 37);
  assert.equal(trial.rows[0].estimateMm, 155);
  assert.equal(trial.rows[0].baselineMm, 42);
  assert.equal(trial.rows.at(-1).timeMs, 634);
  const badSource = structuredClone(raw);
  badSource.dataset.provenance.derivativeSha256 = '0'.repeat(64);
  assert.equal(scoreEegReplay(modelFile, parsed(badSource)).diagnostics[0].code, 'study_asset_identity');
  const noPalm = structuredClone(raw);
  noPalm.streams[3].values.fill(null, 12);
  const noReference = scoreEegReplay(modelFile, parsed(noPalm));
  assert.equal(noReference.status, 'no_matched_rows');
  assert.equal(noReference.trials[0].anchorMs, 4);
  assert.equal(noReference.trials[0].timeReferenceMs, null);
  assert.equal(noReference.trials[0].issues[0].code, 'palm_timing_origin_missing');
});

test('false declarations, swapped columns, unmatched target axes and broken native clocks are rejected', () => {
  const mismatches = [
    ['model_identity', raw => { raw.design_sha256 = 'a230ad20ece1c05b52cdceea00b8b55a51a27af8e038a2abda9c550b6eaf722c'; }, true],
    ['model_features', raw => raw.features.order.reverse(), true],
    ['model_parameters', raw => { raw.models.time_palm.scale[0] = 0; }, true],
    ['release_identity', raw => { raw.dataset.provenance.releaseCommit = 'wrong'; }],
    ['release_identity', raw => { raw.dataset.provenance.archiveHand = 'left'; }],
    ['trial_identity', raw => { raw.dataset.provenance.trial.lm_trial = 44; }],
    ['source_selection', raw => { raw.dataset.provenance.selection.rowStartZeroBased = 14; }],
    ['eeg_mapping', raw => { raw.streams[0].provenance.sourceColumnZeroBased = 13; }],
    ['eeg_mapping', raw => { raw.streams[0].unit = 'V'; }],
    ['palm_mapping', raw => { raw.streams[3].frame = 'Leap Motion device frame, left positive'; }],
    ['palm_mapping', raw => { raw.streams[3].provenance.sourceField = 'OUT.z_mm'; }],
    ['palm_mapping', raw => { raw.streams[3].origin = 'simulated'; }],
    ['stream_clock', raw => { raw.streams[3].t[5] += 0.0001; }],
    ['off_lattice', raw => {
      raw.dataset.provenance.clock.timestampMilliseconds[16] += 0.05;
      for (const stream of raw.streams) stream.t[16] = 44.05 / 1000;
    }],
  ];
  for (const [code, mutate, changeModel] of mismatches) {
    const packet = packetFixture();
    const model = structuredClone(modelFile);
    mutate(changeModel ? model : packet);
    const result = scoreEegReplay(model, parsed(packet));
    assert.equal(result.status, 'rejected', code);
    assert.equal(result.diagnostics[0]?.code, code);
    assert.equal(result.summary, null);
  }
  const packet = parsed(packetFixture());
  assert.equal(scoreEegReplay(modelFile, [packet, packet]).diagnostics[0].code, 'duplicate_trial');
});

test('separate real-shaped trial packets retain identity and never share each other’s source rows', () => {
  const full = parsed(packetFixture());
  const short = parsed(clip(packetFixture({ trialNo: 2 }), 12, 63, true));
  const result = scoreEegReplay(modelFile, [full, short]);
  assert.equal(result.status, 'partial');
  assert.deepEqual(result.trials.map(trial => trial.matched), [9, 7]);
  assert.deepEqual(result.trials.map(trial => trial.trial.lm_trial), [0, 2]);
  assert.equal(result.summary.matchedRows, 16);
  assert.equal(result.summary.requestedRows, 18);
});
