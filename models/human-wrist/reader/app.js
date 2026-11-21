"use strict";
(() => {
  const byId=id=>document.getElementById(id), ns="http://www.w3.org/2000/svg";
  let pack, simulated=true, loadTicket=0;
  const controls=["edit-right","edit-left","edit-voltage"];
  const referenceName=()=>simulated?"Simulated reference":"Supplied reference";
  const format=x=>x.toFixed(2);
  const pair=xy=>xy.map(format).join(", ");
  function resetEdits() {controls.forEach((id,i)=>{byId(id).value=i===2?100:0;});}
  function use(pkg,isDemo) {
    const validated=WristEngine.validate(pkg);
    pack=validated; simulated=isDemo;
    const select=byId("example"); select.replaceChildren();
    for (let i=0;i<pkg.cases.length;i++) select.add(new Option((isDemo?"Generated motion ":"Local case ")+(i+1),i));
    byId("origin").textContent=isDemo?"Simulated motion and simulated training data.":"Local package · fitted weights and case supplied by you.";
    byId("mobile-origin").textContent=isDemo?"Simulated example":"Locally imported example";
    resetEdits(); render();
  }
  function svgNode(root,tag,attributes,label) {
    const el=document.createElementNS(ns,tag);
    for (const [name,value] of Object.entries(attributes)) el.setAttribute(name,value);
    if(label!==undefined) el.textContent=label;
    root.append(el);
    return el;
  }
  function plot(id,data,h,comp,extent) {
    const svg=byId(id); svg.replaceChildren();
    const X=x=>151+100*x/extent, Y=y=>114+100*y/extent;
    const at=xy=>[X(xy[0]),Y(xy[1])];
    const stroke=(a,b,color,other={})=>svgNode(svg,"line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:color,...other});
    const text=(x,y,t,extra={})=>svgNode(svg,"text",{x,y,fill:"#526665","font-size":12,...extra},t);
    svgNode(svg,"title",{},id+" wrist: learned displacement "+pair(data.learned[h])+" pixels.");
    for (const tick of [-extent,0,extent]) {
      const color=tick===0?"#bdcac3":"#e1e7e1";
      stroke([X(tick),Y(-extent)],[X(tick),Y(extent)],color);
      stroke([X(-extent),Y(tick)],[X(extent),Y(tick)],color);
      text(X(tick),230,String(tick),{"text-anchor":"middle"});
      text(X(-extent)-4,Y(tick)+4,String(tick),{"text-anchor":"end"});
    }
    const past=data.history.map(at);
    svgNode(svg,"polyline",{points:past.map(p=>p.join(",")).join(" "),fill:"none",stroke:"#566461","stroke-width":3});
    svgNode(svg,"circle",{cx:X(0),cy:Y(0),r:3,fill:"#273c36"});
    const prior=at(data[comp][h]), learned=at(data.learned[h]);
    stroke([X(0),Y(0)],prior,"#98500b",{"stroke-width":2,"stroke-dasharray":"4 3"});
    stroke([X(0),Y(0)],learned,"#034d9d",{"stroke-width":2});
    svgNode(svg,"circle",{cx:learned[0],cy:learned[1],r:5,fill:"#034d9d"});
    const [px,py]=prior;
    svgNode(svg,"polygon",{points:[[px,py-7],[px+7,py],[px,py+7],[px-7,py]].map(p=>p.join(",")).join(" "),fill:"none",stroke:"#98500b","stroke-width":2});
    if(data.reference) {
      const [x,y]=at(data.reference[h]);
      svgNode(svg,"polygon",{points:[[x,y-6],[x-6,y+5],[x+6,y+5]].map(p=>p.join(",")).join(" "), fill:"#07715e",stroke:"#fff","stroke-width":1});
    }
  }
  function trace(id, values, duration, units, showDots) {
    const svg=byId(id);svg.replaceChildren();
    const lo=Math.min(...values), hi=Math.max(...values), span=Math.max(hi-lo,1e-9);
    const left=42, right=326, top=21, bottom=110;
    const points=values.map((y,i)=>[left+(right-left)*i/(values.length-1),bottom-(bottom-top)*(y-lo)/span]);
    svgNode(svg,"title",{},values.length+" samples, from "+lo.toFixed(2)+" to "+hi.toFixed(2)+" "+units);
    for(const y of [top,bottom])svgNode(svg,"line",{x1:left,y1:y,x2:right,y2:y,stroke:"#c7d3ce"});
    svgNode(svg,"polyline",{points:points.map(p=>p.join(",")).join(" "),fill:"none",stroke:showDots?"#04599c":"#07715e","stroke-width":2});
    if(showDots)for(const [x,y] of points)svgNode(svg,"circle",{cx:x,cy:y,r:2.8,fill:"#04599c"});
    for(const [x,y,txt,anchor] of [[left-4,top+4,hi.toFixed(1),"end"],[left-4,bottom+4,lo.toFixed(1),"end"],[left,bottom+19,"−"+duration+" ms","start"],[right,bottom+19,"0 ms","end"]]){
      svgNode(svg,"text",{x,y,fill:"#516565","font-size":11,"text-anchor":anchor},txt);
    }
    svgNode(svg,"text",{x:left,y:13,fill:"#516565","font-size":11},units);
  }
  function drawClocks() {
    if(!pack || !byId("clock-panel").open)return;
    const c=pack.cases[+byId("example").value];
    const side=+byId("clock-hand").value, channel=+byId("clock-contact").value;
    const drift=+byId(side===0?"edit-right":"edit-left").value, gain=(+byId("edit-voltage").value)/100;
    const wrist=c.pose_px.map((frame,t)=>frame[side][0][0]+drift*t/14);
    trace("pose-clock",wrist.map(x=>x-wrist[14]),467,"px",true);
    trace("voltage-clock",c.ecog_uv.map(row=>row[channel]*gain),498,"µV",false);
  }
  function tableRow(parent,items,head=false) {
    const row=parent.insertRow();
    for (const value of items) {
      const cell=document.createElement(head?"th":"td");cell.textContent=value;row.append(cell);
    }
  }
  function render() {
    const edit=controls.map(id=>Number(byId(id).value));edit[2]/=100;
    byId("r-val").textContent=edit[0]+" px";byId("l-val").textContent=edit[1]+" px";byId("v-val").textContent=edit[2].toFixed(2)+"×";
    drawClocks();
    const c=pack.cases[Number(byId("example").value)], comp=byId("control").value;
    const h=Number(byId("horizon").value);
    const state=WristEngine.predict(pack.weights,c,byId("treatment").value,byId("modality").value,edit);
    const largest=Math.max(1,...state.flatMap(d=>[...d.history,d.learned[h],d[comp][h],...(d.reference?[d.reference[h]]:[])].flat().map(Math.abs)));
    const mag=10**Math.floor(Math.log10(largest));
    const extent=Math.max(1,Math.ceil(largest/mag)*mag);
    plot("right",state[0],h,comp,extent);plot("left",state[1],h,comp,extent);
    const has=!!state[0].reference;
    byId("ref-key").hidden=!has;byId("ref-name").textContent=referenceName();
    byId("reference-state").textContent=has?"":edit[0]!==0||edit[1]!==0||edit[2]!==1?"Hypothetical inputs. No reference exists for this edit.":"The local package contains earlier inputs only.";
    const head=byId("number-head"),body=byId("number-rows");
    head.replaceChildren();body.replaceChildren();
    tableRow(head,["Wrist","Frames","Learned Δx, Δy","Comparison Δx, Δy",...(has?[referenceName()+" Δx, Δy","Error (px)"]:[])],true);
    for (const [s,d] of state.entries()) for (const [t,horizon] of [8,15].entries()) {
      const e=has?Math.hypot(...d.learned[t].map((x,j)=>x-d.reference[t][j])):null;
      tableRow(body,[s===0?"Right":"Left",horizon,pair(d.learned[t]),pair(d[comp][t]),...(has?[pair(d.reference[t]),format(e)]:[])]);
    }
  }
  function scores() {
    const element=byId("group-result"), data=globalThis.WristScores;
    if (!data) {element.textContent="The second-day comparison is awaiting scoring.";return;}
    for (const line of data.summary) {let p=document.createElement("p");p.textContent=line;element.append(p);}
    for(const section of data.tables) {
      const title=document.createElement("h3");title.textContent=section.title;element.append(title);
      const p=document.createElement("p");p.textContent=section.description;element.append(p);
      const wrapper=document.createElement("div");wrapper.className="table-wrap";element.append(wrapper);
      const table=document.createElement("table");wrapper.append(table);tableRow(table.createTHead(),section.columns,true);
      const body=table.createTBody();for (const row of section.rows) tableRow(body,row);
    }
    for (const line of data.notes) {let p=document.createElement("p");p.textContent=line;element.append(p);}
  }
  for (const id of ["example","treatment","modality","control","horizon"]) byId(id).addEventListener("change",()=>{
    if (id==="example") resetEdits();render();
  });
  for(const id of controls) byId(id).addEventListener("input",render);
  byId("restore").addEventListener("click",()=>{resetEdits();render();});
  byId("use-demo").addEventListener("click",()=>{loadTicket++;byId("package").value="";use(WristDemo,true);byId("load-status").textContent="Simulated examples loaded.";});
  byId("package").addEventListener("change",async event=>{
    const file=event.target.files[0],ticket=++loadTicket;
    if(!file)return;
    try{
      if(file.size>2*1024*1024)throw Error("The file exceeds 2 MiB.");
      const candidate=JSON.parse(await file.text());
      if(ticket!==loadTicket)return;
      use(candidate,false);byId("load-status").textContent="Local package loaded. Your file stays in this tab.";
    }catch(error){
      if(ticket===loadTicket)byId("load-status").textContent="Could not open this package. "+(error instanceof SyntaxError?"The file must contain JSON.":error.message);
    }finally{if(ticket===loadTicket)byId("package").value="";}
  });
  for(const [i,n] of [0,9,18,27,36,45,54,63].entries())byId("clock-contact").add(new Option("Grid contact "+n,i));
  byId("clock-panel").addEventListener("toggle",drawClocks);
  for(const id of ["clock-hand","clock-contact"])byId(id).addEventListener("change",drawClocks);
  if(location.protocol==="file:")byId("download").hidden=true;
  scores();use(WristDemo,true);
})();
