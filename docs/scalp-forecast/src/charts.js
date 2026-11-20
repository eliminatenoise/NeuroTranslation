"use strict";
const ForecastCharts = (() => {
  const svgNS = "http://www.w3.org/2000/svg";
  function element(tag, text, className) {
    const out = document.createElement(tag);
    if (text !== undefined) out.textContent = text;
    if (className) out.className = className;
    return out;
  }
  function svg(tag, attributes, text) {
    const out = document.createElementNS(svgNS, tag);
    for (const [key, value] of Object.entries(attributes)) out.setAttribute(key, value);
    if (text !== undefined) out.textContent = text;
    return out;
  }
  function number(x, digits = 3) {
    if (!Number.isFinite(x)) return "—";
    if (Object.is(x, -0) || x === 0) return "0";
    if (Math.abs(x) < .001 || Math.abs(x) >= 100000) return x.toExponential(digits - 1);
    return Number(x.toPrecision(digits)).toString();
  }
  function namedChart(label, first, second, sensor) {
    const panel = element("article", undefined, "chart");
    panel.append(element("h3",label));
    if (!first && !second) {
      panel.append(element("p","Supply the missing readings to see this forecast."));
      return panel;
    }
    const values = [first,second].filter(Boolean).flatMap(result => result.delta.map(row=>row[sensor]));
    let low = Math.min(...values,0), high = Math.max(...values,0);
    if (high === low) { high += 1; low -= 1; }
    const scale = Math.max(Math.abs(low), Math.abs(high));
    const hi = high / scale, lo = low / scale;
    const x = k => 47 + 63 * k;
    const y = v => 18 + 83 * (hi - v/scale)/(hi-lo);
    const graph = svg("svg", {viewBox:"0 0 256 135",role:"img","aria-label":label+" predicted change. Exact values follow under Read all nine forecast values."});
    const tickVals = [high,low];
    if (high > 0 && low < 0 && y(0)-18 > 13 && 101-y(0) > 13) tickVals.push(0);
    for (const v of tickVals) {
      graph.append(svg("line",{x1:x(0),y1:y(v),x2:x(3),y2:y(v),stroke:v===0?"#99aca2":"#e0e7de"}));
      graph.append(svg("text",{x:40,y:y(v)+3,"text-anchor":"end"},number(v)));
    }
    ["0","+0.5","+1.0","+1.5 s"].forEach((t,i)=>graph.append(svg("text",{x:x(i),y:121,"text-anchor":"middle"},t)));
    for (const [result,color,dash] of [[second,"#a44b15","5 4"],[first,"#177267",""]]) {
      if (!result) continue;
      const points = [0,...result.delta.map(row=>row[sensor])];
      graph.append(svg("polyline",{points:points.map((v,i)=>x(i)+","+y(v)).join(" "),fill:"none",stroke:color,"stroke-width":2.3,"stroke-dasharray":dash}));
      points.slice(1).forEach((v,i)=>{
        const p=dash
          ? svg("rect",{x:x(i+1)-3.6,y:y(v)-3.6,width:7.2,height:7.2,fill:"white",stroke:color,"stroke-width":1.8})
          : svg("circle",{cx:x(i+1),cy:y(v),r:3.1,fill:color});
        p.append(svg("title",{},number(v,7)+" at +"+(.5*(i+1))+" s"));
        graph.append(p);
      });
    }
    panel.append(graph);
    return panel;
  }
  function makeTable(id, name, headers, rows) {
    const target=document.getElementById(id);
    const scroller=element("div",undefined,"table-scroll");
    scroller.tabIndex=0;scroller.setAttribute("role","region");scroller.setAttribute("aria-label",name);
    const table=element("table");table.setAttribute("aria-label",name);
    const head=table.createTHead().insertRow();
    headers.forEach(h=>{const th=element("th",h);th.scope="col";head.append(th);});
    const body=table.createTBody();
    rows.forEach(({name,values,active})=>{
      const row=body.insertRow();if(active) row.className="strong-row";
      const first=element("th",name);first.scope="row";row.append(first);
      values.forEach(v=>row.insertCell().textContent=v);
    });
    scroller.append(table);target.replaceChildren(scroller);
  }
  return {element,number,namedChart,makeTable};
})();
