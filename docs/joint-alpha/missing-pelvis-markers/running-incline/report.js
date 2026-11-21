"use strict";

const data = JSON.parse(document.querySelector("#data").textContent);
const target = document.querySelector("#target");
const grades = ["+1","+6","-4"];
const methods = {
  learned_stride:"Earlier stride with learned correction",
  stride:"Replay the earlier stride",
  zero:"Predict zero displacement",
  camera_speed:"Continue recent camera speed",
  chair_direct:"Chair-trained attention",
  chair_correction:"Chair model correcting recent speed",
};

function cell(tag, text) {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}

function table(id, field, values) {
  const body = document.querySelector("#" + id + " tbody");
  const groups = grades.map(grade => values[grade][field]);
  const best = groups.map(group => group ? Math.min(...Object.values(group)) : null);
  const rows = Object.entries(methods).map(([name,label]) => {
    const row = document.createElement("tr");
    const heading = cell("th",label);
    heading.scope = "row";
    row.append(heading);
    groups.forEach((group,index) => {
      const value = group ? group[name] : null;
      const result = cell("td",value === null ? "—" : value.toFixed(2));
      if (value !== null && value === best[index]) result.classList.add("best");
      row.append(result);
    });
    return row;
  });
  body.replaceChildren(...rows);
}

function signed(value) {
  return (value > 0 ? "+" : "") + value.toFixed(2).replace("-","−");
}

function render() {
  const score = data.primary[target.value];
  table("average","person_equal_mae_mm",score.common);
  table("tail","pooled_p90_abs_error_mm",score.common);
  const reference = score.common["+1"];
  const label = reference.people + " runners, " + reference.windows.toLocaleString("en") + " forecasts on each slope.";
  document.querySelector("#support").textContent = label +
    (reference.descriptive_only ? " Forecast errors need at least six runners." : "");
  const comparisons = score.learned_minus_stride;
  const text = comparisons ? grades.map(grade => {
    const row = comparisons[grade];
    return grade.replace("-","−") + "% " + signed(row.mean_mm) + " mm (95% interval "
      + row.bootstrap95_mm.map(signed).join(" to ") + " mm).";
  }).join(" ") : "";
  document.querySelector("#paired").textContent = text
    ? "Change in error after adding the learned correction. " + text : "";
}

render();
target.addEventListener("change",render);
document.querySelector("#controls").hidden = false;
document.querySelector("#results").hidden = false;
