'use strict';

{
  const select = id => document.getElementById(id);
  const status = select('status');
  const settings = ['mode', 'passes', 'checkpoint'].map(select);
  const tissueIds = ['triceps-track', 'brachialis-track'];
  const payload = globalThis.ReachingCheckpoint;

  function message(value, error = false) {
    status.textContent = value;
    status.dataset.state = error ? 'error' : 'ready';
  }

  function showHistory(history, mode) {
    const bins = globalThis.ReachingForecast.upperBin(mode);
    tissueIds.forEach((id, tissue) => {
      const track = select(id);
      const items = history.map((row, index) => {
        const item = document.createElement('li');
        const state = index >= bins ? 'withheld' : row[24 + tissue] ? 'used' : 'missing';
        const time = `${(10 - index) * 20} to ${(9 - index) * 20} ms before forecast`;
        const value = state === 'used' ? `${row[22 + tissue].toFixed(3)} mm`
          : state === 'withheld' ? 'hidden' : 'missing';
        item.className = state;
        item.title = `${time}, ${value}`;
        item.setAttribute('aria-label', item.title);
        return item;
      });
      track.replaceChildren(...items);
    });
    select('history-explanation').textContent = mode === 'gap'
      ? 'The latest five slots are hidden. Earlier readings are used where available.'
      : mode === 'blind' ? 'All ten ultrasound slots are hidden.'
        : 'The 200 ms history is available wherever a reading was recorded.';
  }

  function clearEstimates() {
    for (const cell of document.querySelectorAll('[data-value]')) {
      cell.textContent = '—';
      delete cell.dataset.value;
    }
  }

  try {
    const engine = globalThis.ReachingForecast.create(payload);
    let sample = payload.example;
    let generation = 0;

    function compute(current) {
      const [mode, passes, seed] = settings.map(field => field.value);
      const result = engine.compare(current, {mode, passes: [Number(passes)], seed});
      return {mode, values: [...result.simple, ...result.linear, ...result.forecast[passes]]};
    }

    function show(current, result) {
      const cells = document.querySelectorAll('[data-value]');
      result.values.forEach((value, index) => {
        cells[index].textContent = value.toFixed(3);
        cells[index].dataset.value = String(value);
      });
      showHistory(current.history, result.mode);
    }

    show(sample, compute(sample));
    for (const field of settings) {
      field.addEventListener('change', () => {
        try {
          show(sample, compute(sample));
          message('');
        } catch (error) {
          clearEstimates();
          message(error.message, true);
        }
      });
    }

    select('file').addEventListener('change', async event => {
      const file = event.target.files[0];
      event.target.value = '';
      if (!file) return;
      const attempt = ++generation;
      try {
        if (file.size > 1024 * 1024) throw new Error('Choose one JSON history smaller than 1 MB.');
        const current = JSON.parse(await file.text());
        if (attempt !== generation) return;
        globalThis.ReachingForecast.validate(current, 'full');
        const result = compute(current);
        sample = current;
        show(sample, result);
        select('source').textContent = file.name;
        message('Local history opened.');
      } catch (error) {
        if (attempt === generation) {
          message(error instanceof SyntaxError ? 'This file could not be read as JSON.' : error.message, true);
        }
      }
    });

    select('reset').addEventListener('click', () => {
      generation++;
      sample = payload.example;
      select('source').textContent = 'Invented example';
      show(sample, compute(sample));
      message('Example restored.');
    });
  } catch {
    clearEstimates();
    for (const field of [...settings, select('file'), select('reset')]) field.disabled = true;
    message('The model could not load. Reopen the page or extract the complete browser package.', true);
  }
}
