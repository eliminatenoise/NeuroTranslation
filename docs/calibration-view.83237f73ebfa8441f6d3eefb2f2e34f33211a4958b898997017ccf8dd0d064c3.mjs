const methodCells = {
  'calibration-palm-fixed': 'time_palm_frozen',
  'calibration-palm-adapted': 'time_palm_ridge',
  'calibration-eeg-fixed': 'time_palm_eeg_frozen',
  'calibration-eeg-adapted': 'time_palm_eeg_ridge'
};

const countText = ({eligible, released, positions}) =>
  `${eligible.toLocaleString('en-US')} of ${released.toLocaleString('en-US')} trials · ${positions.toLocaleString('en-US')} positions`;

function validRow(row) {
  if (!row) return false;
  const counts = [row.calibration, row.evaluation];
  return counts.every(count => count && [count.eligible, count.released, count.positions].every(Number.isSafeInteger)
    && count.released >= count.eligible && count.eligible > 0 && count.positions === count.eligible * 9)
    && Number.isSafeInteger(row.clockExclusions) && row.clockExclusions >= 0
    && row.clockExclusions === row.evaluation.released - row.evaluation.eligible
    && Object.values(methodCells).every(method => Number.isFinite(row.rmseMm?.[method]) && row.rmseMm[method] >= 0)
    && row.eegCalibrationTrials
    && ['lower', 'higher', 'tied'].every(direction => Number.isSafeInteger(row.eegCalibrationTrials[direction]) && row.eegCalibrationTrials[direction] >= 0)
    && row.eegCalibrationTrials.lower + row.eegCalibrationTrials.higher + row.eegCalibrationTrials.tied === row.evaluation.eligible;
}

function outcomeText({rmseMm, eegCalibrationTrials}, eligible) {
  const {lower, higher, tied} = eegCalibrationTrials;
  const delta = rmseMm.time_palm_eeg_ridge - rmseMm.time_palm_ridge;
  const trial = count => count === 1 ? 'trial' : 'trials';
  const wins = `Calibrating the EEG model lowered error on ${lower} of ${eligible} R2 trials.`;
  const losses = higher ? ` The fixed model did better on ${higher} ${trial(higher)}.` : '';
  const ties = tied ? ` The models tied on ${tied} ${trial(tied)}.` : '';
  const effect = delta === 0
    ? ' After calibration, the two input sets gave the same error.'
    : ` Adding EEG after calibration ${delta > 0 ? 'raised' : 'lowered'} RMSE by ${Math.abs(delta).toFixed(4)} mm.`;
  return wins + losses + ties + effect;
}

export async function showCalibrationStudy() {
  const byId = id => document.getElementById(id);
  const status = byId('calibration-status');
  try {
    const response = await fetch('./calibration-summary.83237f73ebfa8441f6d3eefb2f2e34f33211a4958b898997017ccf8dd0d064c3.json');
    if (!response.ok) throw new Error('Archived results unavailable');
    const study = await response.json();
    const people = Object.entries(study.participants ?? {});
    const overall = 'all';
    const rows = new Map([[overall, study.equalPerson], ...people]);
    if (study.schemaVersion !== 1 || people.length === 0
      || people.some(([person]) => !/^sub-\d+$/.test(person))
      || ![...rows.values()].every(validRow)) {
      throw new Error('Invalid archived results');
    }
    const selector = byId('calibration-participant');
    selector.replaceChildren(
      new Option(`All ${people.length} · equal weight`, overall),
      ...people.map(([person]) => new Option(person, person))
    );
    const showSelection = () => {
      const selection = rows.has(selector.value) ? selector.value : overall;
      selector.value = selection;
      const row = rows.get(selection);
      const excluded = byId('calibration-exclusion');
      const weighting = byId('calibration-weighting');
      const excludedPeople = people.filter(([, person]) => person.clockExclusions > 0).map(([id]) => id);
      weighting.hidden = selection !== overall;
      byId('calibration-r1').textContent = countText(row.calibration);
      byId('calibration-r2').textContent = countText(row.evaluation);
      excluded.hidden = row.clockExclusions === 0;
      const source = selection === overall ? excludedPeople.join(', ') : selection;
      const noun = row.clockExclusions === 1 ? 'trial' : 'trials';
      excluded.textContent = `The study excluded ${row.clockExclusions} R2 ${noun} for ${source} because the archived clock fell outside the allowed tolerance.`;
      for (const [id, method] of Object.entries(methodCells)) byId(id).textContent = row.rmseMm[method].toFixed(3);
      byId('calibration-outcome').textContent = outcomeText(row, row.evaluation.eligible);
    };
    showSelection();
    selector.addEventListener('change', showSelection);
    status.hidden = true;
    byId('calibration-results').hidden = false;
  } catch {
    status.textContent = 'Archived calibration results could not be loaded. The linked study includes the results table.';
  }
}
