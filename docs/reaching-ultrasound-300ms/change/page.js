(() => {
  'use strict';

  const entries = [
    ['zero_change', 'Predict no change'],
    ['absolute_motion_ridge', 'Linear motion forecast'],
    ['relative_motion_u800_p1', 'Motion from start'],
    ['absolute_motion_emg_u1600_p3', 'Position and muscle activity'],
    ['relative_motion_emg_u1600_p3', 'Motion from start and muscle activity'],
  ];

  const model = globalThis.NeuroTranslateReachingChange;
  const data = globalThis.NeuroTranslateReachingChangeExample;
  const byId = name => document.getElementById(name);
  const input = byId('file');
  const number = byId('example-number');
  const numberLabel = byId('example-number-label');
  const status = byId('status');
  const source = byId('source');
  const forecastRows = byId('forecast-values');
  const scoredRows = byId('scored-values');
  const scaleNote = byId('scale');
  let output;
  let request = 0;

  function showStatus(message, error = false) {
    status.textContent = message;
    status.classList.toggle('error', error);
  }

  function numberText(value, digits) {
    const display = value.toFixed(digits);
    return Number(display) === 0 ? (0).toFixed(digits) : display;
  }

  function fillTable(rows, valuesFor, digits, limit = 0) {
    const fragment = document.createDocumentFragment();
    for (const [method, label] of entries) {
      const row = document.createElement('tr');
      row.dataset.method = method;
      const name = document.createElement('th');
      name.scope = 'row';
      name.textContent = label;
      row.append(name);
      for (const value of valuesFor(method)) {
        const cell = document.createElement('td');
        cell.textContent = numberText(value, digits);
        if (limit) {
          const track = document.createElement('div');
          track.className = 'track';
          track.setAttribute('aria-hidden', 'true');
          const fill = document.createElement('div');
          fill.className = value < 0 ? 'fill negative' : 'fill';
          const length = 50 * Math.abs(value) / limit;
          fill.style.setProperty('--start', `${value < 0 ? 50 - length : 50}%`);
          fill.style.setProperty('--length', `${length}%`);
          track.append(fill);
          cell.append(track);
        }
        row.append(cell);
      }
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
  }

  function showHistory(index) {
    const values = name => output.change_in_spread_mm[name][index];
    const limit = Math.max(0.0001, ...entries.flatMap(([name]) => values(name).map(Math.abs)));
    fillTable(forecastRows, values, 4, limit);
    scaleNote.textContent = `Bars share a scale from −${limit.toPrecision(3)} mm to +${limit.toPrecision(3)} mm. The centre mark is zero.`;
    scaleNote.hidden = false;
  }

  function run(history, label) {
    const result = model.forecast(history);
    const count = result.change_in_spread_mm.zero_change.length;
    output = result;
    number.replaceChildren();
    for (let i = 0; i < count; i++) {
      const option = document.createElement('option');
      option.value = i;
      option.textContent = `${i + 1} of ${count}`;
      number.append(option);
    }
    number.hidden = numberLabel.hidden = count === 1;
    source.textContent = label;
    showHistory(0);
  }

  function restore() {
    request++;
    input.value = '';
    run(data.history, 'Invented example');
    showStatus('');
  }

  async function loadFile() {
    const file = input.files[0];
    if (!file) return;
    const id = ++request;
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('Use a JSON file smaller than 2 MB.');
      const contents = await file.text();
      if (id !== request) return;
      const {history} = JSON.parse(contents);
      if (!Array.isArray(history)) throw new Error('Add the array of readings under “history”.');
      if (Array.isArray(history[0]?.[0]) && history.length > 50) throw new Error('Use at most 50 histories in a file.');
      run(history, file.name);
      showStatus('Forecast updated.');
    } catch (error) {
      if (id !== request) return;
      input.value = '';
      const detail = error instanceof SyntaxError ? 'Check that the file contains valid JSON.' : error.message;
      showStatus(`Could not use the file. The previous forecast is still shown. ${detail}`, true);
    }
  }

  if (!model || !data) {
    showStatus('The forecast files could not load. Extract all the files into one folder and open index.html again.', true);
    input.disabled = byId('reset').disabled = true;
    return;
  }
  fillTable(scoredRows, name => data.scored_errors_mm[name], 4);
  input.addEventListener('change', loadFile);
  number.addEventListener('change', () => showHistory(Number(number.value)));
  byId('reset').addEventListener('click', restore);
  restore();
})();
