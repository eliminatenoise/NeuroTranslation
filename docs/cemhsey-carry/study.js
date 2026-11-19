"use strict";
(() => {
  const results = window.PINCH_CARRY_STUDY;
  const phases = {overall:"Whole trial", initial_rest:"Initial rest", ramp_up:"Rise", hold:"Hold", release:"Release", final_rest:"Final rest"};
  const parents = {history_phase:"Force history", history_phase_paired_grid:"Five grids"};
  const variants = {frozen:"original forecast", adjusted:"cue adjustment", carried:"earlier practice", same_day:"fresh practice"};
  const control = "persistence_plus_cue_change";
  const names = {persistence:"Current force", scheduled_cue:"Scheduled target", [control]:"Current force + cue change"};
  for (const [parent, name] of Object.entries(parents)) {
    for (const [variant, label] of Object.entries(variants)) names[parent+"_"+variant] = name+" · "+label;
  }
  const comparisons = [];
  function add(candidate, comparator, label) { comparisons.push({candidate, comparator, label}); }
  for (const parent of ["history_phase_paired_grid","history_phase"]) {
    for (const [candidate, comparator] of [["carried","same_day"],["carried","adjusted"],["same_day","adjusted"],["adjusted","frozen"]]) {
      add(parent+"_"+candidate, parent+"_"+comparator, parents[parent]+" · "+variants[candidate]+" versus "+variants[comparator]);
    }
    for (const variant of ["adjusted","carried","same_day"]) add(parent+"_"+variant, control, parents[parent]+" · "+variants[variant]+" versus current force + cue change");
  }
  for (const variant of ["adjusted","carried","same_day"]) add("history_phase_paired_grid_"+variant,"history_phase_"+variant,"Five grids versus force history · "+variants[variant]);
  const byId = id => document.getElementById(id);
  function node(name, content) { const item = document.createElement(name); if(content!==undefined)item.textContent=content; return item; }
  function option(value, label) {const item=node("option",label);item.value=value;return item;}
  function ink(name, values) {
    const item=document.createElementNS("http://www.w3.org/2000/svg",name);
    for(const [k,v] of Object.entries(values)) item.setAttribute(k,v);
    return item;
  }
  const pp = value => Number((100*Math.abs(value)).toPrecision(4)).toString();
  const signed = value => value===0?"0":(value<0?"−":"+")+pp(value);
  function rangePlot(change, extent) {
    const x = value => (50+50*value/extent)+"%";
    const line = (x1,x2,y1,y2,stroke,width) => ink("line",{x1,x2,y1,y2,stroke,"stroke-width":width});
    const svg=ink("svg",{width:"100%",height:36,"aria-hidden":"true"});
    svg.append(line(0,"100%",18,18,"#c1cdca",1),line("50%","50%",0,36,"#758782",1),
      line(x(change.mae_gain_min),x(change.mae_gain_max),18,18,"#3e5d57",3));
    for(const edge of [change.mae_gain_min,change.mae_gain_max]) svg.append(line(x(edge),x(edge),13,23,"#3e5d57",2));
    svg.append(ink("circle",{cx:x(change.mae_gain_mean),cy:18,r:5,fill:change.mae_gain_mean>=0?"#17685a":"#a8502c",stroke:"#233d38","stroke-width":1.2}));
    return svg;
  }
  const rowFor=(target,phase)=>results.results.find(row=>row.target_percent_mvc===target&&row.phase===phase);
  const contrastFor=(row,pair)=>row.contrasts.find(c=>c.candidate===pair.candidate&&c.comparator===pair.comparator);
  function render() {
    const target=Number(byId("target").value), phase=byId("phase").value, pair=comparisons[Number(byId("comparison").value)];
    const rows=Object.keys(phases).map(key=>rowFor(target,key));
    const changes=rows.map(row=>contrastFor(row,pair));
    const maximum=Math.max(...changes.flatMap(c=>[Math.abs(c.mae_gain_min),Math.abs(c.mae_gain_max),Math.abs(c.mae_gain_mean)]));
    const extent=maximum>0?maximum*1.12:1;
    const chart=byId("chart");chart.replaceChildren();
    const axis=node("div");axis.className="axis";const scale=node("span");scale.className="scale";
    const left=node("span",maximum?signed(-extent):"");left.className="extent";
    const right=node("span",maximum?signed(extent):"");right.className="extent";
    scale.append(left,node("span","0"),right);
    const meanHeader=node("span","Mean gain");meanHeader.className="mean";axis.append(node("span","Phase"),scale,meanHeader);chart.append(axis);
    for(const [i,c] of changes.entries()){
      const key=rows[i].phase;const button=node("button");button.type="button";button.className="plot-row";button.dataset.phase=key;
      button.setAttribute("aria-pressed",String(key===phase));button.setAttribute("aria-label",phases[key]+". Mean gain "+signed(c.mae_gain_mean)+" percentage points of MVC, range "+signed(c.mae_gain_min)+" to "+signed(c.mae_gain_max)+". Show scores.");
      const value=node("span",signed(c.mae_gain_mean));value.className="mean";
      button.append(node("strong",phases[key]),rangePlot(c,extent),value);
      button.addEventListener("click",()=>{byId("phase").value=key;render();chart.querySelector('[data-phase="'+key+'"]').focus({preventScroll:true});});
      chart.append(button);
    }
    const selected=rowFor(target,phase), c=contrastFor(selected,pair);
    byId("range").textContent=names[pair.candidate]+" compared with "+names[pair.comparator]+" at "+target+"% MVC, "+phases[phase].toLowerCase()+". The mean gain was "+signed(c.mae_gain_mean)+" percentage points of MVC. The four individual gains ranged from "+signed(c.mae_gain_min)+" to "+signed(c.mae_gain_max)+". Lower error for "+c.wins+", equal error for "+c.ties+", higher error for "+c.losses+".";
    byId("support").textContent=phases[phase]+" at "+target+"% MVC. The four second attempts contributed "+selected.issues.toLocaleString("en")+" forecast cutoffs.";
    let order=Object.keys(names);
    if(byId("order").value==="mae")order.sort((a,b)=>selected.arms[a].mae-selected.arms[b].mae);
    const body=byId("scores");body.replaceChildren();
    for(const model of order){
      const score=selected.arms[model],tr=node("tr"),th=node("th",names[model]);th.scope="row";tr.dataset.arm=model;tr.append(th);
      for(const v of [score.mae,score.rmse,score.signed_error,score.target_relative_mae])tr.append(node("td",(100*v).toFixed(5)));
      body.append(tr);
    }
  }
  try {
    if(!results||results.format!=="cemhsey-pinch-carry-public-v1"||results.protocol_sha256!=="38c0551d464f5bbc3d2c4e8a712dfb47fe2f212f7527428c3ec829ad772eac71"||results.results.length!==18)throw Error("Study data");
    for(const q of [10,30,50]) for(const p of Object.keys(phases)){
      const row=rowFor(q,p);
      if(!row||row.participants!==4||row.trials!==4||!Number.isSafeInteger(row.issues)||!Object.keys(names).every(k=>row.arms[k])||!comparisons.every(pair=>contrastFor(row,pair)))throw Error("Incomplete study data");
    }
    byId("comparison").replaceChildren(...comparisons.map((p,i)=>option(i,p.label)));
    byId("phase").replaceChildren(...Object.entries(phases).map(([id,label])=>option(id,label)));
    for(const id of ["target","comparison","phase","order"]){const c=byId(id);c.disabled=false;c.addEventListener("change",render);}
    render();
  }catch{
    for(const select of document.querySelectorAll("select"))select.disabled=true;
    byId("range").textContent="The chart could not be opened. The two CSV downloads and the study report contain the full results.";
  }
})();
