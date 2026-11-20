// SPDX-License-Identifier: CC0-1.0
const el = id => document.getElementById(id);
const n4 = value => value.toFixed(4).replace("-", "−");
const option = (value,label) => new Option(label,value);
const families = ["transformer","ridge","table"];
for (const [i, [code,name]] of areas.entries()) {
  el("region").add(option(code,name));
  const label = document.createElement("label");
  const box = document.createElement("input");
  box.type="checkbox"; box.id="area-"+code;
  box.checked=box.defaultChecked=i<6;
  label.append(box, name);
  el("mask-list").append(label);
}
function scenario() {
  return {
    digit:+el("digit").value, phase:+el("phase").value, tick:+el("tick").value,
    region:+el("region").value, low:+el("low").value, high:+el("high").value,
    mask: areas.map(([code]) => el("area-"+code).checked), unknown:el("unknown").checked
  };
}
function renderPrediction() {
  const s=scenario(), mode=el("mode").value, counts=el("unit").value==="counts";
  const prediction=predictStudy(s,mode);
  const values=fingers.map((_,i) => families.map(family => prediction[family][i]*(counts?gains[i]:1)));
  const area=areas.findIndex(([code]) => code===s.region);
  el("time-value").textContent=s.tick*40+" ms";
  el("low-value").textContent=s.low.toFixed(2).replace("-","−");
  el("high-value").textContent=s.high.toFixed(2).replace("-","−");
  el("low").disabled=el("high").disabled=!s.mask[area];
  el("band-note").textContent=s.mask[area]?
    "Zero is the area’s usual level. A value of one puts the last sample one calibration standard deviation above it.":
    "This area has no electrodes. Its signal inputs are zero. Add contacts below to change its rhythms.";
  el("covered").textContent="("+s.mask.filter(Boolean).length+"/8)";
  const max=Math.max(...values.flat());
  const step=counts?10:0.5;
  const limit=Math.max(step, Math.ceil(max/step)*step);
  const format=value => (counts?value.toFixed(2):value.toFixed(3));
  el("pred-rows").innerHTML=values.map((row,i) =>
    '<tr><th scope="row">'+fingers[i]+'</th>'+row.map(v=>'<td>'+format(v)+'</td>').join("")+'</tr>').join("");
  const chart=values.map((row,i) => '<div class="chart-row"><span>'+fingers[i]+'</span><div class="tracks">'+
    row.map((v,j)=>'<div class="bar '+families[j]+'" style="width:'+(v/limit*100)+'%"></div>').join("")+'</div></div>').join("");
  const ticks=[0,1,2,3,4].map(j => '<span>'+Number((limit*j/4).toFixed(3))+'</span>').join("");
  el("chart").innerHTML=chart+'<div class="axis">'+ticks+'</div>';
  const unit=counts?"invented sensor counts per 40 ms step":"personal calibration units";
  el("axis-caption").textContent="Average movement in "+unit+". All bars share the same scale.";
  el("pred-units").textContent="Predicted movement in "+unit;
  el("chart").setAttribute("aria-label","Estimated movement in "+unit+". In order of Transformer, ridge and cue table: "+
    values.map((row,i)=>fingers[i]+" "+row.map(format).join(", ")).join(". "));
  el("scale-note").textContent=counts?
    "These illustrative count estimates multiply each finger’s output by its invented gain. From thumb to little the gains are 12, 20, 15, 16 and 10 sensor counts per 40 ms step. A real person needs their own calibration.":
    "One unit is that finger’s early root-mean-square movement, with a minimum scale of one sensor count per 40 ms step. The unit measures unsigned sensor change. The clock table uses the same scale.";
}
const gainChecks=[
    ["Single trial · cue only","primary.cue"],["Single trial · cue and clock table","primary.table"],
    ["Single trial · wrong trial’s cortex","primary.earlier"],["Repeat difference · predict zero","repeat.zero"],
    ["Repeat difference · cue only","repeat.cue"],["Repeat difference · wrong trials’ cortex","repeat.earlier"]];

function updatePerson() {
  const person=study.people[+el("person").value];
  const others=study.people.filter(p=>p!==person).map(p=>p.id).join(", ");
  el("split-note").textContent=others+" supplied the training trials. "+person.id+" ("+person.code+
    ") supplied "+person.calibration+" early trials for personal calibration and "+person.trials+" later scored trials. "+
    "The numbers below count this person’s electrodes in each area.";
  el("fold-coverage").innerHTML=areas.map(([,name],i)=>'<span class="'+(person.coverage[i]?"":"absent")+'">'+
    name+' · '+person.coverage[i]+'</span>').join("");
  const idx=+el("person").value;
  el("person-gain-caption").textContent=person.id+" gains in personal calibration units. Positive values favor the correct cortex with cue.";
  el("person-gains").innerHTML=gainChecks.map(([label,key]) => '<tr><th scope="row">'+label+'</th>'+
    ["ridge","transformer"].map(f=>'<td>'+n4(study.contrasts[f+"."+key].person_means[idx])+'</td>').join("")+'</tr>').join("");
  el("unknown-count").textContent=person.unknown+" additional contacts had unknown region codes. All contributed to the common voltage reference. Presence of one or more set a single flag.";
}
function renderEvidence() {
  const metrics=["cue_table","ridge_aligned","transformer_aligned"];
  const scoreCells=scores => metrics.map(k=>'<td>'+n4(scores[k])+'</td>').join("");
  el("hero-control").textContent=n4(study.scores.cue_table);
  el("hero-model").textContent=n4(study.scores.transformer_aligned);
  el("fold-rows").innerHTML=study.people.map((p,i)=>{
    el("person").add(option(i,p.id+" ("+p.code+")"));
    return '<tr><th scope="row">'+p.id+' ('+p.code+')</th><td>'+p.trials+'</td><td>'+p.repeats+'</td>'+scoreCells(p.scores)+'</tr>';
  }).join("");
  const total=k=>study.people.reduce((sum,p)=>sum+p[k],0);
  el("fold-mean").innerHTML='<tr><th scope="row">All five</th><td>'+total("trials")+'</td><td>'+total("repeats")+'</td>'+scoreCells(study.scores)+'</tr>';
  const inputs=[["Cue only","cue"],["Cortex only","cortex"],["Cue and correct cortex","aligned"],["Cue and wrong trial’s cortex","earlier"]];
  el("primary-rows").innerHTML=inputs.map(([label,mode])=>'<tr><th scope="row">'+label+'</th><td>'+
    n4(study.scores["ridge_"+mode])+'</td><td>'+n4(study.scores["transformer_"+mode])+'</td></tr>').join("");
  el("gain-rows").innerHTML=gainChecks.map(([label,k])=>'<tr><th scope="row">'+label+'</th>'+
    ["ridge","transformer"].map(f=>{
      const c=study.contrasts[f+"."+k];
      return '<td>'+n4(c.mean)+' <span class="nowrap">['+c.interval.map(n4).join(", ")+']</span></td>';
    }).join("")+'</tr>').join("");
  updatePerson();
}
el("controls").addEventListener("input",renderPrediction);
el("controls").addEventListener("change",renderPrediction);
el("controls").addEventListener("reset",() => {
  el("mode").value="aligned"; el("unit").value="scaled";
  // The native reset restores the controls after the reset event has finished.
  setTimeout(renderPrediction, 0);
});
el("mode").addEventListener("change",renderPrediction);
el("unit").addEventListener("change",renderPrediction);
el("person").addEventListener("change",updatePerson);
renderEvidence();
renderPrediction();
