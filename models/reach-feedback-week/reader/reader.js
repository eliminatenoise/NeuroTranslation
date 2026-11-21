"use strict";
(() => {
  const byId = id => document.getElementById(id);
  let lastMotor = null;
  const fmt = x => Number(x).toLocaleString("en", {maximumFractionDigits: 3, minimumFractionDigits: 3});
  const labels = {primary:"All exported events",zero:"Unsorted events",positive:"Positive sorts",late:"Positive sorts with recent spikes"};
  const pop = () => byId("population").value;
  const currentCase = () => WEEK_CASES[Number(byId("case").value)];
  const contactList = () => pop() === "late" ? WEEK_MODEL.late.contacts : WEEK_MODEL.populations[pop()].contacts;
  function options(select, values, names) {
    select.replaceChildren(...values.map((v, j) => new Option(names[j], v)));
  }
  function table(node, title, columns, rows) {
    node.replaceChildren();
    node.createCaption().textContent = title;
    const heading = node.createTHead().insertRow();
    for (const name of columns) {
      const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = name; heading.append(cell);
    }
    const body = node.createTBody();
    for (const values of rows) {
      const row = body.insertRow();
      for (const [j, v] of values.entries()) {
        const cell = document.createElement(j === 0 ? "th" : "td");
        if (j === 0) cell.scope = "row"; cell.textContent = v; row.append(cell);
      }
    }
  }
  function svg(name, props, firstText = null) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [k,v] of Object.entries(props)) el.setAttribute(k, v);
    if (firstText !== null) el.textContent = firstText;
    return el;
  }
  function pathChart(col, history, future, velocity, adapter, edited) {
    const chart = byId("path");
    // Positions are stored in metres (arm landmarks) or centimetres (handle); show both in millimetres, like the sliders.
    const unit = "mm", scale = col < 6 ? 1000 : 10;
    const series = [{label:edited ? "Path input" : "Measured",cls:"measured",color:"#162d35",start:-20,values:[...history,...future]}];
    series.push({label:"Constant velocity", cls:"velocity",color:"#84500a",dash:"7 4",start:-1,values:[history[19], ...velocity]});
    if (adapter) series.push({label:"Fitted movement model",cls:"adapter",color:"#62559d",dash:"2 3",start:-1,values:[history[19],...adapter]});
    const legend = byId("legend");legend.replaceChildren();
    for (const s of series) {const lab=document.createElement("span");lab.textContent=s.label;lab.className=s.cls;legend.append(lab);}
    const values = series.flatMap(s => s.values.map(v => v[col] * scale));
    const width = Math.max(228, chart.getBoundingClientRect().width || 640);
    const left = 61, right = 15, top = 23, bottom = 170;
    let lo = Math.min(...values), hi = Math.max(...values);
    const pad = Math.max((hi-lo)*.12,.1);lo-=pad;hi+=pad;
    const X = t => left+(t+20)*(width-left-right)/29;
    const Y = v => bottom-(v-lo)*(bottom-top)/(hi-lo);
    chart.setAttribute("viewBox", `0 0 ${width} 218`);
    chart.replaceChildren(svg("title",{id:"path-title"},"Position along the selected coordinate"),
      svg("desc",{id:"path-description"},`${series.map(s=>s.label).join(", ")}. Values in ${unit}. All ten forward samples appear in the table below.`),
      svg("rect",{x:X(0),y:top,width:X(9)-X(0),height:bottom-top,fill:"#e7f1ed"}));
    chart.append(svg("text",{x:2,y:13},`Position (${unit})`));
    for(let j=0;j<3;j++) {
      const value = lo + j*(hi-lo)/2, y=Y(value);
      chart.append(svg("line",{x1:left,x2:X(9),y1:y,y2:y,stroke:"#cad7d4"}));
      chart.append(svg("text",{x:left-5,y:y+4,"text-anchor":"end"},value.toFixed(1)));
    }
    chart.append(svg("line",{x1:X(0),x2:X(0),y1:top,y2:bottom,stroke:"#517b7d","stroke-dasharray":"3 3"}));
    for(const t of [-20,-10,0,9]) chart.append(svg("text",{x:X(t),y:bottom+19,"text-anchor":"middle"},String(t*10).replace("-","−")));
    chart.append(svg("text",{x:(left+X(9))/2,y:211,"text-anchor":"middle"},"ms from first forecast"));
    for(const s of series) {
      chart.append(svg("polyline",{points:s.values.map((v,j)=>[X(s.start+j),Y(v[col]*scale)].join(",")).join(" "),
        fill:"none",stroke:s.color,"stroke-width":s.cls==="measured"?2.8:2.3,"stroke-linecap":"round","stroke-dasharray":s.dash||"none"}));
    }
    const lab=byId("landmark").selectedOptions[0].text, axis=byId("axis").value;
    byId("path-note").textContent = adapter
      ? "The fitted model forecasts ten positions from earlier motion, go cues and contact counts. Its line averages three frozen movement forecasts. The constant-velocity forecast extends the slope over the last five old samples."
      : "The constant-velocity forecast extends the slope over the last five old samples. Both lines use the current path inputs.";
    table(byId("path-values"),`${lab} · ${axis} coordinate · ${unit}. The old history ends at −10 ms. The ten new samples span 0–90 ms.`,
      ["Time (ms)",edited?"Path input":"Measured","Constant velocity",...(adapter?["Fitted model"]:[])],
      [...history.map((v,j)=>[(j-20)*10,(v[col]*scale).toFixed(2),"—",...(adapter?["—"]:[])]),
       ...future.map((v,j)=>[j*10,(v[col]*scale).toFixed(2),(velocity[j][col]*scale).toFixed(2),...(adapter?[(adapter[j][col]*scale).toFixed(2)]:[])])]);
  }
  function countsChart(rec, arm, edited) {
    const mode = pop(), late = mode === "late", contacts=contactList();
    const observed=rec.measured[late?"positive":mode];
    const baseLabel=late?"Stale position + recent spikes":"Earlier forecast";
    const data=[{name:baseLabel,cls:"base",v:arm.earlier},{name:"Movement update",cls:"update",v:arm.update}];
    if (arm.wrong) data.push({name:"Other reach",cls:"wrong",v:arm.wrong});
    if(!edited) data.push({name:"Recorded count",cls:"observed",v:observed});
    const c=Number(byId("contact").value), ci=contacts.indexOf(c);
    const chart=byId("count-figure");chart.replaceChildren();
    const high=Math.max(1,...data.map(s=>s.v[ci]));
    for (const s of data) {
      const row=document.createElement("div");row.className="bar-row "+s.cls;
      const n=document.createElement("span");n.textContent=s.name;
      const track=document.createElement("span");track.className="track";track.setAttribute("aria-hidden","true");
      const bar=document.createElement("span");bar.className="bar";bar.style.width=100*s.v[ci]/high+"%";track.append(bar);
      const val=document.createElement("b");val.textContent=s.cls==="observed"?s.v[ci]:fmt(s.v[ci]);row.append(n,track,val);chart.append(row);
    }
    byId("donor").textContent=arm.wrong
      ? `The other-reach control uses the movement from sequence ${rec.donorOriginal}, the nearest earlier eligible sequence in this block and workspace with the same go ordinal. All earlier inputs still belong to the selected reach.`
      : "Other-reach control unavailable. This is the first eligible window here at this go ordinal. There is no earlier matching sequence to borrow from.";
    byId("count-explanation").textContent = late
      ? "This separate day-one fit uses the selected contact’s own positive-sort counts through 90 ms. Both arms therefore see the recent spikes. The movement update also takes hand, elbow and handle displacement at 40 and 90 ms. Each number is an expected event count for the following 100 ms."
      : "The earlier model reads 200 ms of movement, cortical counts and go cues. The second model also sees how far the arm and handle ended from the constant-velocity forecast. Both predict the same 100 ms of cortical activity. The expectation can be fractional even though the electrode records whole events.";
    table(byId("all-counts"),`${labels[mode]} · events per contact in the next 100 ms`,["Contact",...data.map(s=>s.name)],
      contacts.map((contact,j)=>[contact,...data.map(s=>s.cls==="observed"?s.v[j]:fmt(s.v[j]))]));
  }
  function results() {
    const s=WEEK_RESULTS;
    byId("verdict").textContent=s.verdict;
    byId("sensitivity").textContent="The full study also reports independent original-sequence bootstrap intervals and contact-specific and movement results. One held day from one animal limits the inference across dates.";
    const node=byId("result-tables");node.replaceChildren();
    for(const [mode,summary] of Object.entries(s.counts)) {
      const open=mode==="primary";
      const el=document.createElement(open?"div":"details");
      el.className="result-block";const title=document.createElement(open?"h3":"summary");
      title.textContent=labels[mode]+(open?" · primary test":" · separate comparison");el.append(title);
      const wrapper=document.createElement("div");wrapper.className="scroll";wrapper.tabIndex=0;wrapper.setAttribute("aria-label","Scrollable results table"); const tb=document.createElement("table");wrapper.append(tb);el.append(wrapper);
      const f=x=>x===null?"Unavailable":fmt(x);
      const diff=(point,ci)=>ci===null?f(point)+" (interval unavailable)":f(point)+" ["+ci.map(f).join(", ")+"]";
      const late=mode==="late";
      table(tb,"Absolute losses and paired differences on matched sequences. Brackets give 95% moving-block intervals.",
        ["Workspace","Windows / sequences","Update",late?"Stale + spikes":"Earlier","Other reach","Update − "+(late?"stale":"earlier"),"Update − other"],
        summary.map(row=>[row.ws,`${row.windows} / ${row.originals}`,...row.means.slice(0,3).map(f),diff(row.means[3],row.ci[3]),diff(row.means[4],row.ci[4])]));
      node.append(el);
    }
    if (s.motor) {
      const d=document.createElement("details"), h=document.createElement("summary");h.textContent="Fitted movement model · trajectory error";d.append(h);
      const p=document.createElement("p");p.textContent=s.motor.detail;d.append(p);
      const wrap=document.createElement("div");wrap.className="scroll";wrap.tabIndex=0;wrap.setAttribute("aria-label","Scrollable movement results");const tb=document.createElement("table");wrap.append(tb);d.append(wrap);
      table(tb,"Mean Euclidean error across ten forecast positions. Smaller is better.",s.motor.columns,s.motor.rows);node.append(d);
    }
  }
  function render() {
    const rec=currentCase(), [block,workspace,original,ordinal,k]=rec.key;
    const landmark=byId("landmark").selectedIndex;
    const col=3*landmark+byId("axis").selectedIndex;
    const old=Number(byId("old").value), newly=Number(byId("new").value);
    const edited=old!==0||newly!==0;
    byId("old-value").value=old+" mm";byId("new-value").value=newly+" mm";
    byId("identity").textContent=`Block ${block} · Workspace ${workspace} · Sequence ${original} · Go ${ordinal} · First forecast at native row ${k}.`;
    const status=byId("status");status.classList.toggle("edited",edited);
    status.textContent=edited?"Hypothetical reach. The count models have run on your edited path. The movement forecast uses your old path and the recorded earlier counts. Recorded outcome values are hidden.":"Recorded reach. The measured path and later counts are available for comparison with forecasts from September 7.";
    const {history,future}=WeekForecast.edit(rec,col,old,newly);
    const mode=pop(), fit=WEEK_MODEL.populations[mode==="late"?"primary":mode];
    const ordinary=WeekForecast.predict(fit,rec,history,future);
    // An edited new path cannot affect a movement forecast issued at k.
    const motorKey = [byId("case").value,old ? col : -1,old].join("/");
    if (lastMotor?.key !== motorKey) lastMotor={key:motorKey, path:WeekMovement.predict(WEEK_MOVEMENT,rec,history)};
    pathChart(col,history,future,ordinary.velocity,lastMotor.path,edited);
    countsChart(rec,mode==="late"?WeekForecast.late(WEEK_MODEL.late,rec,history,future):ordinary,edited);
  }
  function restore(){byId("old").value="0";byId("new").value="0";render();}
  function fillContacts(){const contacts=contactList(), prev=Number(byId("contact").value);options(byId("contact"),contacts,contacts.map(c=>"Contact "+c));if(contacts.includes(prev))byId("contact").value=prev;}
  options(byId("case"),WEEK_CASES.map((_,j)=>j),WEEK_CASES.map(r=>`Block ${r.key[0]} · Workspace ${r.key[1]} · ${r.selection==="first"?"First reach":"First with donor"}`));
  byId("case").addEventListener("change",restore);
  byId("landmark").addEventListener("change",()=>{const n=byId("landmark").selectedIndex===2?2:3, prev=byId("axis").selectedIndex;const axis=["X","Y","Z"].slice(0,n);options(byId("axis"),axis,axis);byId("axis").selectedIndex=Math.min(prev,n-1);restore();});
  byId("axis").addEventListener("change",restore);
  byId("population").addEventListener("change",()=>{fillContacts();render();});
  byId("contact").addEventListener("change",render);
  for(const k of ["old","new"])byId(k).addEventListener("input",render);
  byId("reset").addEventListener("click",restore);
  if(location.protocol==="file:") {
    const a=byId("download");a.href="README.md";a.removeAttribute("download");a.textContent="Offline guide";
  }
  let width=0;
  new ResizeObserver(items=>{const w=Math.round(items[0].contentRect.width);if(width!==w){width=w;render();}}).observe(byId("path"));
  fillContacts();results();render();
})();
