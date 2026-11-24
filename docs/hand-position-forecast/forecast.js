'use strict';

const names = {
  stay_put: 'Stay put',
  constant_velocity: 'Constant velocity',
  constant_acceleration: 'Constant acceleration',
  original: 'Original neural',
  published_blend: 'Published neural blend',
  equal_blend: 'Equal blend',
};
const colours = {
  stay_put: '#40534c',
  constant_velocity: '#164f99',
  constant_acceleration: '#8e4b09',
  published_blend: '#70498b',
  equal_blend: '#167352',
};
const label = new Intl.NumberFormat('en', {maximumFractionDigits: 2});
const error = new Intl.NumberFormat('en', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const day = document.querySelector('#day');
const metric = document.querySelector('#metric');
const group = document.querySelector('#group');
const form = document.querySelector('#example');
const canvas = document.querySelector('#path');
const context = canvas.getContext('2d');
const inputs = ['x80', 'y80', 'x40', 'y40', 'x0', 'y0', 'nx', 'ny']
  .map(id => document.getElementById(id));
let plotted;

function heading(text) {
  const cell = document.createElement('th');
  cell.scope = 'row';
  cell.textContent = text;
  return cell;
}

function cell(text) {
  const item = document.createElement('td');
  item.textContent = text;
  return item;
}

function renderRecorded() {
  const support = document.querySelector('#support');
  const effect = document.querySelector('#effect');
  const body = document.querySelector('#recorded-table tbody');
  const recording = window.handPositionStudy?.recordings[day.value];
  const subset = group.value === 'overall' ? recording?.overall : recording?.strata[group.value];
  if (!subset?.error_mm) {
    support.textContent = 'No scores are available for this selection.';
    effect.textContent = '';
    body.replaceChildren();
    return;
  }
  const score = Number(metric.value);
  const values = Object.keys(names).map(key => [key, subset.error_mm[key][score]]);
  const best = Math.min(...values.map(([, value]) => value));
  support.textContent = `${label.format(subset.rows)} forecasts from ${label.format(subset.trials)} trials`;
  body.replaceChildren(...values.map(([key, value]) => {
    const row = document.createElement('tr');
    row.dataset.method = key;
    const scoreCell = cell(error.format(value));
    if (value === best) {
      row.classList.add('best');
      scoreCell.setAttribute('aria-label', `${error.format(value)} millimetres, lowest error`);
    }
    row.append(heading(names[key]), scoreCell);
    return row;
  }));
  const difference = subset.paired_gain_mm.equal_blend_over_constant_velocity;
  const gain = difference.mean[score];
  const [lo, hi] = difference.paired_95[score];
  const direction = gain >= 0 ? 'lower' : 'higher';
  effect.textContent = `The equal blend averaged ${error.format(Math.abs(gain))} mm ${direction} error than constant velocity. The paired 95% interval for the reduction was ${error.format(lo)} to ${error.format(hi)} mm. Negative values mean the blend had higher error.`;
}

function calculateExample(values) {
  const [x80, y80, x40, y40, x0, y0, nx, ny] = values;
  const past = [[x80, y80], [x40, y40], [x0, y0]];
  const current = past[2];
  const recent = [x0 - x40, y0 - y40];
  const older = [x40 - x80, y40 - y80];
  const ratio = 100 / 40;
  const velocity = recent.map(value => ratio * value);
  const acceleration = velocity.map((value, i) => value + .5 * ratio * (ratio + 1) * (recent[i] - older[i]));
  const neural = [nx, ny];
  const blend = velocity.map((value, i) => (value + neural[i]) / 2);
  const endpoint = delta => current.map((start, i) => start + delta[i]);
  return {
    past,
    endpoints: {
      stay_put: current,
      constant_velocity: endpoint(velocity),
      constant_acceleration: endpoint(acceleration),
      published_blend: endpoint(neural),
      equal_blend: endpoint(blend),
    },
  };
}

function draw() {
  if (!context) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const density = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * density);
  canvas.height = Math.round(height * density);
  context.setTransform(density, 0, 0, density, 0, 0);
  if (!plotted || width < 130 || height < 90) return;
  const all = [...plotted.past, ...Object.values(plotted.endpoints)];
  const xValues = all.map(point => point[0]);
  const yValues = all.map(point => point[1]);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const middleX = (minX + maxX) / 2;
  const middleY = (minY + maxY) / 2;
  const scale = Math.min((width - 115) / Math.max(1, maxX - minX), (height - 76) / Math.max(1, maxY - minY));
  const centerX = (61 + width - 20) / 2;
  const centerY = (22 + height - 47) / 2;
  const plot = ([x, y]) => [centerX + (x - middleX) * scale, centerY - (y - middleY) * scale];
  const stroke = (points, colour, dash = []) => {
    context.beginPath();
    context.setLineDash(dash);
    context.strokeStyle = colour;
    points.forEach(([x, y], index) => index ? context.lineTo(x, y) : context.moveTo(x, y));
    context.stroke();
    context.setLineDash([]);
  };
  const tick = value => Math.abs(value) >= 10000 ? value.toExponential(1) : label.format(value);
  context.fillStyle = '#465a54';
  context.font = '12px system-ui, sans-serif';
  const steps = width < 400 ? 2 : 4;
  for (let i = 0; i <= steps; i++) {
    const x = 56 + i * (width - 77) / steps;
    const y = 24 + i * (height - 70) / steps;
    stroke([[x, 24], [x, height - 46]], '#dce6e0');
    stroke([[56, y], [width - 21, y]], '#dce6e0');
    context.textAlign = 'center';
    context.fillText(tick(middleX + (x - centerX) / scale), x, height - 29);
    context.textAlign = 'right';
    context.fillText(tick(middleY - (y - centerY) / scale), 50, y + 4);
  }
  context.textAlign = 'left';
  context.fillText('Y (mm)', 6, 15);
  context.textAlign = 'center';
  context.fillText('X (mm)', centerX, height - 9);
  context.lineWidth = 2.5;
  stroke(plotted.past.map(plot), colours.stay_put);
  context.fillStyle = colours.stay_put;
  for (const point of plotted.past.slice(0, -1)) {
    context.beginPath();
    context.arc(...plot(point), 3.5, 0, Math.PI * 2);
    context.fill();
  }
  const current = plot(plotted.past[2]);
  for (const [method, point] of Object.entries(plotted.endpoints)) {
    const xy = plot(point);
    if (method !== 'stay_put') stroke([current, xy], colours[method], [4, 3]);
    context.beginPath();
    context.fillStyle = colours[method];
    context.arc(...xy, method === 'equal_blend' ? 6 : 4, 0, Math.PI * 2);
    context.fill();
  }
}

function renderExample() {
  const result = document.querySelector('#example-result');
  const body = document.querySelector('#example-table tbody');
  if (inputs.some(input => !input.validity.valid || !Number.isFinite(input.valueAsNumber))) {
    plotted = null;
    body.replaceChildren();
    result.textContent = 'Enter a value from −1,000,000 to 1,000,000 mm in each box.';
    draw();
    return;
  }
  plotted = calculateExample(inputs.map(input => input.valueAsNumber));
  const [x, y] = plotted.endpoints.equal_blend;
  result.textContent = `The equal blend ends at X ${label.format(x)} mm and Y ${label.format(y)} mm.`;
  body.replaceChildren(...Object.entries(plotted.endpoints).map(([method, point]) => {
    const row = document.createElement('tr');
    row.dataset.method = method;
    const title = heading(method === 'published_blend' ? 'Example neural forecast' : names[method]);
    const marker = document.createElement('span');
    marker.className = 'marker';
    marker.style.backgroundColor = colours[method];
    marker.setAttribute('aria-hidden', 'true');
    title.prepend(marker);
    row.append(title, ...point.map(value => cell(label.format(value))));
    return row;
  }));
  draw();
}

for (const filter of [day, metric, group]) filter.addEventListener('change', renderRecorded);
form.addEventListener('input', renderExample);
form.addEventListener('submit', event => { event.preventDefault(); renderExample(); });
document.querySelector('#example-reset').addEventListener('click', () => { form.reset(); renderExample(); });
if ('ResizeObserver' in window) new ResizeObserver(draw).observe(canvas);
else window.addEventListener('resize', draw);
renderRecorded();
renderExample();
