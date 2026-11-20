const $ = id => document.getElementById(id);
const study = JSON.parse($("study").textContent);
const pristine = "<!doctype html>\n"+document.documentElement.outerHTML;
const transferMethods = ["stride","raw","shared","scrambled"];
const names = {...labels, stride:"Repeat the stride",raw:"Measurements alone",shared:"Frozen encoder",scrambled:"Shuffled encoder"};
const shortNames = {prior_stride:"Repeat",ridge_residual:"Linear",transformer_residual:"Transformer",stride:"Repeat",raw:"Raw",shared:"Frozen",scrambled:"Shuffled"};
const angle = v => v.toFixed(1)+"°";
const signed = v => (v<0?"−":"+")+Math.abs(v).toFixed(1)+"°";
const degree = v => v.toFixed(3).replace("-","−")+"°";
const series = mode => mode === "transfer" ? transferMethods : methods;
let current = null, predictions = null, revealed = false, generation = 0;
const family = () => $("family").value;
const models = () => series(family());
function node(parent, tag, text) {
  const child = document.createElement(tag); child.textContent=text; parent.append(child); return child;
}
function row(parent, cells, active=false) {
  const tr = document.createElement("tr"); if(active) tr.className="active";
  cells.forEach((v,i) => {const cell=node(tr,i?"td":"th",v); if(!i) cell.scope="row";}); parent.append(tr);
}
function draw(side, leg, lo, hi, method, actual) {
  const svg = $(side+"-chart"), h=current.history, p=predictions.period_frames;
  svg.replaceChildren();
  function mark(tag, attrs, content) {
    const el = document.createElementNS("http://www.w3.org/2000/svg",tag);
    Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k,v));
    if(content!==undefined) el.textContent=content; svg.append(el);
  }
  const x = f => 46+(f+239)*431/254;
  const y = a => 152-(a-lo)*111/(hi-lo);
  const text=(px,py,label,anchor="middle",size=14)=>mark("text",{x:px,y:py,"text-anchor":anchor,"font-size":size,fill:"#304a4d"},label);
  const line=(x1,y1,x2,y2,stroke,width=1,dash="")=>mark("line",{x1,y1,x2,y2,stroke,"stroke-width":width,"stroke-dasharray":dash});
  mark("title",{},side+" knee. Forecast "+angle(predictions[method][leg])+". The estimated repeat interval is "+p+" frames.");
  mark("rect",{x:x(-59-p),y:39,width:x(-p)-x(-59-p),height:115,fill:"#d5e5d9"});
  mark("rect",{x:x(-59),y:39,width:x(0)-x(-59),height:115,fill:"#dae7f2","fill-opacity":.84});
  for (const tick of [lo,(lo+hi)/2,hi]) {
    line(x(-239),y(tick),x(15),y(tick),"#c6d1c9");text(40,y(tick)+5,tick.toFixed(0)+"°","end");
  }
  line(x(-p),27,x(0),27,"#4c6656",1.7);
  for(const f of [-p,0]) line(x(f),23,x(f),32,"#4c6656",1.7);
  text((x(-p)+x(0))/2,19,p+" frames");
  line(x(0),38,x(0),157,"#4a666f",1.2,"3 4");
  mark("polyline",{points:h.map((pair,i)=>x(i-239)+","+y(pair[leg])).join(" "),fill:"none",stroke:"#08665d","stroke-width":2.4});
  mark("circle",{cx:x(15-p),cy:y(h[239+15-p][leg]),r:4.5,fill:"#236a4d",stroke:"white","stroke-width":1.5});
  const fx=x(15),fy=y(predictions[method][leg]);
  mark("path",{d:"M "+fx+" "+(fy-6)+" l 6 6 -6 6 -6 -6 z",stroke:"#a64016",fill:"white","stroke-width":2.6});
  if (actual) {
    const yy=y(actual[leg]);
    mark("path",{d:"M "+(fx-5)+" "+(yy-5)+" l 10 10 m -10 0 l 10 -10",stroke:"#172f33",fill:"none","stroke-width":2.5});
  }
  for(const f of [-239,-180,-120,-60,0,15]) {
    line(x(f),154,x(f),159,"#607675");text(x(f),f===15?193:177,f===0?"0":(f>0?"+":"−")+Math.abs(f));
  }
  text(x(-125),196,"Frames from cutoff");
}
function render() {
  const mode=family(), method=$("method").value, selected=predictions[method];
  const {trial,index,cutoff}=current;
  const recorded=trial.mode==="recorded";
  const actual=revealed ? trial.pairs[current.futureIndex] : null;
  $("method").disabled=false; $("reveal").disabled=false; $("scrubbing").hidden=false;
  $("cut").max=trial.cuts.length-1; $("cut").value=index; $("cut").setAttribute("aria-valuetext","frame "+cutoff);
  $("frame-value").textContent="Frame "+cutoff;
  $("period-note").textContent="The closest earlier match ends "+predictions.period_frames+" frames back ("+(predictions.period_frames/60).toFixed(2)+" seconds). Both knees contribute to this estimate.";
  const values=current.history.flat().concat(selected,actual||[]);
  const low=Math.floor(Math.min(...values)/10)*10-5, high=Math.ceil(Math.max(...values)/10)*10+5;
  ["right","left"].forEach((side,i) => {$(side+"-angle").textContent=angle(selected[i]); draw(side,i,low,high,method,actual);});
  const base=predictions[mode==="transfer"?"stride":"prior_stride"];
  const end=cutoff+15-predictions.period_frames;
  $("frame-detail").textContent="Frame "+end+" supplies the copied pair for frame "+(cutoff+15)+". "+names[method]+
    (method==="prior_stride" || method==="stride" ? " uses that pair directly." : " changes it by "+signed(selected[0]-base[0])+" on the right and "+signed(selected[1]-base[1])+" on the left.");
  $("forecasts").replaceChildren();
  for(const m of models()) {
    const pair=predictions[m], cells=[names[m],...pair.map(angle)];
    if(actual) cells.push(...pair.map((v,i)=>angle(Math.abs(v-actual[i]))));
    row($("forecasts"),cells,method===m);
  }
  document.querySelectorAll(".err").forEach(el=>el.hidden=!revealed);
  $("later-key").hidden=!revealed; $("reveal").textContent=(revealed?"Hide ":"Reveal ")+(recorded?"recorded":"invented")+" angles";
  $("reveal").setAttribute("aria-expanded",String(revealed));
  $("observation").textContent=actual ? (recorded?"Recorded":"Invented")+" frame "+(cutoff+15)+" · right "+angle(actual[0])+", left "+angle(actual[1])+". The error columns show each forecast’s distance from these angles." :
    (recorded?"The later sensor-derived angles":"The invented continuation")+" at frame "+(cutoff+15)+" "+(recorded?"are hidden.":"is hidden.");
}
function choose(trial,index) {
  const input=atCutoff(trial,index);
  const result=family()==="transfer"?sharedKneeForecast(input.history,study.shared):forecast(input.history,study.weights);
  current=input; predictions=result; revealed=false; render();
}
function clear() {
  current=null; predictions=null; revealed=false;
  for(const id of ["right-chart","left-chart","forecasts","period-note","frame-detail","frame-value","observation"]) $(id).replaceChildren();
  for(const id of ["right-angle","left-angle"]) $(id).textContent="—";
  $("scrubbing").hidden=true; $("later-key").hidden=true;
  document.querySelectorAll(".err").forEach(el=>el.hidden=true);
  $("reveal").disabled=true; $("reveal").setAttribute("aria-expanded","false"); $("reveal").textContent="Reveal later angles"; $("method").disabled=true; $("mode").textContent="No walk selected";
}
function loadTrial(trial) {
  const recorded=trial.mode==="recorded";
  $("mode").textContent=recorded?"Recorded walk · S"+trial.member.subject:"Invented walk";
  $("status").dataset.error="false";
  $("status").textContent=recorded?"Verified original CSV · "+trial.member.path+" · 0.5 m/s. The file stays in this tab.":
    "A pair of changing waves supplies this walk. Open an original study CSV to compare against sensor-derived angles.";
  choose(trial,0);
}
function peopleTable() {
  const scores=study.scores[family()], axis=$("axis").value;
  const head=$("people-head");head.replaceChildren();
  for(const value of ["Walker","Windows",...models().map(m=>shortNames[m])]) node(head,"th",value).scope="col";
  $("people").replaceChildren(); for(const person of scores.people) {
    row($("people"),["S"+person.id,person.cutoffs.toLocaleString("en-US"),...models().map(m=>degree(person.mae[m][axis]))]);
  }
}
function setFamily() {
  const mode=family(), scores=study.scores[mode];
  const method=$("method");method.replaceChildren();
  for(const m of models()) method.add(new Option(names[m],m));
  method.value=mode==="transfer"?"shared":"transformer_residual";
  $("method-intro").textContent=mode==="transfer"?"All four rows start from the same earlier stride. Three models learn a correction using measurements alone, measurements with the frozen NeuroTranslate encoder, or measurements with a shuffled copy of that encoder.":
   "Each row predicts both knees at the same instant, 15 frames after the cutoff. The linear model learns a weighted correction. The Transformer learns which parts of the two strides to weigh together.";
  $("scores-intro").textContent="The fitted models learned from 39 walkers. Twelve other walkers supplied "+scores.cutoffs.toLocaleString("en-US")+" overlapping windows at 0.5 m/s. Each knee and each walker count equally in the mean absolute error below.";
  $("means").replaceChildren();
  for(const m of models()){const div=document.createElement("div");node(div,"strong",degree(scores.means[m]));node(div,"span",names[m]);$("means").append(div);}
  $("outcome").textContent=scores.outcome; $("comparisons").replaceChildren();
  for(const c of scores.comparisons) node($("comparisons"),"p",names[c.a]+" minus "+names[c.b]+": "+degree(c.mean)+". 95% interval "+degree(c.ci[0])+" to "+degree(c.ci[1])+". The first method was closer for "+c.wins+" walkers, tied for "+c.ties+" and farther away for "+c.losses+".");
  peopleTable();
  if(current) choose(current.trial,current.index);
}
$("family-choice").hidden=!study.shared;
$("family").addEventListener("change",setFamily); $("axis").addEventListener("change",peopleTable);
$("method").addEventListener("change",()=>{if(current)render();});
$("reveal").addEventListener("click",()=>{if(current){revealed=!revealed;render();}});
$("cut").addEventListener("input",()=>{if(current)choose(current.trial,Number($("cut").value));});
$("example").addEventListener("click",()=>{generation++;$("file").value="";loadTrial(inventedWalk());});
$("file").addEventListener("change",async event=>{
  const file=event.target.files[0]; if(!file)return;
  const stamp=++generation; clear(); $("status").dataset.error="false"; $("status").textContent="Checking the original file…";
  try {const trial=await openWalk(file,study.source);if(stamp===generation)loadTrial(trial);}
  catch(e){if(stamp===generation){clear();$("status").textContent=e.message;$("status").dataset.error="true";}}
  finally{if(stamp===generation)$("file").value="";}
});
$("save").addEventListener("click",()=>{
  const href=URL.createObjectURL(new Blob([pristine],{type:"text/html;charset=utf-8"}));
  const link=document.createElement("a");link.href=href;link.download="knee-stride.html";link.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
});
setFamily();loadTrial(inventedWalk());
