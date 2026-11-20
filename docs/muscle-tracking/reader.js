(() => {
  "use strict";
  const el = id => document.getElementById(id);
  const fields = ["length", "angle", "alternate"];
  const methods = {
    full: ["Transformer · length + earlier angle", "One fitted Transformer uses the earlier length and angle histories together."],
    length: ["Transformer · length alone", "A second Transformer learned from the length history alone."],
    wrong: ["Transformer · alternate angles", "The full model keeps the lengths and receives the alternate angle series in place of the original angles."],
    ridge: ["Linear length model", "A fitted straight-line combination of the five ending lengths and five changes in length."],
    zero: ["Hold last length", "Keep the last length unchanged for the next ten tracking steps."],
    recent: ["Repeat recent change", "Repeat the change in length between step −10 and step 0."],
    typical: ["Typical training change", "Use the median change learned from the training recordings, giving each person and trial equal weight."],
    projection: ["Straight-line projection", "Continue the recent change along the reference axis and convert it back to a change along the bundle. The formula uses the last available angle."]
  };
  const svgNS = "http://www.w3.org/2000/svg";
  const f3 = value => value.toFixed(3);
  const signed = value => (Number(f3(value)) > 0 ? "+" : "") + f3(value).replace(/^-0\.000$/, "0.000").replace("-", "−");
  let history;
  let predictions;
  let dirty = false;

  function node(tag, attrs, text) {
    const n = document.createElementNS(svgNS, tag);
    for (const [key, val] of Object.entries(attrs)) n.setAttribute(key, val);
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function draw(lengths, predicted, status) {
    const svg = el("plot");
    svg.replaceChildren();
    // Tight plots need readable tick labels at phone widths.
    const width = Math.max(290, Math.min(810, Math.floor(svg.getBoundingClientRect().width)));
    const height = width < 400 ? 205 : 230;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    if (!lengths) {
      svg.append(node("text", {x: 12, y: 60, class: "axis"}, status));
      svg.setAttribute("aria-label", status);
      return;
    }
    const low = Math.min(...lengths, predicted ?? Infinity);
    const high = Math.max(...lengths, predicted ?? -Infinity);
    const mid = (low + high) / 2;
    const span = Math.max(high - low, 0.2);
    const lo = mid - span * 0.64, hi = mid + span * 0.64;
    const left = 57, right = width - 14, top = 17, bottom = height - 40;
    const x = step => left + (step + 20) / 30 * (right - left);
    const y = v => bottom - ((v - lo) / (hi - lo)) * (bottom - top);
    for (const tick of [lo, mid, hi]) {
      svg.append(node("line", {x1: left, x2: right, y1: y(tick), y2: y(tick), class: "grid"}));
      svg.append(node("text", {x: left - 7, y: y(tick) + 4, "text-anchor": "end", class: "axis"}, tick.toFixed(2)));
    }
    svg.append(node("line", {x1: x(0), x2: x(0), y1: top, y2: bottom, class: "cut"}));
    for (const [step, label] of [[-20, "−20"], [-10, "−10"], [0, "0"], [10, "+10"]]) {
      svg.append(node("text", {x: x(step), y: bottom + 17, class: "axis", "text-anchor": "middle"}, label));
    }
    svg.append(node("text", {x: (left + right) / 2, y: height - 1, "text-anchor": "middle", class: "axis"}, "Tracking steps from cutoff"));
    const points = lengths.map((v, i) => x(i - 20) + "," + y(v)).join(" ");
    svg.append(node("polyline", {points, class: "history"}));
    for (const [i, v] of lengths.entries()) {
      svg.append(node("circle", {cx: x(i - 20), cy: y(v), r: 2.3, class: "dot"}));
    }
    if (predicted !== null) svg.append(node("circle", {cx: x(10), cy: y(predicted), r: 6.5, class: "forecast"}));
    svg.setAttribute("aria-label", "Invented history begins at " + f3(lengths[0]) + " mm and ends at " +
      f3(lengths[20]) + " mm. " + (predicted === null ? status : "Predicted length at +10 is " + f3(predicted) + " mm."));
  }

  function refresh() {
    const method = el("method").value;
    el("method-note").textContent = methods[method][1];
    const tbody = el("predictions");
    tbody.replaceChildren();
    el("original-change").textContent = !predictions || dirty ? "—" : signed(predictions.full) + " mm";
    el("alternate-change").textContent = !predictions || dirty ? "—" : signed(predictions.wrong) + " mm";
    if (!predictions || dirty) {
      el("direction").textContent = "";
      el("change").textContent = "—"; el("endpoint").textContent = "—";
      draw(null, null, dirty ? "Apply edited values to see a forecast." : "Forecast unavailable.");
      return;
    }
    const delta = predictions[method];
    const endpoint = delta === null ? null : history.length[20] + delta;
    const visibleChange = delta === null ? null : Number(f3(delta));
    el("direction").textContent = delta === null ? "Angle too close to a right angle" : visibleChange === 0 ? "No change at this precision" : delta < 0 ? "Shorter" : "Longer";
    el("change").textContent = delta === null ? "Undefined" : signed(delta) + " mm";
    el("endpoint").textContent = endpoint === null ? "—" : f3(endpoint) + " mm";
    draw(history.length, endpoint, "The projection is undefined at the last available angle.");
    for (const [key, [label]] of Object.entries(methods)) {
      const row = tbody.insertRow();
      const th = document.createElement("th");
      th.scope = "row"; th.textContent = label; row.append(th);
      row.insertCell().textContent = predictions[key] === null ? "Undefined" : signed(predictions[key]);
    }
  }

  function parse(key) {
    const count = key === "length" ? 21 : 20;
    const field = el(key);
    const raw = field.value.trim();
    const items = raw.includes(",") ? raw.split(",").map(s => s.trim()) : raw.split(/\s+/);
    const regex = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
    const values = items.map(Number);
    const bad = items.length !== count || items.some(v => !regex.test(v)) ||
      values.some(v => !Number.isFinite(v) || (key === "length" && v <= 0));
    if (bad) {
      field.setAttribute("aria-invalid", "true");
      field.focus();
      throw new Error(`Enter ${count} ${key === "length" ? "positive, finite lengths in mm" : "finite angles in degrees"} for this example.`);
    }
    return values;
  }

  function apply() {
    fields.forEach(key => el(key).removeAttribute("aria-invalid"));
    el("error").textContent = "";
    try {
      const candidate = Object.fromEntries(fields.map(key => [key, parse(key)]));
      if (!globalThis.FASCICLE_WEIGHTS || !globalThis.FascicleModel) throw new ReferenceError("Missing model");
      const next = FascicleModel.predict(globalThis.FASCICLE_WEIGHTS, candidate);
      history = candidate; predictions = next; dirty = false;
    } catch (e) {
      predictions = null;
      el("error").textContent = e instanceof ReferenceError ? "The local model files could not be loaded. Keep the extracted reader files in the same folder." : e.message;
    }
    refresh();
  }

  function preset(kind) {
    const value = FascicleExample.make(kind);
    el("preset").value = kind;
    fields.forEach(key => { el(key).value = value[key].join(", "); });
    dirty = false;
    apply();
  }
  el("preset").addEventListener("change", () => preset(el("preset").value));
  el("restore").addEventListener("click", () => {el("method").value = "full"; preset("shorten");});
  el("method").addEventListener("change", refresh);
  el("apply").addEventListener("click", apply);
  for (const key of fields) {
    el(key).addEventListener("input", () => {
      dirty = true; el("preset").value = "custom";
      el("error").textContent = ""; el(key).removeAttribute("aria-invalid");
      refresh();
    });
  }
  el("download").hidden = location.protocol === "file:";
  preset("shorten");
  let lastWidth;
  new ResizeObserver(([entry]) => {
    if (entry.contentRect.width === lastWidth) return;
    lastWidth = entry.contentRect.width;
    refresh();
  }).observe(el("plot"));
})();
