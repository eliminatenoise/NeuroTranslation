import {normalizeFinite} from './plot.mjs';
import {sha256Hex} from './hash.mjs';
import {scoreEegReplay, validateEegReplayModel} from './palm-model.mjs';

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
  if (!rows.length || !canvas.clientWidth || !canvas.clientHeight) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  ctx.scale(canvas.width / w, canvas.height / h);
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
  let model, modelDigest, loadError = false, packetList, candidates = [], currentResult, rows = [], generation = 0;

  function reset() {
    generation++;
    currentResult = undefined; rows = []; output.hidden = true;
    exportButton.disabled = true;
    run.disabled = !model || candidates.length === 0;
    if (loadError) status.textContent = 'The fitted benchmark could not be loaded. Reload the page to try again.';
    else if (candidates.length === 0) status.textContent = 'Import an IACKD trial packet to compare its palm position with the fitted estimates.';
    else if (!model) status.textContent = 'Loading fitted benchmark parameters…';
    else status.textContent = 'Choose a recording and compare the estimates on its original trial clock.';
  }

  function showRows(trial) {
    const table = byId('replay-rows');
    table.replaceChildren();
    for (const row of trial.rows) {
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

  async function compare() {
    const packet = candidates[picker.selectedIndex];
    if (!packet || !model) return;
    reset();
    const token = generation;
    run.disabled = true;
    try {
      const result = await scoreEegReplay(model, packet, { modelStateSha256: modelDigest });
      if (token !== generation) return;
      const trial = result.trials?.[0];
      if (!trial || !trial.rows?.length) {
        status.textContent = explainIssues([...(result.diagnostics || []), ...(trial?.issues || [])]) ||
          'This recording lacks the channels, units or clock required by the palm benchmark.';
        return;
      }
      rows = trial.rows; currentResult = result;
      const matched = rows.filter(row => [row.targetMm, row.estimateMm, row.baselineMm].every(Number.isFinite));
      byId('replay-name').textContent = packet.dataset.name;
      const role = {TRAIN:'training participant', DEV:'development participant', outside_cohort:'participant outside the fitted cohort'}[trial.cohortRole] || 'imported recording';
      byId('replay-scope').textContent = role.charAt(0).toUpperCase() + role.slice(1) +
        ' · ' + (trial.coverage === 'full_source_trial' ? 'Full source trial' : 'Imported source window') +
        (Number.isFinite(trial.timeReferenceMs) ? ' · First available palm sample at ' + trial.timeReferenceMs + ' ms on the task clock' : '');
      status.textContent = matched.length + ' of ' + rows.length + ' time points have a recorded value and both estimates.';
      const errors = byId('replay-errors');
      if (matched.length) {
        errors.textContent = 'Across these points, root mean squared error was ' + numberText(result.summary.baseline.rmseMm) +
          ' mm with timing and hand history, ' + numberText(result.summary.estimate.rmseMm) + ' mm with EEG added.';
      } else errors.textContent = 'An error comparison requires at least one matched point.';
      showRows(trial);
      const missing = explainIssues(trial.issues);
      byId('replay-missing').textContent = missing;
      byId('replay-missing').hidden = !missing;
      byId('replay-samples').open = matched.length < rows.length;
      output.hidden = false; exportButton.disabled = false;
      drawReplay(canvas, rows);
    } catch (error) {
      if (token === generation) status.textContent = error.message || 'The benchmark could not read this trial.';
    } finally {
      if (token === generation) run.disabled = !model || !candidates.length;
    }
  }

  picker.addEventListener('change', reset);
  run.addEventListener('click', compare);
  byId('replay-import').addEventListener('click', openImport);
  exportButton.addEventListener('click', () => {
    if (currentResult) download('neurotranslation-palm-replay.json', currentResult);
  });
  if (typeof ResizeObserver === 'function') {
    const observer = new ResizeObserver(() => { if (!output.hidden) drawReplay(canvas, rows); });
    observer.observe(canvas);
  } else window.addEventListener('resize', () => { if (!output.hidden) drawReplay(canvas, rows); });

  // Fetch only the static fitted parameters. Imported recordings stay in memory.
  fetch('./palm-model.json').then(response => {
    if (!response.ok) throw new Error('Fitted parameters unavailable');
    return response.arrayBuffer();
  }).then(buffer => {
    const bytes = new Uint8Array(buffer);
    const digest = sha256Hex(bytes);
    if (digest !== expectedModelSha256) throw new Error('Fitted parameters differ from the released model');
    const value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
    validateEegReplayModel(value);
    modelDigest = digest; model = value; reset();
  })
    .catch(() => { loadError = true; reset(); });

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
