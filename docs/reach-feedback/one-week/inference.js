"use strict";
const WeekForecast = (() => {
  function edit(record, column, oldMm, newMm) {
    const unit = column < 6 ? 0.001 : 0.1;
    const history = record.history.map(row => [...row]);
    const future = record.future.map(row => [...row]);
    for (let j = 0; j < 5; j++) history[15 + j][column] += oldMm * unit * (j + 1) / 5;
    for (let j = 0; j < 10; j++) future[j][column] += newMm * unit * (j + 1) / 10;
    return {history, future};
  }
  function movement(history, future) {
    const last = history[19];
    const slope = last.map((v, j) => (v - history[15][j]) / 4);
    const velocity = future.map((_, t) => last.map((v, j) => v + (t + 1) * slope[j]));
    const residual = future[9].map((v, j) => v - velocity[9][j]);
    return {slope, velocity, residual};
  }
  function linearRate(standardized, coefficients) {
    let eta = coefficients[0];
    for (let j = 0; j < standardized.length; j++) eta += standardized[j] * coefficients[j + 1];
    return Math.exp(eta);
  }
  function rates(fit, features) {
    const z = features.map((v, j) => (v - fit.mean[j]) / fit.scale[j]);
    return fit.coefficients.map(row => linearRate(z, row));
  }
  function predict(fit, record, history, future) {
    const {slope, velocity, residual} = movement(history, future);
    const base = [...history[19], ...slope, ...record.countHistory, ...record.cueAtK];
    const earlier = rates(fit.base, base);
    const update = rates(fit.update, [...base, ...residual]);
    const wrong = record.donorResidual ? rates(fit.update, [...base, ...record.donorResidual]) : null;
    return {earlier, update, wrong, velocity, residual};
  }
  function singleContact(model, raw) {
    const z = raw.map((v, j) => Math.max(-8, Math.min(8, (v - model.mean[j]) / model.scale[j])));
    return linearRate(z, model.coefficients);
  }
  function late(fits, record, history, future) {
    const last = history[19];
    const common = [...last, ...last.map((v, j) => v - history[9][j]), ...record.cueLast];
    const motion = [4, 9].flatMap(t => future[t].map((v, j) => v - last[j]));
    const stale = [], update = [], wrong = [];
    for (const contact of fits.contacts) {
      const spikes = record.positiveRecent[String(contact)].map(Math.log1p);
      const x = [...common, ...spikes];
      stale.push(singleContact(fits.stale_position[contact], x));
      update.push(singleContact(fits.measured_update[contact], [...x, ...motion]));
      if (record.donorLateMovement) {
        wrong.push(singleContact(fits.measured_update[contact], [...x, ...record.donorLateMovement]));
      }
    }
    return {earlier: stale, update, wrong: record.donorLateMovement ? wrong : null};
  }
  return {edit, movement, predict, late};
})();
