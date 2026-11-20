(() => {
  "use strict";
  // Entirely invented. Rounding here makes the editable text the actual model input.
  const rounded = v => Number(v.toFixed(3));
  function make(kind) {
    const sign = {shorten: -1, steady: 0, lengthen: 1}[kind];
    if (sign === undefined) throw new Error("Choose a known example.");
    const length = Array.from({length: 21}, (_, i) =>
      rounded(27 + sign * (0.045 * i + 0.12 * Math.sin(i / 3))));
    const angle = Array.from({length: 20}, (_, i) => rounded(10 - sign * (i / 19 + 0.3 * Math.sin(i / 3))));
    const alternate = Array.from({length: 20}, (_, i) => rounded(10.7 + 0.9 * Math.sin(0.5 + i / 4)));
    return {length, angle, alternate};
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {make};
  else globalThis.FascicleExample = {make};
})();
