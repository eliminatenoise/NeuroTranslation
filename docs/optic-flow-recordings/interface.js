(() => {
  'use strict';

  const element = id => document.getElementById(id);
  const scale = element('movement');
  const scaleValue = element('movement-value');
  const reverseCurrent = element('reverse-command');
  const reverseEarlier = element('reverse-earlier');
  const input = element('case-input');
  const status = element('forecast-status');
  const inputSource = element('input-source');
  const result = element('forecast-json');
  const jsonPanel = element('copy-forecast');
  const rows = Array.from(document.querySelectorAll('tr[data-method]'));

  function draw(values) {
    const spreads = values === null ? [] : rows.map(row => values[row.dataset.method]);
    if (spreads.some(value => !Number.isFinite(value) || value < 0)) {
      throw new Error('The model returned an invalid spread.');
    }
    const max = Math.max(...spreads, 0.000001);
    rows.forEach((row, index) => {
      const value = values === null ? 0 : spreads[index];
      row.querySelector('[data-spread]').textContent = values === null ? '—' : value.toFixed(6);
      const meter = row.querySelector('meter');
      meter.max = max;
      meter.value = value;
    });
    result.textContent = values === null ? '' : JSON.stringify(values, null, 2);
    jsonPanel.hidden = values === null;
  }

  function run() {
    status.classList.remove('invalid');
    try {
      const values = globalThis.ZebrafishForecast.predict(JSON.parse(input.value));
      draw(values);
      status.textContent = values === null ? 'This row is marked ineligible.' : 'All seven forecasts calculated.';
    } catch (error) {
      draw(null);
      status.classList.add('invalid');
      status.textContent = 'Forecast unavailable. ' + error.message;
    }
  }

  function markEdited(source) {
    const manual = source === 'manual';
    inputSource.textContent = manual ? 'Edited input' : 'Invented example';
    scale.disabled = manual;
    reverseCurrent.disabled = manual;
    reverseEarlier.disabled = manual;
    status.classList.remove('invalid');
    status.textContent = manual
      ? 'Calculate the edited forecast or restore the example to use its controls.'
      : 'Choose Calculate forecast to apply the current input.';
    draw(null);
  }

  function setExample() {
    const row = structuredClone(globalThis.ZebrafishForecastExample);
    const factor = Number(scale.value) / 100;
    row.camera_stats_rad = row.camera_stats_rad.map(pair => pair.map(value => value * factor));
    row.recent_spread_rad *= factor;
    if (reverseCurrent.checked) row.command_codes = row.command_codes.map(value => -value);
    if (reverseEarlier.checked) row.earlier_command_codes = row.earlier_command_codes.map(value => -value);
    scaleValue.textContent = scale.value + '%';
    input.value = JSON.stringify(row, null, 2);
    markEdited('example');
  }

  function restore() {
    scale.value = '100';
    reverseCurrent.checked = false;
    reverseEarlier.checked = false;
    setExample();
    run();
  }

  if (!globalThis.ZebrafishForecast || !globalThis.ZebrafishForecastExample) {
    status.classList.add('invalid');
    status.textContent = 'The fitted model files could not open. Extract the whole ZIP and leave its files together.';
    for (const id of ['movement', 'reverse-command', 'reverse-earlier', 'calculate', 'restore', 'case-input']) {
      element(id).disabled = true;
    }
    return;
  }

  scale.addEventListener('input', setExample);
  reverseCurrent.addEventListener('change', setExample);
  reverseEarlier.addEventListener('change', setExample);
  input.addEventListener('input', () => markEdited('manual'));
  element('calculate').addEventListener('click', run);
  element('restore').addEventListener('click', restore);
  restore();
})();
