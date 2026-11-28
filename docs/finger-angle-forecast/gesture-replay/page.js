(() => {
  'use strict';

  const el = id => document.getElementById(id);
  const study = globalThis.FingerGestureStudy;
  const replayModel = globalThis.FingerGestureReplay;
  const trained = globalThis.NeuroTranslateGestureModels;
  const echo = el('echo');
  const finger = el('finger');
  const method = el('chart-method');
  const file = el('history-file');
  const canvas = el('chart');
  const format = new Intl.NumberFormat('en-US');
  const choice = 'adaptive_replay_or_hold';
  const replay = 'past_trajectory_replay';
  let active;
  let results;
  let readToken = 0;

  function status(text, error = false) {
    el('input-status').textContent = text;
    el('input-status').classList.toggle('error', error);
  }

  if (!study || !replayModel || !trained) {
    status('A model file could not open. Extract the complete download and open the page again.', true);
    return;
  }

  function inventedHistory(gesture, speed) {
    const period = { Slow: 1.85, Medium: 1.30, Fast: 0.90 }[speed];
    const base = gesture === 'IndPinch' ? [18, 12, 10, 9] : [21, 18, 16, 15];
    const amplitude = gesture === 'IndPinch' ? [49, 13, 6, 4] : [22, 39, 45, 43];
    const rounded = value => Math.round(value * 10000) / 10000;
    return Array.from({ length: 101 }, (_, frame) => {
      const t = frame / 25;
      const angles = base.map((start, i) => {
        const phase = (2 * Math.PI * t) / period + 0.31 - i * 0.12;
        return rounded(start + amplitude[i] * (1 - Math.cos(phase)) / 2 + 1.3 * Math.sin(0.7 * t + i));
      });
      const tiles = Array.from({ length: 16 }, (_, i) =>
        rounded(3.65 + 0.023 * i + angles[i % 4] * 0.0025 + 0.06 * Math.sin(t * 2.1 + i * 0.5)));
      return angles.concat(tiles);
    });
  }

  function evaluate(rows, includeEcho) {
    const angles = rows.map(row => row.slice(0, 4));
    const match = replayModel.forecastFromHistory(angles);
    const fitted = trained.forecast(includeEcho ? rows : angles);
    return {
      match,
      values: { zero_change: match.hold, [replay]: match.replay, [choice]: match.adaptive, ...fitted }
    };
  }

  function number(value) {
    return (Math.abs(value) >= 1e6 ? value.toExponential(2) : Number(value.toFixed(2)).toFixed(2)) + '°';
  }

  function output(id, value) {
    const item = el(id);
    item.value = number(value);
    item.dataset.degrees = String(value);
  }

  function options(keys, previous) {
    method.replaceChildren(...keys.map(key => new Option(study.methods[key], key)));
    method.value = keys.includes(previous) ? previous : choice;
  }

  function showForecast() {
    const axis = Number(finger.value);
    const key = method.value;
    const current = active.rows.at(-1)[axis];
    const later = results.values[key][axis];
    output('now', current);
    output('later', later);
    output('change', later - current);
    const usesMatch = key === replay || (key === choice && results.match.usesReplay[axis]);
    el('match-key').hidden = !usesMatch;
    if (usesMatch) {
      const delay = results.match.delayFrames[axis];
      const explanation = key === choice ? 'The rule selected replay for this finger. ' : '';
      el('chart-note').textContent = explanation + 'The ten marked readings most closely match the last ten angles and their changes. ' +
        'The earlier sequence ends ' + (delay * 40) + ' ms before the last reading. Its angle eight frames later supplies the forecast.';
    } else if (key === choice) {
      el('chart-note').textContent = 'The rule selected hold for this finger. It compared replay and hold on nine earlier forecasts with known outcomes.';
    } else if (key === 'zero_change') {
      el('chart-note').textContent = 'Holding the last angle gives a forecast of zero change.';
    } else if (key === 'past_angle_trend') {
      el('chart-note').textContent = 'The trend extends a straight line fitted to the last five readings.';
    } else {
      el('chart-note').textContent = 'The fitted model estimates the change in angle. The forecast adds that change to the last reading.';
    }
    draw();
  }

  function draw() {
    if (!active || !results) return;
    const { width, height } = canvas.getBoundingClientRect();
    if (!width || !height) return;
    const scale = window.devicePixelRatio || 1;
    const pixels = [Math.round(width * scale), Math.round(height * scale)];
    if (canvas.width !== pixels[0] || canvas.height !== pixels[1]) {
      canvas.width = pixels[0];
      canvas.height = pixels[1];
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const axis = Number(finger.value);
    const angles = active.rows.map(row => row[axis]);
    const prediction = results.values[method.value][axis];
    const smallest = Math.min(...angles, prediction);
    const largest = Math.max(...angles, prediction);
    const padding = Math.max(2, (largest - smallest) * .12, Math.abs(largest) * Number.EPSILON * 16);
    const low = smallest - padding;
    const high = largest + padding;
    const label = value => Math.abs(value) >= 10000 ? value.toExponential(0) + '°' : Math.round(value) + '°';
    ctx.font = '12px system-ui, sans-serif';
    const left = Math.max(39, ctx.measureText(label(low)).width + 10, ctx.measureText(label(high)).width + 10);
    const right = width - 12;
    const bottom = height - 40;
    const x = frame => left + (right - left) * frame / 108;
    const y = angle => bottom - (bottom - 12) * (angle - low) / (high - low);
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.strokeStyle = '#3c4b50';
    ctx.fillStyle = '#c1c9cb';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 3; i++) {
      const value = low + (high - low) * i / 3;
      ctx.beginPath();
      ctx.moveTo(left, y(value)); ctx.lineTo(right, y(value)); ctx.stroke();
      ctx.fillText(label(value), left - 5, y(value) + 4);
    }
    ctx.setLineDash([3, 4]);
    ctx.beginPath(); ctx.moveTo(x(100), 12); ctx.lineTo(x(100), bottom); ctx.stroke();
    ctx.setLineDash([]);
    ctx.textAlign = 'left'; ctx.fillText('−4 s', x(0), bottom + 18);
    ctx.textAlign = 'center'; ctx.fillText('−2 s', x(50), bottom + 18);
    ctx.textAlign = 'right'; ctx.fillText('Now', x(100), bottom + 18);
    ctx.fillText('+0.32 s', right, bottom + 34);
    ctx.lineWidth = 2.2;
    ctx.strokeStyle = '#9edbc3';
    ctx.beginPath();
    angles.forEach((angle, i) => i === 0 ? ctx.moveTo(x(i), y(angle)) : ctx.lineTo(x(i), y(angle)));
    ctx.stroke();
    if (!el('match-key').hidden) {
      const end = 100 - results.match.delayFrames[axis];
      ctx.strokeStyle = '#c3adff'; ctx.lineWidth = 1.6;
      for (let i = end - 9; i <= end; i++) {
        ctx.beginPath(); ctx.arc(x(i), y(angles[i]), 2.8, 0, 2 * Math.PI); ctx.stroke();
      }
    }
    const px = x(108), py = y(prediction);
    ctx.fillStyle = '#ffc887';
    ctx.beginPath(); ctx.moveTo(px, py - 5); ctx.lineTo(px + 5, py);
    ctx.lineTo(px, py + 5); ctx.lineTo(px - 5, py); ctx.closePath(); ctx.fill();
  }

  function activate(next, includeEcho, estimates) {
    const earlierMethod = method.value;
    active = next;
    results = estimates;
    el('example-controls').disabled = !next.invented;
    echo.disabled = next.rows[0].length === 4;
    echo.checked = includeEcho;
    el('source').textContent = next.invented ? 'Invented example' : 'Local file · ' + next.fileName;
    el('echo-note').textContent = next.invented
      ? 'The example includes invented measurements from sixteen parts of an ultrasound image.'
      : (echo.disabled ? 'This file contains finger angles only.' : 'The last sixteen numbers in each row supply the ultrasound measurements.');
    options(Object.keys(study.methods).filter(k => Object.hasOwn(results.values, k)), earlierMethod);
    showForecast();
  }

  function resetExample(restore) {
    readToken++;
    if (restore) {
      el('example-gesture').value = 'IndPinch';
      el('example-speed').value = 'Medium';
    }
    file.value = '';
    const rows = inventedHistory(el('example-gesture').value, el('example-speed').value);
    const includeEcho = restore ? false : echo.checked;
    activate({ rows, invented: true }, includeEcho, evaluate(rows, includeEcho));
    status(restore ? 'Invented index pinch restored.' : '');
  }

  function loadError(error) {
    status('Could not use the file. ' + error.message + ' The previous movement is still shown.', true);
  }

  file.addEventListener('change', async () => {
    const selected = file.files[0];
    if (!selected) return;
    const token = ++readToken;
    status('Reading ' + selected.name + '…');
    try {
      if (selected.size > 4 * 1024 * 1024) throw new Error('Choose a JSON file under 4 MiB.');
      const raw = await selected.text();
      if (token !== readToken) return;
      let parsed;
      try { parsed = JSON.parse(raw); }
      catch { throw new Error('The file is not valid JSON.'); }
      const rows = parsed?.history;
      if (!Array.isArray(rows) || rows.length !== 101) throw new Error('Provide a history array with 101 rows.');
      const columns = rows[0]?.length;
      if (![4, 20].includes(columns)) throw new Error('Use four angles, or four angles followed by sixteen ultrasound values.');
      if (!rows.every(row => Array.isArray(row) && row.length === columns && row.every(Number.isFinite))) {
        throw new Error('Use the same number of finite numeric values in every row.');
      }
      const includeEcho = columns === 20;
      const estimates = evaluate(rows, includeEcho);
      activate({ rows, invented: false, fileName: selected.name }, includeEcho, estimates);
      status('Loaded 101 readings from the selected file.');
    } catch (error) {
      if (token === readToken) loadError(error);
    } finally {
      if (token === readToken) file.value = '';
    }
  });

  function showStudy() {
    const gesture = el('study-gesture').value, speed = el('study-speed').value;
    const reported = el('study-finger').value;
    const group = study.groups[gesture][speed];
    el('coverage').textContent = study.gestures[gesture] + ' · ' + (speed === 'All' ? 'All speeds' : speed) + ' · ' +
      group.people + ' people · ' + group.recordings + ' recordings · ' + format.format(group.forecast_times_per_finger) + ' forecast times per finger.';
    el('score-caption').textContent = (reported === 'All' ? 'Four-finger average' : study.finger_order[Number(reported)] + ' finger') +
      '. Mean absolute error in degrees. Smaller is better.';
    const body = el('recorded-errors');
    const rows = document.createDocumentFragment();
    for (const [key, title] of Object.entries(study.methods)) {
      const scores = group.mean_absolute_error_degrees[key];
      const value = reported === 'All' ? scores.four_finger_mean : scores.by_finger[Number(reported)];
      const row = document.createElement('tr');
      row.dataset.method = key;
      const heading = document.createElement('th'); heading.scope = 'row'; heading.textContent = title;
      const cell = document.createElement('td'); cell.textContent = number(value); cell.dataset.degrees = String(value);
      row.append(heading, cell); rows.append(row);
    }
    body.replaceChildren(rows);
  }

  for (const id of ['example-gesture', 'example-speed']) el(id).addEventListener('change', () => resetExample(false));
  el('reset').addEventListener('click', () => resetExample(true));
  echo.addEventListener('change', () => {
    try {
      const includeEcho = echo.checked;
      const calculated = evaluate(active.rows, includeEcho);
      activate(active, includeEcho, calculated);
    } catch (error) {
      echo.checked = !echo.checked;
      status('Could not change the inputs. ' + error.message, true);
    }
  });
  for (const item of [finger, method]) item.addEventListener('change', showForecast);
  for (const id of ['study-gesture', 'study-speed', 'study-finger']) el(id).addEventListener('change', showStudy);
  if (window.ResizeObserver) new ResizeObserver(draw).observe(canvas);
  else window.addEventListener('resize', draw);
  resetExample(true);
  status('');
  showStudy();
})();
