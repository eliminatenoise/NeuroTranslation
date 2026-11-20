/* Deterministic invented examples. No participant samples. */
(() => {
  function example(name) {
    const phase = { rise: 0, level: 1, fall: 2 }[name];
    if (phase === undefined) throw new RangeError('Choose an invented history.');
    const load = [],
      emg = [],
      donor = [];
    const round = (value) => Number(value.toFixed(6));
    for (let i = 0; i <= 200; i++) {
      const t = i / 200;
      const direction = [1, 0, -1][phase];
      const start = [0.08, 0.32, 0.68][phase];
      const ramp = t * t * (3 - 2 * t);
      load.push(
        round(start + direction * (0.46 * ramp + 0.08 * t) + 0.006 * Math.sin(3 * Math.PI * t)),
      );
      const peak = [0.68, 0.46, 0.28][phase];
      const amplitude =
        0.025 + (0.2 + 0.17 * Math.abs(direction)) * Math.exp(-((t - peak) ** 2) / 0.035);
      emg.push(
        round(amplitude * (Math.sin(28 * Math.PI * t + phase) + 0.4 * Math.sin(47 * Math.PI * t))),
      );
      donor.push(
        round(
          (0.04 + 0.25 * Math.exp(-((t - 0.84) ** 2) / 0.02)) *
            (Math.sin(32 * Math.PI * t + 0.8) + 0.25 * Math.sin(51 * Math.PI * t)),
        ),
      );
    }
    return { load, emg, donor };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = example;
  else globalThis.pedalExample = example;
})();
