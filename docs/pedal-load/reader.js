/* Reader interactions and plots. The entire calculation runs on the device. */
(() => {
  'use strict';
  const byId = (id) => document.getElementById(id);
  const fields = ['load', 'emg', 'donor'];
  const labels = {
    load: 'pedal load',
    emg: 'original muscle signal',
    donor: 'alternate muscle signal',
  };
  const descriptions = {
    full: 'The fitted Transformer reads load, muscle voltage and pedal setting together.',
    load: 'This Transformer was trained with only the pedal load.',
    load_condition: 'This Transformer was trained with pedal load and the fixed pedal setting.',
    emg_condition:
      'This fit predicts a change from muscle voltage and setting alone. The chart adds the change to the last pedal reading to place the dot.',
    wrong:
      'Retrospective control. The full Transformer receives the alternate muscle signal alongside the original load and pedal setting.',
    ridge_load: 'A fitted linear rule combines the recent load measurements.',
    ridge_condition:
      'A fitted linear rule combines the recent load measurements with the fixed pedal setting.',
    zero: 'Hold the last reading. The predicted change is always zero.',
    continue: 'Repeat the change in load over the preceding 100 sample intervals.',
    typical: 'Use the median load change in training, balanced across people and settings.',
    typical_condition:
      'Use the median training change for the chosen setting, balanced across people.',
  };
  const compact = (value) => {
    if (value !== 0 && (Math.abs(value) >= 1e4 || Math.abs(value) < 1e-4))
      return value.toExponential(2).replace('-', '−');
    const rounded = Number(value.toFixed(4));
    return (rounded === 0 ? '0.0000' : rounded.toFixed(4)).replace('-', '−');
  };
  const signed = (value) =>
    (value > 0 && Number(compact(value).replace('−', '-')) !== 0 ? '+' : '') + compact(value);
  let original,
    pending = false;
  function svgNode(tag, attrs, text) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [name, val] of Object.entries(attrs)) el.setAttribute(name, val);
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function plot(id, trace, endpoint) {
    const svg = byId(id);
    const width = Math.max(242, Math.floor(svg.getBoundingClientRect().width));
    const height = endpoint === null ? 115 : 169;
    const left = 59,
      right = width - 23,
      top = 12,
      bottom = height - 27;
    const x = (sample) => left + ((sample + 200) * (right - left)) / 300;
    let low = Math.min(...trace, endpoint ?? Infinity),
      high = Math.max(...trace, endpoint ?? -Infinity);
    const margin = high === low ? Math.max(0.03, Math.abs(low) * 0.03) : (high - low) * 0.085;
    low -= margin;
    high += margin;
    if (!Number.isFinite(high - low))
      throw new RangeError('The chart cannot display this numeric range.');
    const y = (value) => bottom - ((value - low) / (high - low)) * (bottom - top);
    const elems = [];
    elems.push(
      svgNode('rect', {
        x: x(0),
        y: top,
        width: x(100) - x(0),
        height: bottom - top,
        fill: '#f4f3ee',
      }),
    );
    for (const fraction of [0, 0.5, 1]) {
      const level = low + fraction * (high - low),
        row = y(level);
      const shown =
        Math.abs(level) >= 1e4 || (Math.abs(level) > 0 && Math.abs(level) < 0.001)
          ? level.toExponential(1)
          : level.toFixed(2);
      elems.push(
        svgNode('line', { x1: left, x2: right, y1: row, y2: row, stroke: '#d5ddd9' }),
        svgNode('text', { x: left - 5, y: row + 4, 'text-anchor': 'end' }, shown.replace('-', '−')),
      );
    }
    elems.push(
      svgNode('line', {
        x1: x(0),
        x2: x(0),
        y1: top,
        y2: bottom,
        stroke: '#71827d',
        'stroke-dasharray': '3 4',
      }),
    );
    const points = trace.map((v, i) => `${x(i - 200).toFixed(2)},${y(v).toFixed(2)}`).join(' ');
    elems.push(
      svgNode('polyline', {
        points,
        class: 'line',
        stroke: endpoint === null ? '#5b6399' : '#00665e',
        'stroke-width': endpoint === null ? 1.5 : 2.7,
      }),
    );
    if (endpoint !== null)
      elems.push(
        svgNode('circle', {
          cx: x(100),
          cy: y(endpoint),
          r: 5,
          fill: '#b44725',
          stroke: 'white',
          'stroke-width': 1,
        }),
      );
    const ticks = [
      [-200, '−200'],
      [0, 'Cutoff 0'],
      [100, '+100'],
    ];
    if (width > 360) ticks.splice(1, 0, [-100, '−100']);
    for (const [n, label] of ticks)
      elems.push(svgNode('text', { x: x(n), y: height - 7, 'text-anchor': 'middle' }, label));
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.replaceChildren(...elems);
  }
  function clear(message) {
    byId('error').textContent = message;
    for (const id of ['change', 'endpoint']) byId(id).textContent = '—';
    for (const id of ['load-plot', 'signal-plot', 'predictions']) byId(id).replaceChildren();
    byId('signal-note').textContent = '';
  }
  function update() {
    byId('method-note').textContent = descriptions[byId('method').value];
    if (pending) {
      clear('Apply the edited readings to run the forecast.');
      return;
    }
    const gain = byId('gain').valueAsNumber;
    const good = Number.isFinite(gain) && gain >= 0 && gain <= 10;
    byId('gain').setAttribute('aria-invalid', String(!good));
    if (!good) {
      clear('Enter a muscle-signal multiplier from 0 to 10.');
      return;
    }
    const history = {
      load: original.load,
      emg: original.emg.map((v) => v * gain),
      donor: original.donor,
      angle5: Number(byId('angle').value),
    };
    try {
      const values = PedalForecast.predict(PEDAL_WEIGHTS, history);
      const method = byId('method').value,
        change = values[method],
        endpoint = history.load[200] + change;
      if (!Number.isFinite(endpoint))
        throw new RangeError('The endpoint exceeds the available numeric range.');
      byId('error').textContent = '';
      byId('change').textContent = signed(change);
      byId('endpoint').textContent = compact(endpoint);
      plot('load-plot', history.load, endpoint);
      plot('signal-plot', method === 'wrong' ? history.donor : history.emg, null);
      byId('signal-title').textContent =
        method === 'wrong' ? 'Alternate muscle signal' : 'Original muscle signal';
      const note =
        method === 'wrong'
          ? 'The control uses this invented alternate trace.'
          : ['full', 'emg_condition'].includes(method)
            ? 'The selected fit uses this trace.'
            : 'The selected method ignores this trace.';
      byId('signal-note').textContent =
        note + ' Horizontal axes count samples relative to the cutoff.';
      const rows = Array.from(byId('method').options, (option) => {
        const row = document.createElement('tr'),
          name = document.createElement('th'),
          cell = document.createElement('td');
        name.scope = 'row';
        name.textContent = option.dataset.long || option.text;
        cell.textContent = signed(values[option.value]);
        row.append(name, cell);
        return row;
      });
      byId('predictions').replaceChildren(...rows);
    } catch (err) {
      clear(err.message);
    }
  }
  function fillPreset(name) {
    original = pedalExample(name);
    pending = false;
    for (const key of fields) {
      byId(key).value = original[key].join(', ');
      byId(key).removeAttribute('aria-invalid');
    }
    byId('gain').value = '1';
    byId('preset').value = name;
    update();
  }
  const numberPattern = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
  function parse(text, key) {
    const cells = text.trim().split(/\s*,\s*|\s+/);
    if (
      cells.length !== 201 ||
      !cells.every((s) => numberPattern.test(s) && Number.isFinite(Number(s)))
    ) {
      throw new Error(`Enter exactly 201 finite numbers for the ${labels[key]}.`);
    }
    return cells.map(Number);
  }
  byId('preset').addEventListener('change', () => fillPreset(byId('preset').value));
  byId('restore').addEventListener('click', () => fillPreset('rise'));
  for (const key of fields)
    byId(key).addEventListener('input', () => {
      pending = true;
      byId(key).removeAttribute('aria-invalid');
      update();
    });
  byId('apply').addEventListener('click', () => {
    const edited = {};
    for (const key of fields) {
      try {
        edited[key] = parse(byId(key).value, key);
        byId(key).removeAttribute('aria-invalid');
      } catch (err) {
        pending = true;
        byId(key).setAttribute('aria-invalid', 'true');
        clear(err.message);
        byId(key).focus();
        return;
      }
    }
    original = edited;
    pending = false;
    byId('preset').value = 'custom';
    update();
  });
  for (const id of ['angle', 'method']) byId(id).addEventListener('change', update);
  byId('gain').addEventListener('input', update);
  byId('download').hidden = location.protocol === 'file:';
  let lastWidth = 0;
  new ResizeObserver((entries) => {
    const width = Math.round(entries[0].contentRect.width);
    if (width !== lastWidth) {
      lastWidth = width;
      update();
    }
  }).observe(document.querySelector('.readout'));
  fillPreset('rise');
})();
