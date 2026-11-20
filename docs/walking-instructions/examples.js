/* Invented positions in the observed pelvis's cutoff-local frame, millimetres. */
(() => {
  function history({ speed = 1.10, lift = 70, offset = 30 } = {}) {
    if (!Number.isFinite(speed) || !Number.isFinite(lift) || ![10,20,30,40].includes(offset)) {
      throw new Error("Choose a finite speed, lift amplitude and supported strike offset.");
    }
    const cutoff = offset / 100;
    const pelvisZ = t => 15 * Math.cos(4 * Math.PI * t);
    const rows = [];
    for (let step = -20; step <= 0; step++) {
      const t = cutoff + step / 100;
      // Smooth one-second cycle. The endpoint chord of the pelvis lies on +X.
      const pelvis = [speed * 1000 * step / 100, 4 * Math.sin(Math.PI * (step + 20) / 20), pelvisZ(t) - pelvisZ(cutoff)];
      const phase = 2 * Math.PI * t;
      const heel = [pelvis[0] + 145 * Math.cos(phase), -72 + 9 * Math.sin(phase), -800 + lift * (1 - Math.cos(phase)) / 2 - pelvisZ(cutoff)];
      rows.push([pelvis, heel]);
    }
    return rows;
  }
  globalThis.WalkingExamples = { history };
})();
