'use strict';
// Entirely invented inputs. Coordinates are relative to each heel’s first position.
function exampleHistory(travel, finalRightLoad) {
  if (!Number.isFinite(travel) || travel < -100 || travel > 100 || !Number.isFinite(finalRightLoad) || finalRightLoad < 0 || finalRightLoad > 600) {
    throw new RangeError('Input is outside this example.');
  }
  const heel = [], force = [];
  for (let t = 0; t < 10; t++) {
    const u = t / 9;
    const wave = t === 9 ? 0 : Math.sin(Math.PI * u);
    const size = Math.abs(travel) / 100;
    heel.push([-0.4 * travel * u, -2 * size * wave, 4 * size * wave,
      travel * u * u, 3 * size * wave, 18 * size * wave]);
    const right = 300 + (finalRightLoad - 300) * u;
    force.push([600 - right, right]);
  }
  return {heel, force};
}
