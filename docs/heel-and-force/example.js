/* All numbers in these example histories are invented. No recording is sampled. */
(() => {
  "use strict";
  const channels = [
    "Tibialis anterior",
    "Soleus",
    "Medial gastrocnemius",
    "Vastus medialis",
    "Rectus femoris",
    "Semitendinosus",
    "Gluteus maximus",
    "Gluteus medius",
  ];
  function invented({ rise = 4, gain = 1, offset = 24, alternate = false } = {}) {
    const marker = Array.from({ length: 24 }, (_, i) => {
      const t = i / 23;
      return [
        [300 + 3 * t + 1.2 * t * t, 184 + .6 * Math.sin(t * 1.8), 49 + rise * t * t],
        [477 + .8 * t, 178 + .4 * t, 19 + .25 * t],
      ];
    });
    const size = [20, 39, 45, 23, 16, 17, 14, 21];
    const emg = Array.from({ length: 4 }, (_, b) =>
      size.map((v, j) => {
        const k = alternate ? 3 - b : b;
        const amplitude = alternate ? .72 + .06 * (j % 3) : 1;
        return gain * amplitude * v * (1.02 + .19 * Math.sin(k * .76 + j * .44) + k * .025);
      }));
    return { lab_marker_mm: marker, emg_rms_uV: emg, offset_frames: offset };
  }
  globalThis.HeelAndForceExamples = Object.freeze({ invented, channels });
})();
