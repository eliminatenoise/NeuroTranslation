'use strict';

const methods = {
  physical: 'Physical reference',
  compact: 'Compact model',
  compact_blended: 'Compact blend',
  research: 'Research model',
  research_blended: 'Research blend'
};

const outcomes = {
  heel_error_mm: {
    title: 'Heel displacement error (mm)',
    definition: 'The camera tracked a marker on the shoe. This error measures how far its predicted movement in three dimensions missed its measured movement.',
    digits: 3
  },
  force_impulse_error_ns: {
    title: 'Vertical force impulse error (N·s)',
    definition: 'Absolute difference between predicted and measured vertical impulse on a foot. One newton-second is one newton of force sustained for one second.',
    digits: 3
  },
  new_load_brier: {
    title: 'Squared load-start probability error',
    definition: 'A new period of loading under the foot counts as 1. A confirmed window with no new start counts as 0. The score squares the difference between that outcome and the forecast probability.',
    digits: 5
  }
};

const byId = id => document.getElementById(id);
const number = (value, digits) => Math.abs(value).toFixed(digits);
function signed(value, digits) {
  const magnitude = number(value, digits);
  if (Number(magnitude) === 0) return magnitude;
  return (value < 0 ? '−' : '+') + magnitude;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function trace(row, extent) {
  const bounds = row.interval;
  const at = value => 50 + 47 * value / extent;
  const line = element('span', undefined, 'trace');
  line.setAttribute('aria-hidden', 'true');
  line.style.setProperty('--start', at(bounds[0]) + '%');
  line.style.setProperty('--width', (at(bounds[1]) - at(bounds[0])) + '%');
  line.style.setProperty('--estimate', at(row.difference) + '%');
  return line;
}
function render() {
  const encoding = byId('encoding');
  const side = byId('side');
  const metric = document.querySelector('input[name="metric"]:checked').value;
  const group = walkingResults[encoding.value][side.value];
  const scores = group[metric];
  const outcome = outcomes[metric];
  const selection = encoding.selectedOptions[0].textContent + ' · ' + side.selectedOptions[0].textContent;
  byId('outcome').textContent = outcome.title;
  byId('definition').textContent = outcome.definition;
  const starts = metric === 'new_load_brier' ? ' · ' + group.distinctStarts + ' distinct confirmed starts' : '';
  byId('support').textContent = scores.footForecasts.toLocaleString('en-US') + ' scored foot forecasts · ' + scores.walkers + ' walkers' + starts;
  byId('selection').textContent = selection;
  byId('announcement').textContent = selection + '. ' + outcome.title + '. ' + byId('support').textContent;
  const differences = scores.methods.filter(row => row.interval);
  const extent = Math.max(...differences.flatMap(row => row.interval.map(Math.abs)));
  const rows = [];
  for (const row of scores.methods) {
    const tr = document.createElement('tr');
    const name = element('th', methods[row.method]);
    name.scope = 'row';
    const mean = element('td', number(row.error, outcome.digits));
    const diff = document.createElement('td');
    if (row.interval) {
      const interval = row.interval.map(value => signed(value, outcome.digits)).join(' to ');
      diff.append(
        element('strong', signed(row.difference, outcome.digits)),
        element('span', interval, 'note'),
        trace(row, extent),
        element('span', row.lower + ' of ' + scores.walkers + ' walkers had lower error', 'note')
      );
    } else {
      diff.textContent = 'Reference';
    }
    tr.append(name, mean, diff);
    rows.push(tr);
  }
  byId('values').replaceChildren(...rows);
  byId('scores').hidden = false;
}

for (const input of document.querySelectorAll('select, input[name="metric"]')) {
  input.addEventListener('change', render);
}
render();
