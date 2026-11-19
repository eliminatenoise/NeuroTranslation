"use strict";
(() => {
  const study = window.PINCH_INTERVAL_RESULTS;
  const id = key => document.getElementById(key);
  const phases = {
    initial_rest: "Initial rest", ramp_up: "Ramp up", hold: "Hold",
    release: "Release", final_rest: "Final rest"
  };
  const schemes = ["pooled", "by_issue_phase"];
  const schemeNames = ["One width", "Width by cue phase"];
  const definitions = {
    coverage: "Coverage is the percentage of later readings inside the band, including its edges. The calibration target was 90%.",
    mean_width: "Mean width is the average distance between the two band limits, in fractions of MVC. Narrower bands can miss more often.",
    mean_interval_score: "The interval score counts the band width plus a penalty when the reading lands outside. Lower is better."
  };
  const choices = ["persistence", "history_phase", "history_phase_paired_grid"];
  const namespace = "http://www.w3.org/2000/svg";
  function element(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function svg(name, attrs) {
    const node = document.createElementNS(namespace, name);
    for (const [attr,value] of Object.entries(attrs)) node.setAttribute(attr, String(value));
    return node;
  }
  function value(record, measure) {
    return measure === "coverage" ? record.covered / record.issue_windows * 100 : record[measure];
  }
  function display(v, measure) {
    return measure === "coverage" ? v.toFixed(1) + "%" : v.toFixed(4);
  }
  function option(key, label) {
    const o = element("option", "", label); o.value = key; return o;
  }
  function parts(breakdown) {
    const rows = [{key:"all", label:"All cutoffs", group:study.overall}];
    if (breakdown === "day") {
      for (const day of ["7","8"]) rows.push({key:"day-"+day,label:"Day "+day,group:study.by_indexed_day[day]});
    } else {
      for (const [phase,label] of Object.entries(phases)) rows.push({key:phase,label,group:study.by_issue_phase[phase]});
    }
    return rows;
  }
  function validate(group) {
    for (const model of choices) {
      for (const scheme of schemes) {
        const s = group[model][scheme];
        const counts = [s.covered,s.miss_low,s.miss_high];
        if (!Number.isSafeInteger(s.issue_windows) || s.issue_windows < 1 ||
            counts.some(n => !Number.isSafeInteger(n) || n < 0) ||
            counts.reduce((a,b) => a+b,0) !== s.issue_windows ||
            [s.mean_width,s.mean_interval_score].some(v => !Number.isFinite(v) || v < 0) ||
            s.mean_interval_score < s.mean_width) throw Error("Aggregate count or unit mismatch");
      }
    }
  }
  function track(fixed, phased, max, withTarget) {
    const plot = svg("svg",{class:"track",height:42,width:"100%","aria-hidden":"true"});
    const percent = x => (100*x/max)+"%";
    plot.append(svg("line",{x1:0,x2:"100%",y1:21,y2:21,stroke:"#b0bdb4"}));
    if (withTarget) plot.append(svg("line",{x1:"90%",x2:"90%",y1:0,y2:42,stroke:"#40554b","stroke-dasharray":"3 3"}));
    plot.append(svg("circle",{cx:percent(fixed),cy:13,r:5,fill:"#1b6460",stroke:"#164845","stroke-width":1.7}));
    const marker = svg("svg",{x:percent(phased),width:1,height:42,overflow:"visible"});
    marker.append(svg("path",{d:"M0 22 L6 28 L0 34 L-6 28 Z",fill:"#b46627",stroke:"#74431d","stroke-width":1.7}));
    plot.append(marker); return plot;
  }
  function drawDetails(rows) {
    const current = rows.find(r => r.key === id("slice").value) || rows[0];
    const model = id("model").value, table = id("counts-body");
    table.replaceChildren();
    for (const [i,scheme] of schemes.entries()) {
      const s = current.group[model][scheme];
      const row = element("tr"); const heading = element("th","",schemeNames[i]); heading.scope = "row";row.append(heading);
      const tails = count => count.toLocaleString("en")+" ("+(100*count/s.issue_windows).toFixed(1)+"%)";
      for (const n of [tails(s.miss_low),s.covered,tails(s.miss_high),display(value(s,"coverage"),"coverage"),s.mean_width.toFixed(4),s.mean_interval_score.toFixed(4)]) row.append(element("td","",String(n)));
      table.append(row);
    }
    const ref = current.group[model].pooled;
    id("support").textContent = current.label+" · "+ref.issue_windows.toLocaleString("en")+" forecast cutoffs from "+ref.trials+" trials, "+ref.participants+" people and "+ref.indexed_days+" indexed "+(ref.indexed_days===1?"day.":"days.");
    for (const button of id("chart").querySelectorAll("button")) button.setAttribute("aria-pressed", String(current.key === button.dataset.key));
  }
  function draw() {
    const model=id("model").value, measure=id("measure").value;
    const rows=parts(id("breakdown").value), chart=id("chart");
    const previous=id("slice").value;
    id("slice").replaceChildren(...rows.map(r=>option(r.key,r.label)));
    if (rows.some(r=>r.key===previous)) id("slice").value=previous;
    chart.replaceChildren();
    const allValues=rows.flatMap(r=>schemes.map(s=>value(r.group[model][s],measure)));
    const max=measure==="coverage"?100:Math.max(.001,Math.ceil(Math.max(...allValues)*1000)/1000);
    id("definition").textContent=definitions[measure];id("target-key").hidden=measure!=="coverage";
    chart.append(element("p","axis","Scale from "+display(0,measure)+" to "+display(max,measure)+(measure==="coverage"?"":" MVC fraction")));
    for (const r of rows) {
      const pair=schemes.map(s=>value(r.group[model][s],measure));
      const button=element("button","chart-row");button.type="button";button.dataset.key=r.key;
      button.setAttribute("aria-label",r.label+", one width "+display(pair[0],measure)+", width by cue phase "+display(pair[1],measure)+". Show counts.");
      const values=element("span","values");for(const v of pair) values.append(element("span","",display(v,measure)));
      button.append(element("span","row-name",r.label),track(pair[0],pair[1],max,measure==="coverage"),values);
      button.addEventListener("click",()=>{id("slice").value=r.key;drawDetails(rows);});chart.append(button);
    }
    const release=study.by_issue_phase.release[model].by_issue_phase;
    const total=study.overall[model].by_issue_phase;
    id("release-note").textContent="For this forecast, the phase-based band covered "+display(value(total,"coverage"),"coverage")+" across the full cue and "+display(value(release,"coverage"),"coverage")+" during release.";
    const decisions={
      descriptive_gain:"Across all cutoffs, the phase-based band was narrower, covered at least as many readings, and had a lower interval score.",
      width_coverage_tradeoff:"Across all cutoffs, the phase-based band was narrower and missed more readings.",
      no_prespecified_gain:"Across all cutoffs, the phase-based band did not achieve all three goals of reducing width, maintaining coverage and lowering the interval score."
    };
    id("decision").textContent=decisions[study.comparison[model].classification];
    drawDetails(rows);
  }
  try {
    if (!study || study.format!=="cemhsey-pinch-interval-public-v1" || study.nominal_coverage!==.9 ||
        study.protocol_sha256!=="44bc615272587c66b90a10be4208168501539d0ab3eb10a929040a80a3848082") throw Error("Missing bound aggregate");
    [study.overall,...Object.values(study.by_issue_phase),...Object.values(study.by_indexed_day)].forEach(validate);
    for (const key of ["model","measure","breakdown"]) id(key).addEventListener("change",draw);
    id("slice").addEventListener("change",()=>drawDetails(parts(id("breakdown").value)));draw();
  } catch (error) {
    for (const select of document.querySelectorAll("select")) select.disabled=true;
    id("definition").textContent="The aggregate could not be opened. The methods and aggregate data link below contains the numerical results.";
    id("chart").replaceChildren();id("decision").textContent="";id("support").textContent="";
  }
})();
