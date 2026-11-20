/* Plain-script area 2 ridge. Works in a local HTML file without network access. */
(function (root) {
  "use strict";
  const session = "C_20170912_COactpas";
  const units = Object.freeze([
    "ch12:sort1", "ch13:sort1", "ch16:sort1", "ch17:sort1", "ch18:sort1",
    "ch24:sort1", "ch25:sort1", "ch27:sort1", "ch27:sort2", "ch29:sort1",
    "ch35:sort1", "ch35:sort2", "ch37:sort1", "ch39:sort1", "ch49:sort1",
    "ch52:sort1", "ch52:sort2", "ch53:sort1", "ch55:sort1", "ch56:sort1",
    "ch58:sort1", "ch61:sort1", "ch62:sort1", "ch65:sort1", "ch67:sort1",
    "ch70:sort1", "ch72:sort1", "ch73:sort1", "ch90:sort1", "ch92:sort1"
  ]);
  function sameUnits(ids) {
    return Array.isArray(ids) && ids.length === units.length && units.every((c, i) => c === ids[i]);
  }
  function vector(x, size, predicate = Number.isFinite) {
    return Array.isArray(x) && x.length === size && x.every(predicate);
  }
  function checkCues(rows) {
    for (const col of [0, 3, 6]) {
      for (let t = 0; t < rows.length; t++) {
        const row = rows[t], prev = t ? rows[t - 1] : null;
        if (![0, 1].includes(row[col]) || (prev && prev[col] > row[col])) throw Error("invalid cue flag");
        if (col === 6) continue;
        const [x, y] = row.slice(col + 1, col + 3);
        if (row[col] === 0 && (x !== 0 || y !== 0)) throw Error("hidden direction");
        if (row[col] === 1 && Math.abs(Math.hypot(x, y) - 1) > 1e-5) throw Error("invalid direction");
        if (prev && prev[col] === 1 && Math.hypot(x - prev[col + 1], y - prev[col + 2]) > 1e-5)
          throw Error("changed direction");
      }
    }
  }
  function predict(w, input) {
    if (!w || w.format !== "area2-handle-ridge-v1" || w.session !== session ||
        w.mode !== "all" || w.horizon_ms !== 100 || w.outcome_unit !== "cm" || !sameUnits(w.unit_ids))
      throw Error("unexpected ridge weights, session, unit order or output");
    if (!input || input.session !== session || !sameUnits(input.unit_ids))
      throw Error("input session or sorted-unit identity");
    if (!vector(w.center, 205) || !vector(w.scale, 205, x => Number.isFinite(x) && x > 0) ||
        !vector(w.coef, 205, row => vector(row, 2)) || !vector(w.intercept, 2))
      throw Error("invalid ridge values");
    const x = [];
    for (const [key, width] of [["movement", 4], ["cue", 7], ["neural", 30]]) {
      if (!vector(input[key], 5, row => vector(row, width))) throw Error("invalid history: " + key);
      if (key === "neural" && input.neural.some(row => row.some(v => !Number.isSafeInteger(v) || v < 0)))
        throw Error("invalid archived spike count");
      if (key === "cue") checkCues(input.cue);
      for (const row of input[key]) x.push(...row);
    }
    const out = [...w.intercept];
    for (let i = 0; i < x.length; i++) {
      const z = (x[i] - w.center[i]) / w.scale[i];
      out[0] += z * w.coef[i][0];
      out[1] += z * w.coef[i][1];
    }
    if (!out.every(Number.isFinite)) throw Error("nonfinite ridge forecast");
    return out;
  }
  root.Area2Ridge = Object.freeze({predict, session, unitIds: units});
})(globalThis);
