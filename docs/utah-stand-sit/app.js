'use strict';

const examples = {
  steady: [[227, 192], [229, 191], [231, 191], [230, 193], [232, 193],
    [230, 191], [231, 192], [230, 191], [228, 192], [229, 192]],
  rising: [[108, 93], [111, 96], [132, 106], [153, 127], [183, 149],
    [218, 173], [251, 202], [279, 225], [303, 247], [319, 258]],
  falling: [[319, 258], [303, 247], [279, 225], [251, 202], [218, 173],
    [183, 149], [153, 127], [132, 106], [111, 96], [108, 93]],
};

const methods = ['persistence', 'dampedTrend', 'attention'];
const series = [
  {color: '#1257a0', dash: [], plate: 2},
  {color: '#a95213', dash: [6, 4], plate: 3},
];
const selectedExample = document.getElementById('example');
const bins = document.getElementById('force-bins');
const canvas = document.getElementById('history-chart');
const status = document.getElementById('model-status');
const formatImpulse = new Intl.NumberFormat('en', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const formatForce = new Intl.NumberFormat('en', {maximumFractionDigits: 2});
const formatTick = new Intl.NumberFormat('en', {maximumFractionDigits: 0});

const intervalCount = 10;
const intervalDuration = 20;
const inputs = Array.from({length: intervalCount}, (_, i) => {
  const row = bins.insertRow();
  const start = i * intervalDuration - 200;
  const end = start + intervalDuration;
  const time = document.createElement('th');
  time.scope = 'row';
  time.textContent = `${start} to ${end}`.replaceAll('-', '−');
  row.append(time);
  return series.map(({plate}) => {
    const input = document.createElement('input');
    input.type = 'number';
    input.step = 'any';
    input.required = true;
    input.setAttribute('aria-label', `Plate ${plate} force from ${start} to ${end} ms (newtons)`);
    row.insertCell().append(input);
    return input;
  });
});

let plottedHistory = [];

function drawHistory() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const context = canvas.getContext('2d');
  if (!context) return;

  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.scale(pixelRatio, pixelRatio);

  const values = plottedHistory.flat().filter(Number.isFinite);
  const unit = Math.max(1, ...values.map(Math.abs));
  const low = Math.min(0, ...values) / unit;
  const high = values.length ? Math.max(0, ...values) / unit : 1;
  const span = high - low || 1;
  const left = 50;
  const right = width - 15;
  const top = 31;
  const bottom = height - 39;
  const xAt = elapsed => left + (right - left) * elapsed / 200;
  const yAt = normalizedForce => bottom - (normalizedForce - low) * (bottom - top) / span;

  context.fillStyle = '#405966';
  context.font = '12px system-ui, sans-serif';
  context.fillText('Force (N)', 3, 15);
  context.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const normalized = low + span * i / 4;
    const y = yAt(normalized);
    const amount = normalized * unit;
    const label = Math.abs(amount) >= 10000 ? amount.toExponential(1) :
      Math.abs(amount) >= 10 ? formatTick.format(amount) : formatForce.format(amount);
    context.strokeStyle = '#d4e0e7';
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(right, y);
    context.stroke();
    context.fillText(label, left - 6, y + 4);
  }
  if (low < 0 && high > 0) {
    context.strokeStyle = '#8095a2';
    context.beginPath();
    context.moveTo(left, yAt(0));
    context.lineTo(right, yAt(0));
    context.stroke();
  }

  context.textAlign = 'center';
  for (const elapsed of [0, 100, 200]) {
    const label = String(elapsed - 200).replace('-', '−');
    context.fillText(label, xAt(elapsed), bottom + 15);
  }
  context.fillText('Time (ms)', (left + right) / 2, height - 5);

  series.forEach(({color, dash}, column) => {
    context.strokeStyle = color;
    context.lineWidth = 2;
    context.setLineDash(dash);
    context.beginPath();
    let gap = true;
    plottedHistory.forEach((row, index) => {
      const force = row[column];
      if (!Number.isFinite(force)) {
        gap = true;
        return;
      }
      const x = xAt((index + .5) * intervalDuration);
      const y = yAt(force / unit);
      if (gap) context.moveTo(x, y);
      else context.lineTo(x, y);
      gap = false;
    });
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = color;
    plottedHistory.forEach((row, index) => {
      if (!Number.isFinite(row[column])) return;
      context.beginPath();
      context.arc(xAt((index + .5) * intervalDuration), yAt(row[column] / unit), 2.5, 0, 2 * Math.PI);
      context.fill();
    });
  });
}

function showForecast(result) {
  for (const method of methods) {
    const values = result ? [...result[method], result[method][0] + result[method][1]] : [];
    const cells = document.getElementById(method).querySelectorAll('td');
    cells.forEach((cell, i) => {
      cell.textContent = result ? formatImpulse.format(values[i]) : '—';
    });
  }
}

function resultIsValid(result) {
  return typeof result?.rising === 'boolean' && Number.isFinite(result.loadChangeN) &&
    methods.every(method => Array.isArray(result[method]) && result[method].length === 2 &&
      result[method].every(Number.isFinite) && Number.isFinite(result[method][0] + result[method][1]));
}

function setStatus(message, state) {
  status.dataset.state = state;
  if (status.textContent !== message) status.textContent = message;
}

function describeChange(change) {
  if (change === 0) return 'The average combined force was unchanged between the first and last 40 ms.';
  const magnitude = Math.abs(change);
  let amount = formatForce.format(magnitude);
  if (magnitude < .005) amount = 'less than 0.01';
  else if (amount === '50' && magnitude !== 50) amount = magnitude > 50 ? 'just over 50' : 'just under 50';
  return `The average combined force ${change > 0 ? 'rose' : 'fell'} by ${amount} N from the first 40 ms to the last 40 ms.`;
}

function update() {
  let invalid = false;
  plottedHistory = inputs.map(row => row.map(input => {
    const value = input.valueAsNumber;
    const valid = Number.isFinite(value);
    input.setAttribute('aria-invalid', String(!valid));
    invalid ||= !valid;
    return value;
  }));
  drawHistory();

  if (invalid) {
    showForecast(null);
    setStatus('Enter a finite number for each force to calculate a forecast.', 'invalid');
    return;
  }

  if (typeof globalThis.standSitForce?.predict !== 'function') {
    showForecast(null);
    setStatus('The prediction scripts did not load. Reopen the page with weights.js and predict.js in the same folder.', 'invalid');
    return;
  }

  try {
    const forecast = globalThis.standSitForce.predict(plottedHistory);
    if (!resultIsValid(forecast)) throw new Error('Invalid forecast values');
    showForecast(forecast);
    const state = forecast.rising ? 'active' : 'inactive';
    setStatus(`Correction ${state}. ${describeChange(forecast.loadChangeN)}`, state);
  } catch {
    showForecast(null);
    setStatus('The model could not produce a forecast from these values. Edit the forces or choose an example.', 'invalid');
  }
}

function loadExample(name) {
  const history = examples[name];
  if (!history) return;
  inputs.forEach((row, i) => row.forEach((input, plate) => {
    input.value = String(history[i][plate]);
  }));
  update();
}

selectedExample.addEventListener('change', () => loadExample(selectedExample.value));
bins.addEventListener('input', () => {
  selectedExample.value = 'edited';
  update();
});
if (typeof ResizeObserver === 'function') new ResizeObserver(drawHistory).observe(canvas);
else window.addEventListener('resize', drawHistory);

loadExample(selectedExample.value);
