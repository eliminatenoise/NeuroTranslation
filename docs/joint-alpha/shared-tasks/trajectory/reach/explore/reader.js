(() => {
  const $ = id => document.getElementById(id);
  const data = globalThis.MacaquePaths;
  if (!data || data.schema !== 'measured-marker-trajectories-v1') {
    $('data-error').hidden = false;
    return;
  }
  const { families, prepare, visibleMarkers } = ReachGeometry;
  const examples = data.examples.map(prepare);
  const names = { past: 'Recorded past', ridge_point: 'Single fitted path', recorded: 'Measured next positions', ridge_residual: 'Past errors', ar_ridge: 'Step by step', diff_ridge: 'Remove noise' };
  let revealed = false;
  const canvas = $('plot');
  const viewer = canvas.getContext('2d') && createReachScene(canvas, key => { $('view').value = key; });
  if (!viewer) $('readings').open = true;
  for (let i = 1; i <= 32; i++) $('draw').add(new Option(String(i), String(i - 1)));

  function state() {
    return {
      focus: document.querySelector('input[name="focus"]:checked').value,
      families: families.filter(key => $(key).checked),
      horizon: Number($('horizon').value),
      draw: Number($('draw').value),
      ridge: $('ridge_point').checked,
      reveal: revealed,
    };
  }
  function timeLabel(ms) { return ms > 0 ? '+' + ms : String(ms).replace('-', '−'); }
  const numeric = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3, minimumFractionDigits: 3, useGrouping: false });
  function format(value) {
    return numeric.format(Math.abs(value) < .0005 ? 0 : value).replace('-', '−');
  }
  function updateTable() {
    if (!$('readings').open) return;
    const settings = state();
    const example = examples[Number($('example').value)];
    const markers = visibleMarkers(example, settings.focus);
    const key = $('series').value;
    const history = key === 'past';
    const times = history ? data.past_times_ms : data.future_times_ms.slice(0,settings.horizon);
    const rows = document.createDocumentFragment();
    for (let step = 0; step < times.length; step++) {
      for (const m of markers) {
        let path;
        if (history) path = m.past;
        else if (key === 'recorded') path = m.recorded;
        else if (key === 'ridge_point') path = m.ridge;
        else path = m.paths[key][settings.draw];
        const point = path[history ? step : step + 1];
        const row = document.createElement('tr');
        for (const value of [timeLabel(times[step]), m.site === 0 ? 'Hand' : 'Elbow', ...point.map(format)]) {
          const cell = document.createElement('td');
          cell.textContent = value;
          row.append(cell);
        }
        rows.append(row);
      }
    }
    $('positions').replaceChildren(rows);
    const draw = families.includes(key) ? ', path ' + (settings.draw + 1) : '';
    $('table-caption').textContent = example.label + ' · ' + names[key] + draw + ' · XYZ in mm';
  }
  function update() {
    const settings = state();
    const example = examples[Number($('example').value)];
    const previous = $('series').value;
    const keys = ['past'];
    if (settings.ridge) keys.push('ridge_point');
    keys.push(...settings.families);
    if (settings.reveal) keys.push('recorded');
    $('series').replaceChildren(...keys.map(key => new Option(names[key], key)));
    if (keys.includes(previous)) $('series').value = previous;
    $('draw').disabled = !settings.families.length;
    $('reveal').setAttribute('aria-pressed', String(revealed));
    $('reveal').textContent = revealed ? 'Hide measured path' : 'Reveal measured path';
    $('measured-key').hidden = !revealed;
    const f = settings.focus === 'both' ? 'Hand and elbow' : settings.focus === 'hand' ? 'Hand' : 'Elbow';
    const layers = keys.map(key => names[key]).join(', ');
    $('plot-summary').textContent = example.label + '. ' + f + '. Showing ' + layers + ' through ' + data.future_times_ms[settings.horizon - 1] + ' milliseconds. Read positions in the table below.';
    viewer?.update(example, settings);
    updateTable();
  }
  for (const element of document.querySelectorAll('.controls input, #horizon, #draw')) {
    element.addEventListener('change', update);
  }
  $('example').addEventListener('change', () => { revealed = false; update(); });
  $('reveal').addEventListener('click', () => { revealed = !revealed; update(); });
  $('view').addEventListener('change', () => { viewer?.preset($('view').value); });
  $('series').addEventListener('change', updateTable);
  $('readings').addEventListener('toggle', updateTable);
  update();
})();
