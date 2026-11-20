// Invented smooth curves. Phase moves the cutoff through a nominal 1.234-second cycle.
function makeKneeMomentExample(phase = 0) {
  const frames = Array.from({length:400}, (_,i) => 1000 + i);
  const angles_deg = frames.map((_, i) => {
    const tau = 2 * Math.PI;
    const a = tau * ((i-399) / 123.4 + phase / 100);
    function side(x) {
      const wave = (1-Math.cos(x))/2;
      return [5.13 + 50*wave**3 + 9.7*(1-Math.cos(2*x+.45))/2,
        7.31 + 18*Math.cos(x+.63), 3.18 + 9.1*Math.sin(x-.9) + 3.7*Math.sin(2*x+.5)];
    }
    const r = side(a), l = side(a+Math.PI);
    return [r[0],l[0],r[1],l[1],r[2],l[2]];
  });
  return {domain:'knee_moment', mode:'trained', frames, angles_deg};
}
if (typeof module === 'object' && module.exports) module.exports = makeKneeMomentExample;
