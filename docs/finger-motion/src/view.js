// SPDX-License-Identifier: CC0-1.0
// Preserve the standalone document before tables and download URLs are inserted.
const portable = "<!doctype html>\n"+document.documentElement.outerHTML+"\n";
const el = id => document.getElementById(id);
const digit = el("digit"), phase = el("phase"), level = el("level");
const axisMaximum = 140; // Shared by every view; checked over every allowed control combination.
const format = value => value.toFixed(2);

function render() {
  const d = digit.selectedIndex, ph = Number(phase.value), amp = Number(level.value);
  const family = document.querySelector('input[name=family]:checked').value;
  const outputs = predict(d,ph,amp,family);
  const rows = document.createDocumentFragment();
  fingers.forEach((name,f) => {
    const row = document.createElement("tr"), label = document.createElement("th");
    if (d === f) row.className = "cued";
    label.scope="row"; label.textContent=name; row.append(label);
    modes.forEach((mode,k)=>{
      const td = document.createElement("td");
      const value = outputs[k][f], track = document.createElement("span"), bar=document.createElement("span");
      track.setAttribute("aria-hidden","true"); track.className="track";
      bar.className="bar "+mode; bar.style.width = (100*value/axisMaximum)+"%";
      track.append(bar); td.append(format(value),track); row.append(td);
    });
    rows.append(row);
  });
  el("rows").replaceChildren(rows);
  const multiplier = (amp/4).toFixed(2)+"×";
  el("level-out").value = multiplier;
  level.setAttribute("aria-valuetext",multiplier+" amplitude");
  const delta = outputs[2][d]-outputs[0][d];
  const changed = Math.abs(delta)<0.005 ? "changes by less than 0.01" :
    (delta>0 ? "rises by " : "falls by ")+format(Math.abs(delta));
  const name = fingers[d].toLowerCase()+(d===0 ? "" : " finger");
  const detail = "For the "+name+", the estimate "+changed+" counts per step when cortex is added to the cue.";
  el("readout-note").textContent = detail+" All bars share a 0–140 scale.";
  el("status").textContent = (family==="ridge" ? "Ridge. " : "Transformer. ")+detail;
}
for (const control of [digit,phase,...document.querySelectorAll("input[name=family]")]) control.addEventListener("change",render);
level.addEventListener("input",render);
el("save").href=URL.createObjectURL(new Blob([portable],{type:"text/html;charset=utf-8"}));
render();
