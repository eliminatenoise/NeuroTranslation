(() => {
  'use strict';

  const model = globalThis.NeuroTranslateFingerAngle;
  const study = globalThis.NeuroTranslateFingerStudy;
  const byId = id => document.getElementById(id);
  const input = byId('history-file');
  const finger = byId('finger');
  const slider = byId('angle');
  const useEcho = byId('ultrasound');
  const chartMethod = byId('chart-method');
  const canvas = byId('chart');
  const inputStatus = byId('input-status');
  const labels = {
    zero_change: 'Keep latest angle', past_angle_trend: 'Continue recent trend',
    angle_ridge: 'Linear angles', angle_recurrent: 'Recurrent angles',
    joint_ridge_absolute: 'Linear angles + ultrasound', joint_recurrent_absolute: 'Recurrent angles + ultrasound',
    joint_ridge_relative: 'Linear angles + ultrasound change', joint_recurrent_relative: 'Recurrent angles + ultrasound change',
    ultrasound_ridge_absolute: 'Linear ultrasound', ultrasound_recurrent_absolute: 'Recurrent ultrasound',
    ultrasound_ridge_relative: 'Linear ultrasound change', ultrasound_recurrent_relative: 'Recurrent ultrasound change',
  };
  let readings;
  let forecast;
  let originalExample = true;
  let fileRequest = 0;

  function status(message, fault = false) {
    inputStatus.textContent = message;
    inputStatus.classList.toggle('error', fault);
  }

  if (!model || !study) {
    status('The page could not load the model. Extract all files into one folder and open index.html again.', true);
    return;
  }

  function degrees(value) {
    const readable = Number(value.toFixed(2));
    return `${readable.toFixed(2)}°`;
  }

  function tableRows(where, rows) {
    const fragment = document.createDocumentFragment();
    for (const [name, label, ...values] of rows) {
      const row = document.createElement('tr');
      row.dataset.method = name;
      const heading = document.createElement('th');
      heading.scope = 'row';
      heading.textContent = label;
      row.append(heading);
      for (const value of values) {
        const field = document.createElement('td');
        field.textContent = degrees(value);
        row.append(field);
      }
      fragment.append(row);
    }
    where.replaceChildren(fragment);
  }

  function plot() {
    if (!forecast) return;
    const which = Number(finger.value);
    const times = readings.map(row => row[which]);
    const change = forecast.change_in_angle_degrees[chartMethod.value][0][which];
    const last = times.at(-1);
    const later = last + change;
    const size = canvas.getBoundingClientRect();
    if (!size.width || !size.height) return;
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = Math.round(size.width * pixelRatio);
    canvas.height = Math.round(size.height * pixelRatio);
    const ctx = canvas.getContext('2d');
    ctx.scale(pixelRatio, pixelRatio);
    const min = Math.min(...times, later);
    const max = Math.max(...times, later);
    const span = Math.max(12, max - min);
    const low = min - span * .12;
    const high = max + span * .12;
    const x = ms => 42 + (ms + 360) / 680 * (size.width - 60);
    const y = deg => size.height - 30 - (deg - low) / (high - low) * (size.height - 52);
    ctx.font = '12px system-ui, sans-serif';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#c3cdd0';
    ctx.strokeStyle = '#405054';
    for (const value of [low, (low + high) / 2, high]) {
      ctx.beginPath();
      ctx.moveTo(x(-360), y(value));
      ctx.lineTo(x(320), y(value));
      ctx.stroke();
      ctx.fillText(`${Math.round(value)}°`, 4, y(value) + 4);
    }
    const timeY = size.height - 8;
    ctx.fillText('−360 ms', x(-360), timeY);
    ctx.textAlign = 'center';
    ctx.fillText('Last reading', x(0), timeY);
    ctx.textAlign = 'right';
    ctx.fillText('+320 ms', x(320), timeY);
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#9edbc3';
    times.forEach((value, i) => {
      const location = [x((i - 9) * 40), y(value)];
      if (i === 0) ctx.moveTo(...location);
      else ctx.lineTo(...location);
    });
    ctx.stroke();
    ctx.beginPath();
    ctx.strokeStyle = '#ffc887';
    ctx.setLineDash([5, 4]);
    ctx.moveTo(x(0), y(last));
    ctx.lineTo(x(320), y(later));
    ctx.stroke();
    ctx.fillStyle = '#ffc887';
    ctx.beginPath();
    ctx.arc(x(320), y(later), 4, 0, Math.PI * 2);
    ctx.fill();
    byId('chart-caption').textContent = `${model.finger_order[which]}. Last reading ${degrees(last)}. Forecast ${degrees(later)}.`;
  }

  function render() {
    const index = Number(finger.value);
    const hasEcho = readings[0].length === 20;
    useEcho.disabled = !hasEcho;
    byId('ultrasound-help').textContent = hasEcho
      ? 'Turn on ultrasound to compare using it by itself and with the earlier angles.'
      : 'This history contains angle readings. Add sixteen ultrasound values per row to see the other forecasts.';
    forecast = model.forecast(hasEcho && useEcho.checked ? readings : readings.map(row => row.slice(0, 4)));
    const keys = Object.keys(forecast.change_in_angle_degrees);
    const previous = chartMethod.value;
    chartMethod.replaceChildren();
    for (const id of keys) {
      const option = document.createElement('option');
      option.value = id;
      option.textContent = labels[id];
      chartMethod.append(option);
    }
    chartMethod.value = keys.includes(previous) ? previous : 'angle_ridge';
    const current = readings.at(-1)[index];
    tableRows(byId('predictions'), keys.map(id => {
      const delta = forecast.change_in_angle_degrees[id][0][index];
      return [id, labels[id], delta, current + delta];
    }));
    const results = study.equal_person_mae_degrees;
    byId('recorded-finger').textContent = `${model.finger_order[index]} finger. Change Finger above to see the other results.`;
    tableRows(byId('recorded-errors'), ['ridge', 'recurrent'].map((name, i) => [name,
      i === 0 ? 'Linear' : 'Recurrent', results.absolute['angle_' + name][index],
      results.absolute['joint_' + name][index], results.relative['joint_' + name][index],
    ]));
    byId('example-editor').hidden = !originalExample;
    slider.value = current;
    byId('angle-value').textContent = degrees(current);
    plot();
  }

  function reset() {
    fileRequest++;
    input.value = '';
    readings = study.example.history.map(row => [...row]);
    originalExample = true;
    byId('source').textContent = 'Invented example';
    useEcho.checked = false;
    status('');
    render();
  }

  input.addEventListener('change', async () => {
    const file = input.files[0];
    if (!file) return;
    const version = ++fileRequest;
    try {
      const {history} = JSON.parse(await file.text());
      if (version !== fileRequest) return;
      if (!Array.isArray(history) || history.length !== 10 || !Array.isArray(history[0]) || Array.isArray(history[0][0])) {
        throw new Error('Supply one history with ten rows.');
      }
      model.forecast(history);
      readings = history;
      originalExample = false;
      byId('source').textContent = file.name;
      useEcho.checked = false;
      status('Forecast updated.');
      render();
    } catch (error) {
      if (version !== fileRequest) return;
      input.value = '';
      const detail = error instanceof SyntaxError ? 'Check the JSON syntax.' : error.message;
      status(`The previous history is still shown. ${detail}`, true);
    }
  });
  finger.addEventListener('change', render);
  useEcho.addEventListener('change', render);
  chartMethod.addEventListener('change', plot);
  slider.addEventListener('input', () => {
    readings.at(-1)[Number(finger.value)] = Number(slider.value);
    render();
  });
  byId('reset').addEventListener('click', reset);
  new ResizeObserver(plot).observe(canvas);
  reset();
})();
