/* Analytic histories with one rotation axis and two grids of invented voltages. */
(() => {
  "use strict";
  function median(xs) {
    const sorted = xs.slice().sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }
  function spread(xs) {
    const mean = xs.reduce((s, x) => s + x, 0) / xs.length;
    return Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / xs.length);
  }
  function voltageGrid(bin, site, alternate) {
    const start = 20 * bin + (alternate ? 475 : 0);
    const phase = site === "upper" ? .27 : .69;
    const amplitude = site === "upper" ? 5 : 8;
    const rows = [];
    for (let channel = 0; channel < 32; channel++) {
      const c = channel + 1;
      const row = [];
      for (let sample = 1; sample <= 20; sample++) {
        const t = start + sample;
        const envelope = 1 + .42 * Math.sin(.028 * t + phase);
        row.push(amplitude * envelope * (Math.sin(t * .39 + c * .23) + .35 * Math.cos(t * .11 + phase * c)
          + .26 * Math.sin(t * .56 + c * .09 + phase) + .31 * Math.cos(t * .08 - phase)));
      }
      rows.push(row);
    }
    const rmsDiff = rows.map(r => Math.sqrt(r.slice(1).reduce((s, x, i) => s + (x - r[i]) ** 2, 0) / 19));
    const pooled = Array.from({length: 20}, (_, t) => median(rows.map(r => r[t])));
    return [median(rows.map(spread)), median(rmsDiff), spread(pooled)];
  }
  // Positive amplitude changes commute with the spread/RMS summaries before log1p.
  const patterns = new Map();
  function pattern(site, alternate) {
    const key = site + alternate;
    if (!patterns.has(key)) {
      patterns.set(key, Array.from({length: 10}, (_, i) => voltageGrid(i, site, alternate)));
    }
    return patterns.get(key);
  }
  function make({task, motion, upper, lower}, alternate = false) {
    const walk = Number(task) === 621 ? 1 : 0;
    const orientation = [0];
    for (let i = 0; i < 10; i++) {
      const delta = (.17 + .14 * Math.sin(.64 * i - .55) + .055 * Math.cos(.98 * i)) * motion;
      orientation.push(orientation[i] + delta);
    }
    const up = pattern("upper", alternate);
    const down = pattern("lower", alternate);
    return Array.from({length: 10}, (_, i) => [
      Math.abs(orientation[i + 1] - orientation[i]), Math.abs(orientation[i + 1] - orientation[0]), walk,
      ...up[i].map(v => Math.log1p(upper * v)), ...down[i].map(v => Math.log1p(lower * v))
    ]);
  }
  if (typeof module !== "undefined" && module.exports) module.exports = make;
  else globalThis.makeBackRotationExample = make;
})();
