"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const guide = REACH_DATA.unitGuide, records = REACH_DATA.records;
  const svgNS = "http://www.w3.org/2000/svg";
  const colors = {past:"#a5b8c0", full:"#74ece0", measured:"#f8ca76", direct:"#e0a7eb"};
  const axes = ["X","Y","Z"];
  const bounds = {left:49, top:13, right:406, bottom:215};
  let current, history, model, edited;
  const format = (n, digits=2) => n.toFixed(digits).replace(/^-0\.00$/, "0.00");
  function svgNode(root, kind, attrs={}, content="") {
    const node = document.createElementNS(svgNS, kind);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (content) node.textContent = content;
    root.append(node);
    return node;
  }
  function label(root, x, y, text, attrs={}) {
    return svgNode(root, "text", {x,y,...attrs}, text);
  }
  function line(root, points, color, dash="") {
    return svgNode(root,"polyline",{points:points.map(point => point.join(",")).join(" "), fill:"none",
      stroke:color, "stroke-width":"2.6", "stroke-dasharray":dash, "stroke-linejoin":"round", "stroke-linecap":"round"});
  }
  function lastPoint(root, point, color, hollow=false) {
    svgNode(root,"circle",{cx:point[0],cy:point[1],r:3.5,fill:hollow?"#132f36":color,stroke:color,"stroke-width":2});
  }
  function niceStep(raw) {
    const unit = 10 ** Math.floor(Math.log10(raw)), step = raw / unit;
    return (step<=1 ? 1 : step<=2 ? 2 : step<=5 ? 5 : 10) * unit;
  }
  function ticks(lo, hi, step) {
    const start = Math.ceil(lo / step), end = Math.floor(hi / step), result = [];
    for (let n=start; n<=end; n++) result.push(n*step);
    return result;
  }
  function grid(root, horizontal, at, value) {
    const {left,top,right,bottom} = bounds;
    const attrs = horizontal ? {x1:left,y1:at,x2:right,y2:at} : {x1:at,y1:top,x2:at,y2:bottom};
    svgNode(root,"line",{...attrs,class:value===0?"zero":"grid"});
    const printed = String(Number(value.toFixed(3)));
    if (horizontal) label(root,left-7,at+4,printed,{"text-anchor":"end"});
    else label(root,at,bottom+18,printed,{"text-anchor":"middle"});
  }
  function yAxisTitle(root,name) {
    label(root,13,110,name,{transform:"rotate(-90 13 110)","text-anchor":"middle",class:"axis-title"});
  }
  function xyChart() {
    const [a,b] = $("plane").value.split(",").map(Number);
    const root = $("path"); root.replaceChildren();
    const anchor=history.pose[19], previous=history.pose.map(p => [(p[a]-anchor[a])*1000,(p[b]-anchor[b])*1000]);
    const project = path => [[0,0], ...path.map(p => [p[a]*1000,p[b]*1000])];
    const predicted = project(model.movement), measured = edited ? [] : project(current.movement);
    const all = previous.concat(predicted,measured);
    const xs = all.map(p=>p[0]), ys=all.map(p=>p[1]);
    const xrange=[Math.min(...xs), Math.max(...xs)], yrange=[Math.min(...ys), Math.max(...ys)];
    const {left,top,right,bottom}=bounds;
    const unitsPerPixel=Math.max((xrange[1]-xrange[0])/(right-left),(yrange[1]-yrange[0])/(bottom-top),.014)*1.15;
    const cx=(xrange[0]+xrange[1])/2, cy=(yrange[0]+yrange[1])/2;
    const x = d => (d-cx)/unitsPerPixel + (left+right)/2, y = d => (cy-d)/unitsPerPixel+(top+bottom)/2;
    const hx=(right-left)/2*unitsPerPixel, hy=(bottom-top)/2*unitsPerPixel;
    const step=niceStep(2*hy/4);
    ticks(cx-hx,cx+hx,step).forEach(v=>grid(root,false,x(v),v));
    ticks(cy-hy,cy+hy,step).forEach(v=>grid(root,true,y(v),v));
    label(root,225,255,"Hand " + axes[a] + " (mm)",{"text-anchor":"middle",class:"axis-title"});
    yAxisTitle(root,"Hand " + axes[b] + " (mm)");
    const onChart = curve => curve.map(([px,py])=>[x(px),y(py)]);
    line(root,onChart(previous),colors.past,"1 5");
    if (!edited) {
      const pts=onChart(measured);
      line(root,pts,colors.measured,"5 5");lastPoint(root,pts.at(-1),colors.measured,true);
    }
    const trace=onChart(predicted);
    line(root,trace,colors.full);lastPoint(root,trace.at(-1),colors.full);
    lastPoint(root,trace[0],"#f5faf6",true);
    const distance = p => Math.hypot(...p.slice(0,3)) * 1000;
    const endpoint = model.movement.at(-1);
    let caption = "The white ring marks the last known position. At 100 ms the forecast hand displacement is " + format(distance(endpoint)) + " mm.";
    if (!edited) caption += " The hand moved " + format(distance(current.movement.at(-1))) + " mm.";
    $("path-caption").textContent=caption;
    root.setAttribute("aria-label",axes[a] + " / " + axes[b] + " hand path in millimetres. " + caption);
  }
  function totals(matrix, unit) {
    return matrix.reduce((sum,row)=>sum+row[unit],0);
  }
  function spikeChart() {
    const root=$("counts"); root.replaceChildren();
    const unit=Number($("unit").value), [channel,sort]=guide[unit];
    const outcome=edited?null:current.delayed, {left,top,right,bottom}=bounds;
    const recorded=outcome?.map(row=>row[unit]), full=model.full?.map(row=>row[unit]), direct=model.direct?.map(row=>row[unit]);
    let caption;
    if (!recorded && !full) {
      label(root,215,111,"No count forecast on this warm-up reach.",{"text-anchor":"middle"});
      caption="The edited history has no observed outcome. This first training block has no primary count forecast.";
    } else {
      const max=Math.max(.1,...(recorded||[]),...(full||[]),...(direct||[]));
      const step=niceStep(max/4), upper=step*Math.ceil(max/step);
      const x=t=>left+(t-100)/100*(right-left), y=v=>bottom-(v/upper)*(bottom-top);
      [100,120,140,160,180,200].forEach(v=>grid(root,false,x(v),v));
      ticks(0,upper,step).forEach(v=>grid(root,true,y(v),v));
      if (recorded) recorded.forEach((v,j)=>{
        const center=x(105+10*j);
        svgNode(root,"rect",{x:center-5,y:y(v)-.5,width:10,height:Math.max(1.5,bottom-y(v)),fill:colors.measured});
      });
      for (const [curve,color,dash] of [[direct,colors.direct,"5 4"],[full,colors.full,""]]) {
        if (!curve) continue;
        const points=curve.map((v,j)=>[x(105+10*j),y(v)]);
        line(root,points,color,dash);
        points.forEach(([px,py])=>svgNode(root,"circle",{cx:px,cy:py,r:2.1,fill:color}));
      }
      label(root,225,255,"Time after cutoff (ms)",{"text-anchor":"middle",class:"axis-title"});
      yAxisTitle(root,"Spikes / 10 ms");
      if (full) {
        caption="Over 100 ms the model expects " + format(totals(model.full,unit)) + " spikes with the predicted path and " + format(totals(model.direct,unit)) + " from history alone.";
        if (outcome) caption += " Recorded total " + totals(outcome,unit) + ".";
      } else caption="This recording contains " + totals(outcome,unit) + " spikes. The first training block has no primary count forecast.";
    }
    $("count-caption").textContent=caption;
    root.setAttribute("aria-label","Later spikes on electrode " + channel + ", sort " + sort + ". " + caption);
  }
  function appendRow(parent, cells, header=false) {
    const tr=document.createElement("tr");
    for (const text of cells) {
      const td=document.createElement(header?"th":"td");
      if (header) td.scope="col";
      td.textContent=text;tr.append(td);
    }
    parent.append(tr);
  }
  function table(id,columns,rows,caption) {
    const el=$(id);el.replaceChildren();el.setAttribute("aria-label",caption);
    const head=el.createTHead(), body=el.createTBody();
    appendRow(head,columns,true);rows.forEach(row=>appendRow(body,row));
  }
  function tables() {
    const columns=["After last (ms)","Fit X","Fit Y","Fit Z"];
    if (!edited) columns.push("Obs X","Obs Y","Obs Z");
    const paths=model.movement.map((row,i)=>{
      const values=[10*(i+1),...row.slice(0,3).map(v=>format(v*1000))];
      if (!edited) values.push(...current.movement[i].slice(0,3).map(v=>format(v*1000)));
      return values;
    });
    table("path-table",columns,paths,"Forecast and available observed hand displacement in millimetres");
    const headers=["Electrode · sort"];
    if (model.full) headers.push("History + path","History only");
    if (!edited) headers.push("Recorded");
    const counts=model.full||!edited ? guide.map(([channel,sort],u)=>{
      const values=[channel+" · "+sort];
      if (model.full) values.push(format(totals(model.full,u)),format(totals(model.direct,u)));
      if (!edited) values.push(totals(current.delayed,u));
      return values;
    }) : [];
    table("count-table",headers,counts,"100-ms spike totals for each sorted unit");
    if (!counts.length) appendRow($("count-table").tBodies[0],["No count forecast on this edited warm-up reach."]);
  }
  function run() {
    current=records[$("split").value];
    const shift=Number($("shift").value), extra=Number($("extra").value), editUnit=Number($("edit-unit").value);
    edited=shift!==0||extra!==0;
    history={pose:current.pose.map(row=>row.slice()),spikes:current.spikes.map(row=>row.slice()),cue:current.cue};
    for (let j=0;j<5;j++) history.pose[15+j][0]+=shift/1000*(j+1)/5;
    history.spikes[19][editUnit]+=extra;
    model=ReachForecast.run(REACH_WEIGHTS,history,current.countSupported);
    $("identity").textContent="Sequence " + current.original + " · Go cue " + current.ordinal + " · Cutoff at source row " + current.cutoff;
    $("state").textContent=edited ? "Hypothetical history · The measurements you changed have no recorded future." :
      "Recorded history · " + (current.countSupported ? "Forecasts use fitted seed-17 Transformers." : "Training warm-up. The movement fit saw this sequence. The count comparison starts in the next block.");
    $("state").classList.toggle("edited",edited);
    $("history-key").textContent=edited&&shift!==0?"Edited hand history":"Earlier hand path";
    $("shift-value").value=shift+" mm"; $("extra-value").value=String(extra);
    document.querySelectorAll(".observation").forEach(el=>el.hidden=edited);
    document.querySelectorAll(".forecast-key").forEach(el=>el.hidden=!current.countSupported);
    xyChart();spikeChart();tables();
  }
  function restore() {$("shift").value="0";$("extra").value="0";run();}
  for (const [i,[channel,sort]] of guide.entries()) {
    for (const id of ["unit","edit-unit"]) $(id).add(new Option(channel+" · "+sort,String(i)));
  }
  $("unit").value=$("edit-unit").value="3";
  $("split").addEventListener("change",restore); $("restore").addEventListener("click",restore);
  $("plane").addEventListener("change",xyChart); $("unit").addEventListener("change",spikeChart);
  $("edit-unit").addEventListener("change",run);
  for(const id of ["shift","extra"]) $(id).addEventListener("input",run);
  if(location.protocol==="file:") $("download").hidden=true;
  run();
})();
