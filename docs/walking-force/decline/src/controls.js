(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const model = DeclineForce.create(JSON.parse(get('checkpoint').textContent));
  const example = DeclineForce.csvRows(JSON.parse(get('example').textContent));
  const channel = get('channel');
  const gain = get('gain');
  const file = get('file');
  const passes = get('passes');
  const usingMass = get('using-mass');
  const mass = get('mass');
  const slope = get('slope');
  const rows = get('forecast-rows');
  const canvas = get('trace');
  const recentStart = 120;
  const voltsToMicrovolts = 1e6;
  const digits = new Intl.NumberFormat('en', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  let original = example;
  let sourceRevision = 0;
  let pendingFrame = null;

  function showError(id, message = '') {
    const element = get(id);
    element.textContent = message;
    element.hidden = !message;
  }

  function paint(base, revised, index) {
    const context = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (!context || width < 1 || height < 1) return;
    const dpi = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpi);
    canvas.height = Math.round(height * dpi);
    context.setTransform(dpi, 0, 0, dpi, 0, 0);
    const top = 12, bottom = height - 29, left = 47, right = width - 14;
    const middle = (top + bottom) / 2;
    const peak = Math.max(1, ...base.map(Math.abs), ...revised.map(Math.abs)) * 1.05;
    const x = i => left + (right - left) * i / (base.length - 1);
    const y = u => middle - u / peak * ((bottom - top) / 2);

    context.fillStyle = '#e5f2ef';
    context.fillRect(x(recentStart), top, right - x(recentStart), bottom - top);
    context.strokeStyle = '#b5c6c9';
    context.lineWidth = 1;
    context.beginPath();
    for (const guide of [top, middle, bottom]) {
      context.moveTo(left, guide);
      context.lineTo(right, guide);
    }
    context.stroke();
    context.fillStyle = '#435b60';
    context.font = '11px system-ui, sans-serif';
    context.textAlign = 'right';
    const tick = u => Math.abs(u) < 10000 ? Math.round(u).toString() : u.toExponential(1);
    context.fillText(tick(peak), left - 6, top + 4);
    context.fillText('0', left - 6, middle + 4);
    context.fillText(tick(-peak), left - 6, bottom + 4);
    context.textAlign = 'left';
    context.fillText('210 ms before', left, bottom + 16);
    context.textAlign = 'right';
    context.fillText('10.5 ms before', right, bottom + 16);

    function draw(points, colour, lineWidth) {
      context.beginPath();
      context.moveTo(x(0), y(points[0]));
      for (let i = 1; i < points.length; i++) context.lineTo(x(i), y(points[i]));
      context.strokeStyle = colour;
      context.lineWidth = lineWidth;
      context.stroke();
    }
    if (Number(gain.value) !== 1) draw(base, '#93a6aa', 1);
    draw(revised, '#087c70', 1.7);
    const minimum = tick(Math.min(...revised)), maximum = tick(Math.max(...revised));
    canvas.setAttribute('aria-label', `${DeclineForce.channels[index]} voltage history. ${minimum} to ${maximum} microvolts.`);
  }

  function display(prediction, depth) {
    const total = pair => pair[0] + pair[1];
    const methods = [
      [`Compact · ${depth} ${depth === 1 ? 'pass' : 'passes'}`, [...prediction.attention, total(prediction.attention)]],
      ['Linear fit', [...prediction.linear, total(prediction.linear)]],
      ['Relative-muscle fit and blend', [...prediction.relativeMuscle, total(prediction.relativeMuscle)]],
      [usingMass.checked ? 'Static weight on the slope' : 'Typical total from fitting', [null, null, prediction.reference]],
    ];
    const tableRows = methods.map(([name, values], index) => {
      const row = document.createElement('tr');
      if (index === 0) row.className = 'compact';
      const heading = document.createElement('th');
      heading.scope = 'row';
      heading.textContent = name;
      row.append(heading);
      for (const value of values) {
        const cell = document.createElement('td');
        cell.textContent = value === null ? '—' : digits.format(Math.abs(value) < .005 ? 0 : value);
        if (value !== null) cell.dataset.value = value;
        row.append(cell);
      }
      return row;
    });
    rows.replaceChildren(...tableRows);
    get('announce').textContent = `Compact forecast total ${tableRows[0].cells[3].textContent} newton-seconds.`;
  }

  function redraw() {
    pendingFrame = null;
    const index = Number(channel.value);
    const factor = Number(gain.value);
    const depth = Number(passes.value);
    const adjusted = original.map((row, time) => time < recentStart || factor === 1
      ? row : row.map((value, c) => c === index ? value * factor : value));
    get('gain-value').value = factor.toFixed(2) + '×';
    get('trace-note').textContent = factor === 1
      ? 'Voltage in microvolts. The shaded area marks the last 140 milliseconds of the input.'
      : 'Voltage in microvolts. The grey line shows the original voltages before the change.';
    paint(original.map(row => row[index] * voltsToMicrovolts), adjusted.map(row => row[index] * voltsToMicrovolts), index);
    get('mass-inputs').hidden = !usingMass.checked;
    get('context-note').hidden = !usingMass.checked;
    if (usingMass.checked) {
      get('context-note').textContent = original === example
        ? 'The invented example starts at 72 kg and −10°. Use a negative angle for a downhill slope.'
        : 'Use the measured body mass and slope for this history. Use a negative angle for a downhill slope.';
    }
    try {
      const condition = usingMass.checked ? {mass: mass.valueAsNumber, slope: slope.valueAsNumber} : null;
      display(model.predict(DeclineForce.relativeHistory(adjusted), depth, condition), depth);
      showError('forecast-error');
    } catch (error) {
      rows.replaceChildren();
      get('announce').textContent = '';
      showError('forecast-error', error.message);
    }
  }

  function schedule() {
    if (pendingFrame === null) pendingFrame = requestAnimationFrame(redraw);
  }

  file.addEventListener('change', async () => {
    const chosen = file.files[0];
    if (!chosen) return;
    const revision = ++sourceRevision;
    showError('file-error');
    try {
      if (chosen.size > 512 * 1024) throw Error('Choose a voltage CSV smaller than 512 KiB.');
      const candidate = DeclineForce.csvRows(await chosen.text());
      DeclineForce.relativeHistory(candidate);
      if (revision !== sourceRevision) return;
      original = candidate;
      get('active-source').textContent = chosen.name;
      gain.value = '1';
      mass.value = '';
      slope.value = '';
      usingMass.checked = false;
      passes.value = '5';
      schedule();
    } catch (error) {
      if (revision !== sourceRevision) return;
      file.value = '';
      showError('file-error', error.message);
    }
  });

  get('reset').addEventListener('click', () => {
    sourceRevision++;
    original = example;
    get('active-source').textContent = 'Invented example';
    file.value = '';
    channel.value = '0';
    gain.value = '1';
    mass.value = '72';
    slope.value = '-10';
    usingMass.checked = true;
    passes.value = '9';
    showError('file-error');
    schedule();
  });

  usingMass.addEventListener('change', () => {
    passes.value = usingMass.checked ? '9' : '5';
    schedule();
  });
  for (const input of [channel, gain, passes, mass, slope]) input.addEventListener('input', schedule);
  window.addEventListener('resize', schedule);
  redraw();
})();
