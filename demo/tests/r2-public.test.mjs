import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { parsePacket } from '../src/core.mjs';
import { loadR2ReplayState, scoreR2Replay } from '../src/r2-replay.mjs';

const readAsset = name => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');
const assets = {
  baseModel: readAsset('palm-model.json'),
  calibrationState: readAsset('r2-calibration-state.json'),
  source: readAsset('r2-source.json'),
  trialIndex: readAsset('r2-trial-index.json'),
};
const state = loadR2ReplayState(assets);
const source = JSON.parse(assets.source);
const index = JSON.parse(assets.trialIndex);
const offsets = [200, 250, 300, 350, 400, 450, 500, 550, 600];
const methods = ['fixedHand', 'fixedEegHand', 'calibratedHand', 'calibratedEegHand'];

// Invented values and times exercise window behavior. No source traces are bundled.
function packetFixture({ subject = 'sub-13', row = 0, full = false } = {}) {
  const binding = source.participants.find(item => item.subject === subject && item.role === 'EVALUATION');
  const { outIndexZeroBased, eeg_seg_idx, lm_trial, sourceTrialRowCount } = index.participants[subject].trials[row];
  const { raw_sources: { brainvision_header, channels_tsv }, n_channels } = binding;
  const parent = `${subject}_task-ihc_acq-right_run-02`;
  const start = full ? 0 : 12;
  const count = full ? sourceTrialRowCount : 60;
  const times = Array.from({ length: count }, (_, i) => (i - 11) * 10 + 2.125);
  const seconds = times.map(t => t / 1000);
  const selectedChannels = binding.channels.map(channel => ({
    name: channel.name, sourceColumnZeroBased: channel.index_zero_based,
  }));
  return {
    schemaVersion: 1,
    dataset: {
      id: 'synthetic-r2-window', name: 'Invented samples for the R2 partial-path test',
      sourceUrl: 'https://doi.org/10.18112/openneuro.ds006840.v1.0.0',
      license: 'CC0', organism: 'Homo sapiens', subjectId: subject,
      recordingId: `${parent} · derivative trial ${row + 1} (EEG segment ${eeg_seg_idx}, Leap trial ${lm_trial})`,
      task: 'IACKD right-hand movement execution with screen feedback',
      timebase: 'IACKD event 14 · cue disappearance', split: 'heldout', origin: 'derived',
      provenance: {
        datasetVersion: '1.0.0', releaseCommit: source.release_commit,
        derivativePath: binding.derivative.release_path, derivativeSha256: binding.asset_sha256,
        parentRecordingId: parent, archiveHand: 'right', archiveRun: '02', archiveDerivative: 'R2',
        trial: { outIndexZeroBased, outPositionOneBased: row + 1, eeg_seg_idx, lm_trial },
        selection: { rowStartZeroBased: start, rowEndExclusive: start + count, sourceTrialRowCount, evaluationRole: 'EVALUATION' },
        clock: { sourceField: 'OUT.t_ms', sourceUnit: 'ms', packetUnit: 's', sourceStepMs: 10,
          timestampMilliseconds: times, timestampSeconds: seconds },
        montage: { acquisitionChannelCount: 31, derivativeEegColumnCount: n_channels,
          sourceOrientation: 'samples × channels in HDF5 storage',
          sourceEegShape: [sourceTrialRowCount, n_channels], selectedChannels,
          acquisitionHeaderSha256: brainvision_header.sha256, channelsTsvSha256: channels_tsv.sha256 },
      },
    },
    streams: [
      ...selectedChannels.map(({ name, sourceColumnZeroBased }, i) => ({
        id: `eeg-${name.toLowerCase()}`, label: `${name} scalp EEG`, modality: 'neural', region: 'brain',
        signalType: 'EEG', origin: 'derived', unit: 'µV', rateHz: 100, t: [...seconds],
        values: times.map((_, j) => i - j / 100),
        provenance: { sourceField: 'OUT.EEG', channel: name, sourceColumnZeroBased },
      })),
      { id: 'leap-palm-x', label: 'Palm x · Leap Motion', modality: 'displacement', origin: 'derived',
        unit: 'mm', rateHz: 100, t: [...seconds], values: times.map((_, j) => 6 + j / 5),
        frame: 'Leap Motion device frame, right positive', provenance: { sourceField: 'OUT.x_mm' } },
    ],
  };
}

const score = packet => scoreR2Replay(state, parsePacket(JSON.stringify(packet)));

test('R2 requires the four exact frozen JSON assets and rejects forged state objects', () => {
  for (const [asset, contents] of Object.entries(assets)) {
    assert.throws(() => loadR2ReplayState({ ...assets, [asset]: contents + ' ' }), { code: 'state_digest' });
  }
  assert.equal(scoreR2Replay({ ...state }, packetFixture()).diagnostics[0].code, 'unverified_state');
});

test('an R2 replay never accepts an R1, unbound source or wrong montage declaration', () => {
  const cases = [
    ['release_identity', p => { p.dataset.provenance.archiveRun = '01'; }],
    ['r2_source_identity', p => { p.dataset.provenance.derivativeSha256 = '0'.repeat(64); }],
    ['r2_trial_identity', p => { p.dataset.provenance.trial.outPositionOneBased += 1; }],
    ['r2_montage', p => { p.dataset.provenance.montage.sourceOrientation = 'channels × samples'; }],
    ['eeg_mapping', p => { p.streams[1].unit = 'V'; }],
  ];
  for (const [code, alter] of cases) {
    const packet = packetFixture();
    alter(packet);
    const replay = score(packet);
    assert.equal(replay.status, 'rejected');
    assert.equal(replay.diagnostics[0].code, code);
    assert.deepEqual(replay.rows, []);
    assert.equal(replay.officialExclusion, null);
  }
});

test('a synthetic window exposes four compared estimates on the identical available offsets', () => {
  const replay = score(packetFixture());
  assert.equal(replay.status, 'partial');
  assert.equal(replay.coverage, 'source_window');
  assert.equal(replay.timeReferenceMs, 2.125);
  assert.equal(replay.sourceClockVerified, false);
  assert.equal(replay.selectedSamplesMatchSource, null);
  assert.equal(replay.eligibleForStudySupport, null);
  assert.equal(replay.officialCohortScore, null);
  assert.deepEqual(replay.rows.map(row => row.offsetMs), offsets);
  assert.equal(replay.summary.matchedRows, 6);
  const first = replay.rows[0];
  assert.equal(first.timeMs, 202.125);
  assert.equal(first.sampleLeadMs, 100);
  assert.equal(first.sourceRowIndex, 43);
  assert.deepEqual(Object.keys(first.predictionsMm), methods);
  for (const method of methods) {
    assert.equal(first.errorsMm[method], first.predictionsMm[method] - first.targetMm);
    assert.ok(Number.isFinite(replay.summary.metrics[method].rmseMm));
  }
  assert.ok(replay.rows.slice(6).every(row => row.errorsMm === null && row.predictionsMm === null));
});

test('no estimates come from a crop of the indexed exclusion or a counterfeit complete trial', () => {
  const subject = 'sub-14';
  const row = index.participants[subject].trials.findIndex(trial => trial.exclusion === 'clock_gapped_or_off_lattice');
  assert.notEqual(row, -1);
  const crop = score(packetFixture({ subject, row }));
  assert.equal(crop.status, 'partial');
  assert.equal(crop.summary.matchedRows, 0);
  assert.equal(crop.officialExclusion, null);
  assert.ok(crop.rows.every(item => item.predictionsMm === null));
  const full = score(packetFixture({ subject, row, full: true }));
  assert.equal(full.status, 'rejected');
  assert.equal(full.diagnostics[0].code, 'r2_archived_clock_mismatch');
  assert.equal(full.officialExclusion, null);
  assert.deepEqual(full.rows, []);
});
