/* Units and sample order follow the Peterson/Ferris v1.0.3 study. */
(function (host) {
  'use strict';
  const names = ['Tibialis anterior', 'Soleus', 'Medial gastrocnemius', 'Peroneus longus'];
  const labels = Array.from({length: 8}, (_, i) => (i < 4 ? 'Left ' : 'Right ') + names[i % 4].toLowerCase());
  const axes = ['ML', 'SI', 'AP'];
  function validate(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('Enter one object with leg_uv, sacrum_mm, posture and direction.');
    if (![0, 1].includes(input.posture)) throw Error('Posture must be 0 (standing) or 1 (walking).');
    if (![-1, 1].includes(input.direction)) throw Error('Direction must be −1 (counterclockwise) or 1 (clockwise).');
    for (const [name, width] of [['leg_uv', 8], ['sacrum_mm', 3]]) {
      if (!Array.isArray(input[name]) || input[name].length !== 160) throw Error(name + ' needs exactly 160 rows.');
      input[name].forEach((row, i) => {
        if (!Array.isArray(row) || row.length !== width || !row.every(Number.isFinite)) throw Error(name + ', row ' + (i + 1) + ', needs ' + width + ' finite numbers.');
      });
    }
    return {leg_uv: input.leg_uv, sacrum_mm: input.sacrum_mm, posture: input.posture, direction: input.direction};
  }
  function scaled(base, posture, direction, legFactor, pathFactor) {
    const last = base.sacrum_mm.at(-1);
    return validate({
      leg_uv: base.leg_uv.map(row => row.map(v => legFactor * v)),
      sacrum_mm: base.sacrum_mm.map(row => row.map((v, k) => last[k] + (v - last[k]) * pathFactor)),
      posture, direction
    });
  }
  function previousRms(leg) {
    return labels.map((_, k) => Math.hypot(...leg.slice(-32).map(row => row[k])) / Math.sqrt(32));
  }
  function reference(input, method) {
    const p = input.sacrum_mm;
    const last = p.at(-1);
    const path = Array.from({length: 32}, (_, i) => last.map((v, k) => {
      if (method === 'stationary') return 0;
      if (method === 'repeat') return p[128 + i][k] - p[127][k];
      const steps = method === 'velocity16' ? 16 : 32;
      return (i + 1) * (v - p[159 - steps][k]) / steps;
    }));
    return {future_rms_uv: previousRms(input.leg_uv), future_path_mm: path};
  }
  function validOutput(x) {
    return x && x.future_rms_uv?.length === 8 && Array.from(x.future_rms_uv).every(Number.isFinite) &&
      x.future_path_mm?.length === 32 && Array.from(x.future_path_mm).every(row => row?.length === 3 && Array.from(row).every(Number.isFinite));
  }
  host.MuscleMotionExperiment = {axes, names, labels, validate, scaled, previousRms, reference, validOutput};
})(globalThis);
