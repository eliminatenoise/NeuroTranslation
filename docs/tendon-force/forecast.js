'use strict';

function tendonForecast(tendon, values) {
  const model = TENDON_PREDICTORS[tendon];
  if (!Object.hasOwn(TENDON_PREDICTORS, tendon) || values.length !== 10 || !values.every(value => Number.isFinite(value) && value >= 0)) {
    throw new RangeError('Enter ten finite, nonnegative values and select a tendon.');
  }
  const windowRms = Math.sqrt(values.reduce((sum, value) => sum + value ** 2, 0) / values.length);
  if (!Number.isFinite(windowRms)) throw new RangeError('These values are too large to calculate.');

  const normalized = values.map(value => windowRms === 0 ? 0 : value / windowRms);
  function ridge({ centers, scales, coefficients }, sample) {
    const weighted = sample.reduce((sum, value, bin) => sum + ((value - centers[bin]) / scales[bin]) * coefficients[bin + 1], 0);
    return coefficients[0] + weighted;
  }
  const result = { raw: ridge(model.raw, values), scaled: ridge(model.scaled, normalized), median: model.median };
  if (!Object.values(result).every(Number.isFinite)) throw new RangeError('A numerical forecast was unavailable for these values.');
  return result;
}

const example = [0.06, 0.08, 0.13, 0.19, 0.22, 0.17, 0.11, 0.09, 0.12, 0.15];
const notes = {
  LG: 'Uses the signal from the lateral gastrocnemius (LG), one of the muscles that pull on the Achilles tendon.',
  DF: 'Uses the signal from digital flexor IV (DF), the muscle that pulls on the fourth-toe flexor tendon.',
};
const form = document.querySelector('#inputs');
const tendon = document.querySelector('#tendon');
const bins = document.querySelector('#bins');
const status = document.querySelector('#status');
const origin = document.querySelector('#input-origin');
const outputs = Object.fromEntries(['raw', 'scaled', 'median'].map(name => [name, document.querySelector(`#result-${name}`)]));
const numericFormat = new Intl.NumberFormat('en', { minimumFractionDigits: 4, maximumFractionDigits: 4 });

const fields = example.map((_, bin) => {
  const start = (10 - bin) * 20;
  const stop = start - 20;
  const label = document.createElement('label');
  label.htmlFor = `bin-${bin + 1}`;
  label.textContent = `${start}–${stop} ms`;
  const input = document.createElement('input');
  input.id = label.htmlFor;
  input.name = label.htmlFor;
  input.type = 'number';
  input.min = '0';
  input.step = 'any';
  input.inputMode = 'decimal';
  input.required = true;
  input.setAttribute('aria-describedby', 'history-help');
  label.append(input);
  bins.append(label);
  return input;
});

function clearForecast() {
  for (const output of Object.values(outputs)) output.value = '—';
}

function calculate() {
  try {
    const result = tendonForecast(tendon.value, fields.map(field => field.valueAsNumber));
    for (const [name, output] of Object.entries(outputs)) output.value = numericFormat.format(result[name]);
    status.textContent = `Forecasts updated for ${tendon.selectedOptions[0].textContent}.`;
  } catch (error) {
    clearForecast();
    status.textContent = error.message;
  }
}

function loadExample() {
  fields.forEach((field, bin) => { field.value = example[bin]; });
  origin.textContent = 'These are invented values.';
  calculate();
}

function requestCalculation() {
  clearForecast();
  status.textContent = 'Select Calculate to update the forecasts.';
}

form.addEventListener('submit', event => {
  event.preventDefault();
  calculate();
});
tendon.addEventListener('change', () => {
  document.querySelector('#route-note').textContent = notes[tendon.value];
  requestCalculation();
});
bins.addEventListener('input', () => {
  origin.textContent = 'These values include your edits.';
  requestCalculation();
});
document.querySelector('#example').addEventListener('click', loadExample);
loadExample();
