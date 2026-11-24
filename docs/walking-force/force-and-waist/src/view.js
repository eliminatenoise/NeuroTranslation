(() => {
  const payload = JSON.parse(document.getElementById('payload').textContent);
  const model = ForceWaist.create(payload);
  const labels = ['Keep the latest average', 'Extend the recent trend', 'Ridge regression', 'Shared attention'];
  const tasks = {
    force: {
      channels: ['Vertical force (N)'],
      output: ['N·s'],
      label: 'Vertical force impulse',
      meaning: 'Impulse adds force over time. A steady 300 N for 100 ms gives 30 N·s.',
      benchmark: 'Mean absolute impulse error',
      benchmarkUnit: 'N·s'
    },
    waist: {
      channels: ['Acceleration X (g)', 'Acceleration Y (g)', 'Acceleration Z (g)',
        'Rotation X (rad/s)', 'Rotation Y (rad/s)', 'Rotation Z (rad/s)'],
      output: ['X', 'Y', 'Z'],
      label: 'Average rotation rate (rad/s)',
      meaning: 'X, Y and Z are the watch’s axes. These values describe how fast the watch turns.',
      benchmark: 'Three-axis rotation error',
      benchmarkUnit: 'rad/s'
    }
  };
  const byId = id => document.getElementById(id);
  const canvas = byId('plot');
  const channel = byId('channel');
  const editor = byId('editor');
  const inputs = byId('inputs');
  const outputs = byId('outputs');
  const status = byId('status');
  const tabs = [...document.querySelectorAll('[data-task]')];
  const examples = key => payload.examples[key].map(row => [...row]);
  const histories = {force: examples('force'), waist: examples('waist')};
  let task = 'force';
  let column = 0;
  let editors = [];

  function element(name, text) {
    const item = document.createElement(name);
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function header(table, labels) {
    table.replaceChildren();
    const row = table.createTHead().insertRow();
    for (const label of labels) {
      const heading = element('th', label);
      heading.scope = 'col';
      row.append(heading);
    }
    return table.createTBody();
  }

  function rowHead(row, label) {
    const item = element('th', label);
    item.scope = 'row';
    row.append(item);
  }

  const decimal = (value, digits) => value === null ? 'Unavailable'
    : Math.abs(value) >= 1e6 ? value.toExponential(2)
    : value.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});

  function setupEditor() {
    const history = histories[task];
    const name = tasks[task].channels[column];
    const selected = column;
    const body = header(inputs, ['Bin ends', name]);
    editors = history.map((row, i) => {
      const entries = body.insertRow();
      const time = (i - 9) * 20;
      rowHead(entries, time + ' ms');
      const input = element('input');
      input.type = 'number';
      input.step = 'any';
      input.inputMode = 'text';
      input.setAttribute('aria-label', name + ', ' + time + ' ms');
      input.value = row[selected] ?? '';
      input.setAttribute('aria-invalid', String(row[selected] === null));
      input.addEventListener('input', () => {
        const next = input.valueAsNumber;
        const valid = Number.isFinite(Math.fround(next));
        row[selected] = valid ? next : null;
        input.setAttribute('aria-invalid', String(!valid));
        update();
      });
      entries.insertCell().append(input);
      return input;
    });
  }

  function draw() {
    byId('chart-label').textContent = tasks[task].channels[column];
    historyChart.draw(canvas, histories[task].map(row => row[column]));
  }

  function update() {
    draw();
    let forecasts;
    try {
      forecasts = model.predict(task, histories[task]);
      status.hidden = true;
      status.textContent = '';
    } catch (error) {
      status.hidden = false;
      status.textContent = error.message;
      forecasts = labels.map(() => tasks[task].output.map(() => null));
    }
    const tbody = header(outputs, ['Method', ...tasks[task].output]);
    forecasts.forEach((values, i) => {
      const row = tbody.insertRow();
      rowHead(row, labels[i]);
      values.forEach(value => { row.insertCell().textContent = decimal(value, task === 'force' ? 2 : 3); });
    });
  }

  function showBenchmark() {
    const metadata = tasks[task];
    const scope = task === 'force' ? byId('benchmark-scope').value : 'all';
    const methodScores = payload.benchmark[task].scores;
    const support = methodScores.latest_mean[scope];
    byId('benchmark-filter').hidden = task !== 'force';
    byId('benchmark-detail').textContent = metadata.benchmark + ' on ' +
      support.windows.toLocaleString('en-US') + ' windows from ' + support.people + ' held participants.';
    const benchmark = header(byId('bench-results'), ['Method', metadata.benchmarkUnit]);
    model.methods.forEach((name, i) => {
      const row = benchmark.insertRow();
      rowHead(row, labels[i]);
      row.insertCell().textContent = decimal(methodScores[name][scope].mean, 3);
    });
  }

  function activate(next) {
    task = next;
    column = task === 'force' ? 0 : 3;
    const metadata = tasks[task];
    tabs.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.task === task)));
    channel.replaceChildren(...metadata.channels.map((label, i) => new Option(label, i)));
    channel.value = column;
    byId('channel-control').hidden = task === 'force';
    byId('output-label').textContent = metadata.label;
    byId('meaning').textContent = metadata.meaning;
    showBenchmark();
    setupEditor();
    update();
  }

  tabs.forEach(tab => tab.addEventListener('click', () => activate(tab.dataset.task)));
  channel.addEventListener('change', () => { column = Number(channel.value); setupEditor(); draw(); });
  byId('benchmark-scope').addEventListener('change', showBenchmark);
  byId('reset').addEventListener('click', () => {
    histories[task] = examples(task);
    setupEditor();
    update();
  });
  canvas.addEventListener('click', event => {
    const bin = historyChart.binAt(canvas, event.clientX - canvas.getBoundingClientRect().left);
    editor.open = true;
    editors[bin].focus();
  });
  if (location.protocol === 'file:') {
    byId('offline-link').hidden = true;
    for (const [id, file] of [['simple-link', 'SIMPLE.md'], ['technical-link', 'TECHNICAL.md']]) {
      const link = byId(id);
      if (link) link.href = file;
    }
  }
  activate('force');
  new ResizeObserver(draw).observe(canvas);
})();
