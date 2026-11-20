"use strict";

function drawForecasts(container, forecasts, sensorLabels, methods, formatNumber) {
  const ns = "http://www.w3.org/2000/svg";
  const width = Math.max(195, Math.min(850, container.clientWidth - (window.innerWidth > 800 ? 114 : 0)));
  const height = 119, left = width < 290 ? 47 : 55, right = width - 19;
  const top = 13, bottom = 91;
  const make = (tag, attributes, text) => {
    const element = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    if (text !== undefined) element.textContent = text;
    return element;
  };
  container.replaceChildren();
  sensorLabels.forEach((label, index) => {
    const panel = document.createElement("div");
    panel.className = "sensor-plot";
    const heading = document.createElement("h3");
    heading.textContent = label;
    const svg = make("svg", {viewBox: `0 0 ${width} ${height}`, role:"img", "aria-label": label + " change from cutoff"});
    const curves = forecasts.map(forecast => [0, ...forecast.delta.map(row => row[index])]);
    const description = curves.map((curve, i) => methods[i] + ": " + curve.slice(1).map(formatNumber).join(", ")).join(". ");
    svg.append(make("desc", {}, "Changes at 0.5, 1.0 and 1.5 seconds after cutoff. " + description));
    const low = Math.min(...curves.flat()), high = Math.max(...curves.flat());
    const pad = high === low ? 1 : Math.max(Math.abs(high), Math.abs(low)) * .10;
    const lower = low - pad, upper = high + pad;
    const x = position => left + position / 3 * (right - left);
    const y = value => bottom - (value - lower) / (upper - lower) * (bottom - top);
    const ticks = low === high ? [-1, 0, 1] : [low, 0, high].filter((value,i,a)=>i===a.indexOf(value));
    for (const value of ticks.filter(t=>t===0 || Math.abs(y(t)-y(0))>=13)) {
      svg.append(make("line", {x1:left,y1:y(value),x2:right,y2:y(value),stroke:value===0?"#8c9f97":"#d5ddd7","stroke-dasharray":value===0?"none":"2 3"}));
      svg.append(make("text", {x:left-5,y:y(value)+4,"text-anchor":"end",fill:"#485b55","font-size":11}, formatNumber(value)));
    }
    ["Cutoff","+0.5 s","+1.0 s","+1.5 s"].forEach((name, i) => {
      svg.append(make("text", {x:x(i),y:height-8,"text-anchor":"middle",fill:"#485b55","font-size":11},name));
    });
    // Draw the comparison first so its hollow diamonds remain visible at crossings.
    for (let series = curves.length - 1; series >= 0; series--) {
      const curve = curves[series], primary = series === 0;
      const color = primary ? "#984023" : "#286a66";
      svg.append(make("polyline", {points:curve.map((v,i)=>x(i)+","+y(v)).join(" "),fill:"none",stroke:color,"stroke-width":primary?2.5:2,"stroke-dasharray":primary?"none":"5 4"}));
      for (let i=1;i<curve.length;i++) {
        const cx=x(i), cy=y(curve[i]);
        const symbol = primary ? make("circle",{cx,cy,r:3.1,fill:color})
          : make("path",{d:`M ${cx} ${cy-5} l 5 5 -5 5 -5 -5 z`,fill:"#fffefa",stroke:color,"stroke-width":1.5});
        symbol.append(make("title",{},methods[series]+" at "+(i*.5)+" s: "+formatNumber(curve[i])));
        svg.append(symbol);
      }
    }
    panel.append(heading,svg); container.append(panel);
  });
}
