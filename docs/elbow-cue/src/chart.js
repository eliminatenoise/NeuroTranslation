function plotElbow(history, change, outcome) {
  const svg = document.getElementById("chart"), group = document.getElementById("marks");
  const mobile = svg.getBoundingClientRect().width < 450;
  const width = mobile ? 380 : 640, height = 222;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  group.replaceChildren();
  const left = mobile ? 52 : 66, right = width-26, top = 34, bottom = height-43;
  const endpoint = history[3] + change;
  const values = [...history, endpoint, ...(outcome === null ? [] : [outcome])];
  const lo = Math.min(...values), hi = Math.max(...values), span = Math.max(hi-lo, 0.12);
  const mid = (lo+hi)/2, lower = mid - span*.66, upper = mid + span*.66;
  const x = t => left + (t + .25)/1.25 * (right-left);
  const y = value => bottom - (value-lower)/(upper-lower) * (bottom-top);
  const fmt = n => Math.abs(n) >= 10000 ? n.toExponential(1) : Number(n.toFixed(span < .1 ? 3 : 2)).toString();
  function el(tag, attrs, label) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (label !== undefined) node.textContent = label;
    group.append(node);
    return node;
  }
  function line(x1,y1,x2,y2,stroke,dash) {
    return el("line",{x1,y1,x2,y2,stroke,"stroke-width":1,...(dash ? {"stroke-dasharray":dash} : {})});
  }
  function label(x, y, text, anchor="middle", color="#c7dace") {
    return el("text",{x,y,"text-anchor":anchor,fill:color,"font-size":mobile?12:13},text);
  }
  el("rect",{x:x(-.25),y:top,width:x(.25)-x(-.25),height:bottom-top,fill:"#263f36"});
  for (const value of [lower, mid, upper]) {
    line(left,y(value),right,y(value),"#456052","3 4");
    label(left-6,y(value)+4,fmt(value),"end");
  }
  for (const [time,text] of [[0,"Cue"],[.25,"Cutoff"],[1,"Endpoint"]]) {
    line(x(time),top-4,x(time),bottom+3,time===.25?"#92ba9f":"#587062",time===.25?"4 4":"2 5");
    label(x(time),top-12,text, time===1?"end":"middle");
    label(x(time),bottom+20,time===0?"0 s":`+${time.toFixed(2)} s`,time===1?"end":"middle");
  }
  const points = history.map((v,i) => [x(-.125+i*.125),y(v)]);
  el("polyline",{points:points.map(p=>p.join(",")).join(" "),fill:"none",stroke:"#cad8cc","stroke-width":2});
  points.forEach(([cx,cy])=>el("circle",{cx,cy,r:3.8,fill:"#d4dfd4",stroke:"#263f36"}));
  const fx=x(1), fy=y(endpoint), r=7;
  el("polygon",{points:`${fx},${fy-r} ${fx+r},${fy} ${fx},${fy+r} ${fx-r},${fy}`,fill:"#adf0c0",stroke:"#142d26","stroke-width":1.5});
  if (outcome !== null) {
    // The hollow square still reveals the diamond when forecast and outcome coincide.
    el("rect",{x:fx-9,y:y(outcome)-9,width:18,height:18,fill:"none",stroke:"#ffcc86","stroke-width":2});
  }
  document.getElementById("chart-desc").textContent = `Four invented summaries are ${history.join(", ")}. Predicted endpoint ${endpoint.toFixed(5)} native units. ${outcome===null?"No later observation entered.":"Invented later observation "+outcome+"."}`;
}
