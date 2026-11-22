'use strict';
const byId = id => document.getElementById(id);
function cell(text, tag = 'td') {
  const el = document.createElement(tag);
  el.textContent = text;
  if (tag === 'th') el.scope = 'row';
  return el;
}
const signed = v => (v > 0 ? '+' : '') + v.toFixed(1).replace('-', '−');
function averageForecast(history, useForce) {
  const first = compactWalking.predict(history, useForce, 2731);
  const second = compactWalking.predict(history, useForce, 4119);
  const mean = (left, right) => left.map((value, index) => (value + right[index]) / 2);
  return {
    heel: first.heel.map((side, index) => mean(side, second.heel[index])),
    impulse: mean(first.impulse, second.impulse),
    loadStart: mean(first.loadStart, second.loadStart),
  };
}
function render() {
  const travel = Number(byId('travel').value);
  const load = Number(byId('load').value);
  const forceMode = byId('model').value === 'both';
  const history = exampleHistory(travel, load);
  const choice = byId('seed').value;
  const result = choice === 'average'
    ? averageForecast(history, forceMode)
    : compactWalking.predict(history, forceMode, Number(choice));
  byId('mode-note').textContent = forceMode ?
    'This input uses both heel paths and both foot loads.' :
    'This input uses only heel positions. Changing a load updates the invented history. Both force channels stay marked unavailable to the model.';
  byId('travel-value').value = travel + ' mm';
  byId('load-value').value = load + ' N';
  byId('travel').setAttribute('aria-valuetext', travel + ' millimetres');
  byId('load').setAttribute('aria-valuetext', load + ' newtons');
  const bins = history.heel.map((row, t) => {
    const tr = document.createElement('tr');
    tr.append(cell((t * 20 - 200) + ' to ' + (t * 20 - 180), 'th'),
      cell(row.slice(0, 3).map(signed).join(', ')), cell(row.slice(3).map(signed).join(', ')),
      cell(history.force[t].map(v => v.toFixed(1)).join(' / ')));
    return tr;
  });
  byId('bins').replaceChildren(...bins);
  const vectors = [];
  for (let side = 0; side < 2; side++) {
    const show = (name, value) => {
      document.querySelector('[data-result="' + name + '-' + side + '"]').textContent = value;
    };
    show('heel', Math.hypot(...result.heel[side]).toFixed(1));
    show('impulse', result.impulse[side].toFixed(2) + ' N·s');
    show('load', (100 * result.loadStart[side]).toFixed(1) + '%');
    const tr = document.createElement('tr');
    tr.append(cell(side === 0 ? 'Left' : 'Right', 'th'), ...result.heel[side].map(v => cell(signed(v))));
    vectors.push(tr);
  }
  byId('xyz').replaceChildren(...vectors);
  byId('total-impulse').textContent = (result.impulse[0] + result.impulse[1]).toFixed(2) + ' N·s';
}
for (const id of ['travel', 'load']) byId(id).addEventListener('input', render);
for (const id of ['model', 'seed']) byId(id).addEventListener('change', render);
render();
