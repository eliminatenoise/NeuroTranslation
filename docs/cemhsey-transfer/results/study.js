"use strict";
(() => {
  const data = globalThis.PINCH_TARGET_RESULTS;
  const el = id => document.getElementById(id);
  const names = {
    persistence: "Current force carried forward", scheduled_cue: "Scheduled cue alone",
    persistence_plus_cue_change: "Current force + cue change",
    history_phase_frozen: "Force history and phase · frozen", history_phase_adjusted: "Force history and phase · target adjusted",
    history_phase_adapted: "Force history and phase · practice adapted", history_phase_paired_grid_frozen: "Five grids · frozen",
    history_phase_paired_grid_adjusted: "Five grids · target adjusted", history_phase_paired_grid_adapted: "Five grids · practice adapted"
  };
  const phases = {overall:"Whole trial",initial_rest:"Initial rest",ramp_up:"Ramp up",hold:"Hold",release:"Release",final_rest:"Final rest"};
  const targets = [10,30,50];
  const models = Object.keys(names);
  const contrasts = [
    ["history_phase_paired_grid_adapted","history_phase_paired_grid_adjusted","Five grids: practice versus target adjustment"],
    ["history_phase_paired_grid_adjusted","history_phase_paired_grid_frozen","Five grids: target adjustment versus frozen"],
    ["history_phase_adapted","history_phase_adjusted","Force history: practice versus target adjustment"],
    ["history_phase_adjusted","history_phase_frozen","Force history: target adjustment versus frozen"],
    ["history_phase_paired_grid_adjusted","history_phase_adjusted","Target adjusted: grids versus force history"],
    ["history_phase_paired_grid_adapted","history_phase_adapted","Practice adapted: grids versus force history"],
    ["history_phase_paired_grid_adjusted","persistence_plus_cue_change","Target-adjusted grids versus current force + cue change"],
    ["history_phase_paired_grid_adapted","persistence_plus_cue_change","Practice-adapted grids versus current force + cue change"],
    ["history_phase_adjusted","persistence_plus_cue_change","Target-adjusted history versus current force + cue change"],
    ["history_phase_adapted","persistence_plus_cue_change","Practice-adapted history versus current force + cue change"]
  ];
  function tag(name,text) {const n=document.createElement(name);if(text!==undefined)n.textContent=text;return n;}
  function selectOption(v,t){const n=tag("option",t);n.value=v;return n;}
  function svgTag(tag,attrs){const n=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;}
  const signed=n=>n===0?"0":(n>0?"+":"−")+Number(Math.abs(n).toPrecision(4)).toString();
  const plural=(n,unit)=>n+" "+unit+(n===1?"":"s");
  const rowFor=(target,phase)=>data.results.find(r=>r.target_percent_mvc===target&&r.phase===phase);
  const contrastFor=(row,pair)=>row.contrasts.find(c=>c.candidate===pair[0]&&c.comparator===pair[1]);
  function drawRange(c,extent){
    const x=value=>((value/extent+1)*50)+"%";
    const svg=svgTag("svg",{"aria-hidden":"true",width:"100%",height:34});
    svg.append(svgTag("line",{x1:0,x2:"100%",y1:17,y2:17,stroke:"#c5d0c8"}),
      svgTag("line",{x1:"50%",x2:"50%",y1:0,y2:34,stroke:"#4c5d52","stroke-dasharray":"3 3"}),
      svgTag("line",{x1:x(c.mae_gain_min),x2:x(c.mae_gain_max),y1:17,y2:17,stroke:"#516e64","stroke-width":3}));
    for(const end of [c.mae_gain_min,c.mae_gain_max]) svg.append(svgTag("line",{x1:x(end),x2:x(end),y1:12,y2:22,stroke:"#516e64","stroke-width":2}));
    svg.append(svgTag("circle",{cx:x(c.mae_gain_mean),cy:17,r:5.5,fill:c.mae_gain_mean<0?"#a25128":"#1b6a5a",stroke:"#213831","stroke-width":1.3}));return svg;
  }
  function render(){
    const phase=el("phase").value,target=Number(el("target").value),pair=contrasts[Number(el("comparison").value)];
    const rows=targets.map(q=>rowFor(q,phase));const changes=rows.map(r=>contrastFor(r,pair));const selected=targets.indexOf(target);
    const c=changes[selected],row=rows[selected];const max=Math.max(...changes.flatMap(v=>[Math.abs(v.mae_gain_min),Math.abs(v.mae_gain_max),Math.abs(v.mae_gain_mean)]));
    const extent=max>0?max*1.12:1;
    const panel=el("plot");panel.replaceChildren();const axis=tag("div");axis.className="plot-layout axis";const scale=tag("span");scale.className="axis-width";
    const mean=tag("span","Mean gain");mean.className="unit-mean";
    if(max>0)scale.append(tag("span",signed(-extent)),tag("span","0"),tag("span",signed(extent)));else scale.append(tag("span","All published changes equal zero"));
    axis.append(tag("span","Target"),scale,mean);panel.append(axis);
    for(const [i,ch] of changes.entries()){
      const q=targets[i],btn=tag("button");btn.type="button";btn.className="plot-row plot-layout";btn.setAttribute("aria-pressed",String(q===target));btn.dataset.target=String(q);
      btn.setAttribute("aria-label",q+"% MVC. Mean gain "+signed(ch.mae_gain_mean)+", observed range "+signed(ch.mae_gain_min)+" to "+signed(ch.mae_gain_max)+". Show these trials.");
      const value=tag("span",signed(ch.mae_gain_mean));value.className="unit-mean";btn.append(tag("strong",q+"% MVC"),drawRange(ch,extent),value);
      btn.addEventListener("click",()=>{el("target").value=q;render();el("plot").querySelector('[data-target="'+q+'"]').focus({preventScroll:true});});panel.append(btn);
    }
    el("witness").textContent=target+"% MVC · "+phases[phase]+". Mean gain in MAE (comparator minus candidate) "+signed(c.mae_gain_mean)+" MVC fraction. The four individual changes ranged from "+signed(c.mae_gain_min)+" to "+signed(c.mae_gain_max)+". Lower error for "+c.wins+", equal error for "+c.ties+", higher error for "+c.losses+".";
    el("support").textContent=target+"% MVC · "+phases[phase]+" · "+row.issues.toLocaleString("en")+" cutoffs across "+plural(row.trials,"trial")+", "+plural(row.participants,"person").replace("persons","people")+" and one indexed day.";
    const body=el("rows");body.replaceChildren();
    for(const model of models){
      const v=row.arms[model],tr=tag("tr"),th=tag("th",names[model]);th.scope="row";tr.append(th);
      for(const n of [v.mae.toFixed(6),v.rmse.toFixed(6),signed(v.signed_error),(100*v.target_relative_mae).toFixed(2)+"%"])tr.append(tag("td",n));
      body.append(tr);
    }
  }
  try{
    if(!data||data.format!=="cemhsey-pinch-intensity-public-v1"||data.protocol_sha256!=="60388f4aab4daa9591904aef311e0b1f7955e4cb875adb8b8fdde05a5f0f4132"||data.results.length!==18)throw Error("Missing recorded study");
    for(const p of Object.keys(phases))for(const q of targets){const r=rowFor(q,p);if(!r||r.participants!==4||r.trials!==4||!Number.isSafeInteger(r.issues)||!contrasts.every(c=>contrastFor(r,c)))throw Error("Incomplete study cells");}
    el("phase").replaceChildren(...Object.entries(phases).map(([key,value])=>selectOption(key,value)));
    el("comparison").replaceChildren(...contrasts.map((v,i)=>selectOption(i,v[2])));
    for(const k of ["phase","comparison","target"])el(k).addEventListener("change",render);render();
  }catch{for(const node of document.querySelectorAll("select"))node.disabled=true;el("witness").textContent="The comparison could not be opened. Use the two CSV tables or the study report below.";}
})();
