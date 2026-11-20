"use strict";

function vector(value, length) {
  return Array.isArray(value) && value.length === length && value.every(Number.isFinite);
}

function motionFeatures(cutoff, times, positions) {
  if (!Number.isFinite(cutoff) || !vector(times, 5) || !Array.isArray(positions) ||
      positions.length !== 5 || !positions.every(pair => vector(pair, 2))) {
    throw new RangeError("Five finite camera times and five XY positions are required.");
  }
  const ages = times.map((time, i) => cutoff + (i - 4) * 0.25 - time);
  if (ages.some(age => age < -1e-9 || age > 0.075000001) ||
      times.some((time, i) => i > 0 && time <= times[i - 1])) {
    throw new RangeError("A camera sample is out of order, ahead of its tick or too old.");
  }
  const steps = positions.slice(1).map(([x, y], i) => [x - positions[i][0], y - positions[i][1]]);
  const lengths = steps.map(([dx, dy]) => Math.hypot(dx, dy));
  const speeds = lengths.map((length, i) => length / (times[i + 1] - times[i]));
  const endpointDistance = (i, j) => Math.hypot(
    positions[j][0] - positions[i][0], positions[j][1] - positions[i][1]
  );
  const turns = steps.slice(1).map(([dx, dy], i) => {
    const denom = lengths[i] * lengths[i + 1];
    return denom > 0 ? (steps[i][0] * dx + steps[i][1] * dy) / denom : 0;
  });
  return [...speeds, endpointDistance(2, 4), endpointDistance(0, 4), ...turns, ...ages.slice(1)];
}

function firingFeatures(counts, units) {
  if (!vector(units, 2) || !units.every(n => Number.isInteger(n) && n > 0) ||
      !Array.isArray(counts) || counts.length !== 4 ||
      !counts.every(pair => vector(pair, 2) && pair.every(n => Number.isInteger(n) && n >= 0))) {
    throw new RangeError("Four pairs of whole spike counts and two positive unit counts are required.");
  }
  return counts.flatMap(pair => pair.map((count, r) => Math.log1p(count / (0.25 * units[r]))));
}

function ridgeDistance(fit, features) {
  const length = features.length;
  if (!fit || !Number.isFinite(fit.intercept) || !vector(fit.mean, length) ||
      !vector(fit.scale, length) || !fit.scale.every(x => x > 0) || !vector(fit.coefficient, length)) {
    throw new RangeError("The fitted coefficients do not match these inputs.");
  }
  const weighted = features.reduce((sum, value, i) =>
    sum + (value - fit.mean[i]) / fit.scale[i] * fit.coefficient[i], 0);
  return Math.max(0, weighted + fit.intercept);
}

function forecast(cutoff, times, positions, counts, donorCounts, units, weights) {
  const motion = motionFeatures(cutoff, times, positions);
  const aligned = firingFeatures(counts, units);
  const earlier = firingFeatures(donorCounts, units);
  return {
    motion: ridgeDistance(weights.motion, motion),
    combined: ridgeDistance(weights.combined, [...motion, ...aligned]),
    earlier_trip: ridgeDistance(weights.combined, [...motion, ...earlier]),
    constant_speed: 0.25 * motion[3]
  };
}
