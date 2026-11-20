import {normalizeFinite} from './plot.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.mjs';
import {sha256Hex} from './hash.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.mjs';
import {scoreEegReplay, validateEegReplayModel} from './palm-model.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.mjs';

const expectedModelSha256 = 'c9c9e6a5c357274103e339f69517ae6a11f1d90c39f1d172585ad81a38ee8337';
const byId = id => document.getElementById(id);
const curves = [
  {key: 'targetMm', color: '#173e48', dash: []},
  {key: 'baselineMm', color: '#9a542f', dash: [6, 4]},
  {key: 'estimateMm', color: '#385bc2', dash: [2, 3]},
];

function numberText(value) {
  if (!Number.isFinite(value)) return '—';
  return Math.abs(value) >= 1e6 ? value.toExponential(2) : value.toFixed(2);
}

function drawReplay(canvas, rows) {
  if (!canvas.clientWidth || !canvas.clientHeight) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  ctx.scale(canvas.width / w, canvas.height / h);
  if (!rows.length) return;
  const values = rows.flatMap(row => curves.map(c => row[c.key])).filter(Number.isFinite);
  if (!values.length) return;
  const low = Math.min(...values), high = Math.max(...values);
  const left = 52, right = w - 12, top = 14, bottom = h - 34;
  const first = rows[0].offsetMs, last = rows.at(-1).offsetMs;
  const x = offset => left + normalizeFinite(offset, first, last) * (right - left);
  const y = value => bottom - normalizeFinite(value, low, high) * (bottom - top);
  const levels = low === high ? [low] : [low, low/2 + high/2, high];
  ctx.font = '11px Arial, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'right';
  for (const level of levels) {
    ctx.strokeStyle = '#e1e7e9'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(left, y(level)); ctx.lineTo(right, y(level)); ctx.stroke();
    ctx.fillStyle = '#435760'; ctx.fillText(numberText(level), left - 7, y(level), left - 9);
  }
  ctx.textAlign = 'center';
  for (const row of rows) {
    const px = x(row.offsetMs);
    ctx.strokeStyle = '#cad5d8';
    ctx.beginPath(); ctx.moveTo(px, bottom + 2); ctx.lineTo(px, bottom + 5); ctx.stroke();
  }
  for (const offset of [...new Set([first, rows[Math.floor(rows.length / 2)].offsetMs, last])]) {
    ctx.fillText(String(offset), x(offset), bottom + 14);
  }
  ctx.fillText('Time from first available palm sample (ms)', (left + right) / 2, h - 5);
  for (const curve of curves) {
    ctx.strokeStyle = curve.color; ctx.fillStyle = curve.color;
    ctx.lineWidth = 2; ctx.setLineDash(curve.dash); ctx.beginPath();
    let continued = false;
    for (const row of rows) {
      const value = row[curve.key];
      if (!Number.isFinite(value)) { continued = false; continue; }
      if (continued) ctx.lineTo(x(row.offsetMs), y(value));
      else ctx.moveTo(x(row.offsetMs), y(value));
      continued = true;
    }
    ctx.stroke(); ctx.setLineDash([]);
    for (const row of rows) if (Number.isFinite(row[curve.key])) {
      ctx.beginPath(); ctx.arc(x(row.offsetMs), y(row[curve.key]), 2.5, 0, 2 * Math.PI); ctx.fill();
    }
  }
}

function explainIssues(issues) {
  return [...new Set((issues || []).map(issue => issue.message || issue.code).filter(Boolean))].join(' ');
}

export function createPalmReplay({openImport, download}) {
  const picker = byId('replay-recording'), run = byId('replay-run');
  const status = byId('replay-status'), output = byId('replay-result');
  const canvas = byId('replay-plot'), exportButton = byId('replay-export');
  const inputs = byId('replay-inputs');
  let model, modelDigest, runR2, loadError = false, r2LoadError = false;
  let packetList, candidates = [], currentResult, rows = [];

  function selectedPacket() { return candidates[picker.selectedIndex]; }

  function isRunTwo(packet) {
    const provenance = packet?.dataset.provenance;
    return provenance?.archiveRun === '02' || provenance?.archiveDerivative === 'R2';
  }

  function readyFor(packet) { return Boolean(isRunTwo(packet) ? runR2 : model); }

  function reset() {
    currentResult = undefined; rows = []; output.hidden = true;
    exportButton.disabled = true;
    const packet = selectedPacket();
    const r2 = isRunTwo(packet);
    run.disabled = !packet || !readyFor(packet);
    byId('replay-group-note').textContent = r2
      ? 'Across three participants, R1 calibration lowered the hand-and-EEG model’s R2 error from 1.849 to 1.700 mm. Each person had equal weight.'
      : 'Across three R1 development participants, adding EEG raised root mean squared error from 1.09 to 1.22 mm. Each person had equal weight.';
    if (loadError || (r2 && r2LoadError)) {
      status.textContent = r2 ? 'The personal calibration parameters could not be loaded. Reload the page to try again.'
        : 'The fitted benchmark could not be loaded. Reload the page to try again.';
    } else if (!packet) status.textContent = 'Import an IACKD trial packet to compare its palm position with the fitted estimates.';
    else if (!readyFor(packet)) status.textContent = 'Loading fitted benchmark parameters…';
    else status.textContent = r2 ? 'Compare this second recording with and without calibration on the first recording.'
      : 'Choose a recording and compare the estimates on its original trial clock.';
  }

  function showRows(displayRows) {
    const table = byId('replay-rows');
    table.replaceChildren();
    for (const row of displayRows) {
      const tr = document.createElement('tr');
      const offset = document.createElement('th'); offset.scope = 'row';
      offset.textContent = String(row.offsetMs); tr.append(offset);
      for (const key of ['targetMm', 'baselineMm', 'estimateMm']) {
        const cell = document.createElement('td');
        cell.textContent = numberText(row[key]);
        if (Number.isFinite(row[key])) cell.title = String(row[key]) + ' mm';
        tr.append(cell);
      }
      table.append(tr);
      if (row.missingReasons?.length) {
        const reasonRow = document.createElement('tr'), cell = document.createElement('td');
        cell.colSpan = 4; cell.className = 'replay-reason';
        cell.textContent = explainIssues(row.missingReasons); reasonRow.append(cell); table.append(reasonRow);
      }
    }
  }

  function setLabels(before, after, beforeShort, afterShort) {
    byId('replay-legend-baseline').textContent = before;
    byId('replay-legend-estimate').textContent = after;
    byId('replay-head-baseline').textContent = beforeShort;
    byId('replay-head-estimate').textContent = afterShort;
  }

  function plotR2Rows() {
    if (!currentResult || !isRunTwo(selectedPacket())) return;
    const [fixed, adapted] = inputs.value === 'hand'
      ? ['fixedHand', 'calibratedHand'] : ['fixedEegHand', 'calibratedEegHand'];
    rows = currentResult.rows.map(row => ({
      ...row, baselineMm: row.predictionsMm?.[fixed] ?? null, estimateMm: row.predictionsMm?.[adapted] ?? null,
    }));
    showRows(rows);
    drawReplay(canvas, rows);
  }

  function showR2(result, packet) {
    if (result.status === 'rejected') {
      status.textContent = explainIssues(result.diagnostics) || 'This recording could not be matched to the R2 study.';
      return;
    }
    const matched = result.summary?.matchedRows ?? 0;
    const hasPoints = matched > 0;
    const reason = explainIssues(result.diagnostics);
    currentResult = result;
    output.hidden = false;
    byId('replay-name').textContent = packet.dataset.name;
    byId('replay-scope').textContent = packet.dataset.subjectId + ' · R2 evaluation recording · ' +
      (result.fullSourceTrial ? 'Full source trial' : 'Imported source window') +
      (Number.isFinite(result.timeReferenceMs) ? ' · First available palm sample at ' + result.timeReferenceMs + ' ms on the task clock' : '');
    byId('replay-figure').hidden = !hasPoints;
    byId('replay-input-picker').hidden = !hasPoints;
    byId('replay-r2-errors').hidden = !hasPoints;
    byId('replay-samples').hidden = !result.rows?.length || result.status === 'ineligible';
    byId('replay-samples').open = !hasPoints || result.status === 'partial';
    byId('replay-missing').textContent = reason;
    byId('replay-missing').hidden = !reason;
    exportButton.disabled = false;
    setLabels('Fixed model', 'After R1 calibration', 'Fixed', 'Calibrated');
    if (!hasPoints) {
      status.textContent = reason || 'No time points qualify for a matched error comparison.';
      byId('replay-errors').textContent = result.officialExclusion
        ? 'This trial was excluded from the published R2 comparison. The download records the reason.'
        : 'The download records the support available in this input.';
      if (result.status === 'partial' && result.rows?.length) plotR2Rows();
      else { rows = []; showRows([]); }
      return;
    }
    status.textContent = matched + ' of ' + result.summary.requestedRows + ' time points have a recorded palm position and all four estimates.';
    byId('replay-errors').textContent = result.fullSourceTrial && result.status === 'scored'
      ? 'The four errors below use the same nine positions from this trial.'
      : 'These errors describe the matched positions in this local window. The published study scores complete trials.';
    for (const cell of byId('replay-r2-errors').querySelectorAll('[data-method]')) {
      const value = result.summary.metrics[cell.dataset.method]?.rmseMm;
      cell.textContent = Number.isFinite(value) ? value.toFixed(3) : '—';
    }
    plotR2Rows();
  }

  function showR1(result, packet) {
    const trial = result.trials?.[0];
    if (!trial || !trial.rows?.length) {
      status.textContent = explainIssues([...(result.diagnostics || []), ...(trial?.issues || [])]) ||
        'This recording lacks the channels, units or clock required by the palm benchmark.';
      return;
    }
    rows = trial.rows; currentResult = result;
    const matched = result.summary.matchedRows;
    byId('replay-name').textContent = packet.dataset.name;
    const role = {TRAIN:'training participant', DEV:'development participant', outside_cohort:'participant outside the fitted cohort'}[trial.cohortRole] || 'imported recording';
    byId('replay-scope').textContent = role.charAt(0).toUpperCase() + role.slice(1) +
      ' · ' + (trial.coverage === 'full_source_trial' ? 'Full source trial' : 'Imported source window') +
      (Number.isFinite(trial.timeReferenceMs) ? ' · First available palm sample at ' + trial.timeReferenceMs + ' ms on the task clock' : '');
    status.textContent = matched + ' of ' + rows.length + ' time points have a recorded value and both estimates.';
    byId('replay-errors').textContent = matched
      ? 'Across these points, root mean squared error was ' + numberText(result.summary.baseline.rmseMm) +
        ' mm with timing and hand history, ' + numberText(result.summary.estimate.rmseMm) + ' mm with EEG added.'
      : 'An error comparison requires at least one matched point.';
    setLabels('Timing + hand', 'Timing + hand + EEG', 'Timing + hand', 'With EEG');
    byId('replay-input-picker').hidden = true;
    byId('replay-r2-errors').hidden = true;
    byId('replay-samples').hidden = false;
    byId('replay-figure').hidden = false;
    showRows(rows);
    const missing = explainIssues(trial.issues);
    byId('replay-missing').textContent = missing;
    byId('replay-missing').hidden = !missing;
    byId('replay-samples').open = matched < rows.length;
    output.hidden = false; exportButton.disabled = false;
    drawReplay(canvas, rows);
  }

  function compare() {
    const packet = selectedPacket();
    if (!packet || !readyFor(packet)) return;
    reset();
    try {
      if (isRunTwo(packet)) showR2(runR2(packet), packet);
      else showR1(scoreEegReplay(model, packet, {modelStateSha256: modelDigest}), packet);
    } catch (error) {
      reset();
      status.textContent = error.message || 'The benchmark could not read this trial.';
    }
  }

  inputs.addEventListener('change', plotR2Rows);
  picker.addEventListener('change', reset);
  run.addEventListener('click', compare);
  byId('replay-import').addEventListener('click', openImport);
  exportButton.addEventListener('click', () => {
    if (currentResult) download(isRunTwo(selectedPacket()) ? 'neurotranslation-personal-palm-replay.json' : 'neurotranslation-palm-replay.json', currentResult);
  });
  if (typeof ResizeObserver === 'function') {
    const observer = new ResizeObserver(() => { if (!output.hidden) drawReplay(canvas, rows); });
    observer.observe(canvas);
  } else window.addEventListener('resize', () => { if (!output.hidden) drawReplay(canvas, rows); });

  // The app loads only released study parameters. Imported observations stay in this browser.
  async function assetText(response) {
    if (!response.ok) throw new Error('Fitted parameters unavailable');
    return new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(await response.arrayBuffer());
  }
  const baseText = fetch('./palm-model.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.json').then(assetText);
  baseText.then(text => {
    const digest = sha256Hex(text);
    if (digest !== expectedModelSha256) throw new Error('Fitted parameters differ from the released model');
    const value = JSON.parse(text);
    validateEegReplayModel(value);
    modelDigest = digest; model = value;
    if (!isRunTwo(selectedPacket())) reset();
  }).catch(() => { loadError = true; reset(); });

  Promise.all([import('./r2-replay.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.mjs'), baseText, fetch('./r2-calibration-state.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.json').then(assetText),
    fetch('./r2-source.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.json').then(assetText), fetch('./r2-trial-index.4a04840c2566f457b57cd349f8ab92815e4b5908eeefa7d25fe07f06e734f416.json').then(assetText)])
    .then(([replay, baseModel, calibrationState, source, trialIndex]) => {
      const state = replay.loadR2ReplayState({baseModel, calibrationState, source, trialIndex});
      runR2 = packet => replay.scoreR2Replay(state, packet);
      if (isRunTwo(selectedPacket())) reset();
    }).catch(() => { r2LoadError = true; if (isRunTwo(selectedPacket())) reset(); });

  return function setPackets(packets) {
    if (packets === packetList) return;
    const oldId = candidates[picker.selectedIndex]?.dataset.id;
    packetList = packets;
    candidates = packets.filter(packet => packet.dataset.origin !== 'constructed_example');
    picker.replaceChildren();
    if (!candidates.length) picker.add(new Option('No recording imported', ''));
    for (const packet of candidates) {
      const duplicate = candidates.some(other => other !== packet && other.dataset.name === packet.dataset.name);
      picker.add(new Option(duplicate ? packet.dataset.name + ' (' + packet.dataset.id + ')' : packet.dataset.name, packet.dataset.id));
    }
    if (oldId && candidates.some(packet => packet.dataset.id === oldId)) picker.value = oldId;
    picker.disabled = !candidates.length;
    reset();
  };
}
