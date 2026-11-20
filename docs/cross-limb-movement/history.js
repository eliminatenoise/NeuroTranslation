/* Invented examples on the studies' native sampling clocks. */
globalThis.MovementHistory = (() => {
  const lower = ['Left', 'Right'].flatMap(side =>
    ['tibialis anterior', 'soleus', 'medial gastrocnemius', 'peroneus longus'].map(muscle => side + ' ' + muscle));
  const upper = ['anterior deltoid', 'brachioradialis', 'flexor digitorum', 'common extensor digitorum', 'first dorsal interosseous'].map(muscle => 'Right ' + muscle);
  const domains = [
    { key: 'balance', names: lower, offset: 0, axes: ['ML', 'SI', 'AP'], marker: 'Sacrum', unit: 'µV', emgHz: 256, poseHz: 256, samples: 160, positions: 160 },
    { key: 'arm', names: upper, offset: 8, axes: ['X', 'Y', 'Z'], marker: 'Wrist', unit: 'native units', emgHz: 4000, poseHz: 500, samples: 2500, positions: 314 }
  ];
  const time = (i, n, hz) => (i + 1 - n) / hz;
  function example(domain) {
    const spec = domains[domain], arm = domain === 1;
    const emg = Array.from({ length: spec.samples }, (_, i) => {
      const t = time(i, spec.samples, spec.emgHz) + 0.625;
      return spec.names.map((_, c) => {
        const burst = Math.exp(-((t - (arm ? 0.51 : 0.46) - c * 0.006) ** 2) / 0.012);
        const amplitude = (arm ? 0.03 : 14) * (1 + c * 0.06) * (0.75 + burst);
        return amplitude * (Math.sin(2 * Math.PI * (29 + c * 3.5) * t + 0.3 * c) +
          0.42 * Math.sin(2 * Math.PI * (67 + c * 1.3) * t + 0.55));
      });
    });
    const pose = Array.from({ length: spec.positions }, (_, i) => {
      const t = time(i, spec.positions, spec.poseHz);
      return (arm ? [32, -12, 22] : [5, 2.5, -4]).map((amp, c) =>
        amp * Math.sin((arm ? 2.2 : 5.7) * t + c * 0.65) +
        amp * 0.24 * Math.cos(9 * t + c * 0.3));
    });
    return { domain, emg, pose, enabled: spec.names.map(() => true), session: arm ? 1 : 0, direction: arm ? 0 : 1 };
  }
  function prepare(h) {
    const spec = domains[h.domain], width = spec.emgHz / 32;
    const muscle_mask = Array.from({ length: 13 }, (_, i) => Boolean(h.enabled[i - spec.offset]));
    const cutoff = h.pose.at(-1);
    const relative = row => row.map((v, i) => v - cutoff[i]);
    const past_rms = new Array(13).fill(0), age_s = [], patch_xyz_mm = [], patch_rms = [];
    for (let bin = 0; bin < 20; bin++) {
      const end = (bin - 19) / 32;
      const last = h.pose.length - 1 + Math.floor(end * spec.poseHz);
      patch_xyz_mm.push(relative(h.pose[last]));
      age_s.push(end - time(last, h.pose.length, spec.poseHz));
      const rms = new Array(13).fill(0);
      h.enabled.forEach((enabled, c) => {
        if (!enabled) return;
        let sum = 0;
        for (let i = bin * width; i < (bin + 1) * width; i++) sum += h.emg[i][c] ** 2;
        rms[c + spec.offset] = Math.sqrt(sum / width);
        if (bin >= 16) past_rms[c + spec.offset] += sum / (4 * width);
      });
      patch_rms.push(rms);
    }
    const pastAt = t => {
      const i = h.pose.length - 1 + t * spec.poseHz, lo = Math.floor(i), hi = Math.ceil(i);
      return h.pose[lo].map((v, c) => v + (i - lo) * (h.pose[hi][c] - v));
    };
    const prior = pastAt(-0.125);
    const repeat_path_mm = Array.from({ length: 32 }, (_, i) => pastAt((i + 1) / 256 - 0.125).map((v, c) => v - prior[c]));
    return {domain: h.domain, session: h.session, direction: h.direction, muscle_mask, patch_rms,
      patch_xyz_mm, age_s, past_rms: past_rms.map(Math.sqrt), repeat_path_mm};
  }
  return { domains, time, example, prepare };
})();
