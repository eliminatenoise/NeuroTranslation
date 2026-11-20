/* Invented inputs only. No stored subject trace, exemplar or measured force. */
const WalkingExample = (() => {
  const muscles = ['Tibialis anterior', 'Soleus', 'Medial gastrocnemius', 'Vastus medialis',
    'Rectus femoris', 'Semitendinosus', 'Gluteus maximus', 'Gluteus medius'];
  const markers = ['Left heel', 'Left second metatarsal', 'Right heel', 'Right second metatarsal',
    'Left anterior pelvic marker', 'Right anterior pelvic marker'];
  const anchors = Array.from({length: 49}, (_, k) => k * 30);
  const defaults = {speed: 0.60, offset: 0, gain: 1.6, shift: 0, channel: 'all'};

  function signals(timeMs, options) {
    const seconds = timeMs / 1000;
    const phase = seconds / 1.48;
    const angle = 2 * Math.PI * phase;
    const pelvisX = (seconds - 0.72) * options.speed + options.offset / 100;
    const foot = side => {
      const a = angle + (side === 1 ? Math.PI : 0);
      const x = pelvisX + 0.19 * Math.sin(a);
      const y = side === 1 ? 0.10 : -0.10;
      const z = 0.045 + 0.085 * Math.max(0, Math.cos(a)) ** 2;
      return [x - 0.08, y, z, x + 0.12, y, z - 0.012 + 0.020 * Math.sin(a)];
    };
    const pelvisZ = 0.94 + 0.014 * Math.cos(2 * angle);
    const marker = [...foot(1), ...foot(-1), pelvisX, 0.115, pelvisZ, pelvisX, -0.115, pelvisZ];
    // Each bell is an invented RMS envelope, in microvolts. No raw electrode waveform is simulated.
    const peak = [0.76,0.30,0.36,0.02,0.11,0.88,0.03,0.15];
    const height = [48,55,49,39,34,37,31,42];
    const background = [4,5,4,3,4,4,4,5];
    const emg = peak.map((p,k) => {
      const edit = options.channel === 'all' || Number(options.channel) === k;
      const t = phase - (edit ? options.shift / 1.48e3 : 0);
      const distance = t - p - Math.round(t - p);
      return (background[k] + height[k] * Math.exp(-0.5 * (distance / 0.105) ** 2)) * (edit ? options.gain : 1);
    });
    return [...marker, ...Array(6).fill(1), ...emg, ...Array(8).fill(1)];
  }
  function history(anchorMs, options) {
    return Array.from({length: 8}, (_, j) => signals(anchorMs - (7-j) * 30, options));
  }
  function reference(options) { return {...options, gain: 1, shift: 0}; }
  return {muscles, markers, anchors, defaults, history, reference};
})();
if (typeof module === 'object') module.exports = WalkingExample;
