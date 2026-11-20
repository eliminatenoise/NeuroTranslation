(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  const hints = {
    motion: "This model learned from the task and recent sensor turns.",
    upper: "This model also receives the upper-back electrical history.",
    lower: "This model also receives the lower-back electrical history.",
    full: "This model receives motion, the task and both electrical histories.",
    wrong: "The same full model receives both electrical histories from a second invented time. Its motion and task stay fixed."
  };
  const names = ["10 ms turn (°)", "Turn since start (°)", "Task", "Upper spread", "Upper differences", "Upper common spread", "Lower spread", "Lower differences", "Lower common spread"];
  const create = (tag, content, css) => {
    const el = document.createElement(tag);
    if (content !== undefined) el.textContent = content;
    if (css) el.className = css;
    return el;
  };
  function drawTurns(rows) {
    const svg = byId("trace");
    svg.querySelectorAll("[data-draw]").forEach(el => el.remove());
    function paint(tag, attrs, text) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
      el.setAttribute("data-draw", "");
      for (const [key, v] of Object.entries(attrs)) el.setAttribute(key, v);
      if (text) el.textContent = text;
      svg.append(el);
    }
    const values = rows.map(r => r[0]);
    const ceiling = Math.max(.2, Math.ceil(Math.max(...values) * 5) / 5);
    [0, .5, 1].forEach(fraction => {
      const y = 81 - fraction * 66;
      paint("line", {x1: 38, x2: 439, y1: y, y2: y, stroke: "#4c636c", "stroke-width": 1});
      paint("text", {x: 0, y: y + 4, fill: "#d4dfdf", "font-size": 11}, (fraction * ceiling).toFixed(1) + "°");
    });
    values.forEach((v, i) => {
      const height = 66 * v / ceiling;
      paint("rect", {x: 41 + i * 40, y: 81 - height, width: 32, height, rx: 2, fill: "#91d9c4"});
    });
    byId("trace-desc").textContent = "Ten successive unsigned sensor turns in degrees, oldest first: " + values.map(v => v.toFixed(3)).join(", ") + ".";
  }
  function table(target, caption, cols, rows) {
    const wrapper = create("div", undefined, "table-scroll");
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "region");
    wrapper.setAttribute("aria-label", caption);
    const t = create("table");
    t.append(create("caption", caption));
    const head = t.createTHead().insertRow();
    for (const c of cols) {
      const th = create("th", c);
      th.scope = "col";
      head.append(th);
    }
    const body = t.createTBody();
    for (const row of rows) {
      const tr = body.insertRow();
      row.forEach((v, i) => {
        const cell = create(i === 0 ? "th" : "td", String(v));
        if (i === 0) cell.scope = "row";
        tr.append(cell);
      });
    }
    wrapper.append(t);
    target.append(wrapper);
  }
  function inspectRows(rows, variant) {
    const target = byId("input-values");
    target.replaceChildren();
    target.append(create("p", "Ten 10 ms slices, oldest first. Electrical columns use the natural logarithm of one plus each spread or difference, calculated from invented grid voltages in µV. The task flag is 1 for moving and 0 for standing."));
    const columns = [0, 1, 2];
    if (["upper", "full", "wrong"].includes(variant)) columns.push(3, 4, 5);
    if (["lower", "full", "wrong"].includes(variant)) columns.push(6, 7, 8);
    table(target, "Values sent to the selected model", ["End (ms)", ...columns.map(i => names[i])],
      rows.map((r, i) => [(i - 9) * 10, ...columns.map(c => c === 2 ? r[c] : r[c].toFixed(3))]));
    if (columns.length > 3) target.append(create("p", "Spread is the median of the 32 channels’ within-slice standard deviations. Differences is the median of their root mean square sample-to-sample changes. Common spread is the standard deviation of the median across the grid at each sample."));
  }
  function renderExample() {
    const inputs = {
      task: document.querySelector('input[name="task"]:checked').value,
      motion: +byId("motion").value / 100,
      upper: +byId("upper").value / 100,
      lower: +byId("lower").value / 100
    };
    const mode = byId("variant").value;
    const rows = makeBackRotationExample(inputs);
    const donor = mode === "wrong" ? makeBackRotationExample(inputs, true) : undefined;
    const active = BackRotationModel.inputFor(mode, rows, donor);
    for (const id of ["motion", "upper", "lower"]) {
      const control = byId(id);
      const omitted = (mode === "motion" && id !== "motion") || (mode === "upper" && id === "lower") || (mode === "lower" && id === "upper");
      control.disabled = omitted;
      const caption = omitted ? "Unused" : inputs[id].toFixed(2) + "×";
      byId(id + "-value").textContent = caption;
      control.setAttribute("aria-valuetext", caption);
    }
    byId("variant-help").textContent = hints[mode];
    const degrees = BackRotationModel.predict(BACK_WEIGHTS, mode, rows, donor).toFixed(3);
    byId("forecast").textContent = degrees;
    byId("mobile-angle").textContent = degrees + "°";
    byId("carry").textContent = rows[9][1].toFixed(3) + "°";
    drawTurns(active);
    if (document.querySelector(".samples").open) inspectRows(active, mode);
  }
  if (location.protocol === "file:") {
    byId("offline-download").parentElement.remove();
  }
  try {
    renderExample();
    byId("editor").addEventListener("input", renderExample);
    byId("editor").addEventListener("submit", e => e.preventDefault());
    document.querySelector(".samples").addEventListener("toggle", renderExample);
    byId("restore").addEventListener("click", () => { byId("editor").reset(); renderExample(); });
  } catch {
    byId("forecast-description").textContent = "The model could not be opened. Extract the entire reader folder and reopen index.html.";
    for (const control of byId("editor").elements) control.disabled = true;
  }
})();
