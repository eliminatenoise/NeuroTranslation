// SPDX-License-Identifier: CC0-1.0
// Capture the document before controls, canvases or output rows change.
const portablePage = "<!doctype html>\n" + document.documentElement.outerHTML + "\n";
const el = id => document.getElementById(id);
const choice = el("finger"), motion = el("motion"), power = el("power");

function fillTable(id, rows, selected) {
  const body = el(id);
  const content = document.createDocumentFragment();
  rows.forEach((row, i) => {
    const tr = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row"; name.textContent = fingers[i];
    if (i === selected) tr.className = "selected";
    tr.append(name);
    row.forEach(value => {
      const td = document.createElement("td");
      td.textContent = value.toFixed(1);
      tr.append(td);
    });
    content.append(tr);
  });
  body.replaceChildren(content);
}

function render() {
  const f = choice.selectedIndex;
  const scale = Number(power.value);
  const pred = predict(f, motion.value, scale);
  el("power-label").value = scale.toFixed(2) + "×";
  el("power").setAttribute("aria-valuetext", scale.toFixed(2) + " times invented band power");
  el("selected-finger").textContent = "Screen cue · " + fingers[f];
  el("chart-title").textContent = (f === 0 ? "Thumb" : fingers[f] + " finger") + " readings";
  fillTable("forecast-body", fingers.map((_, i) => [pred.hold[i],pred.cue[i],pred.brain[i]]), f);
  fillTable("history-body", fingers.map((_, i) => pred.glove.map(row=>row[i])), f);
  drawGlove(el("map"), f);
  drawChart(el("chart"), f, pred);
  el("update-status").textContent = fingers[f] + " forecast in counts. Hold last " +
    pred.hold[f].toFixed(1) + ", glove and cue " + pred.cue[f].toFixed(1) +
    ", with brain signal " + pred.brain[f].toFixed(1) + ".";
}

choice.addEventListener("change", render);
motion.addEventListener("change", render);
power.addEventListener("input", render);
el("download").href = URL.createObjectURL(new Blob([portablePage], {type: "text/html;charset=utf-8"}));
new ResizeObserver(render).observe(el("chart"));
render();
