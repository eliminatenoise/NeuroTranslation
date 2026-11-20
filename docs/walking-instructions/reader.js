(() => {
  const byId = id => document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const landmarks = ["Pelvis", "Right heel"];
  const colors = ["#126458", "#a54324"];
  const cueKeys = ["4", "5", "none"];
  const cueLabels = {4:"“as usual”", 5:"“fast but not running”", none:"Withhold instruction"};
  const cueValue = {4:"as usual", 5:"fast but not running", none:null};
  const directions = ["Forward", "Left", "Up"];
  let current = null;

  function signed(value) {
    const rounded = Number(value.toFixed(2));
    return (rounded < 0 ? "−" : rounded > 0 ? "+" : "") + Math.abs(rounded).toFixed(2);
  }
  function svgNode(tag, attrs, label) {
    const element = document.createElementNS(ns, tag);
    for (const [name,value] of Object.entries(attrs)) element.setAttribute(name, value);
    if (label !== undefined) element.textContent = label;
    return element;
  }
  function tickSize(range) {
    const rough = Math.max(range / 4, 1);
    const unit = 10 ** Math.floor(Math.log10(rough));
    return unit * ([1,2,2.5,5,10].find(mult => mult >= rough / unit) || 10);
  }
  function drawChart() {
    if (!current) return;
    const axis = Number(byId("axis").value);
    const cue = document.querySelector('input[name="cue"]:checked').value;
    const {history, predictions} = current;
    const series = landmarks.map((_,i) => history.map(row => row[i][axis] - history[20][i][axis]));
    const endpoints = predictions[cue].map(point => point[axis]);
    const width = Math.max(230, Math.floor(byId("chart").getBoundingClientRect().width));
    const height = width < 420 ? 202 : 220;
    const left = width < 420 ? 43 : 52, right = width - 15, top = 21, bottom = height - 37;
    const values = [...series.flat(), ...endpoints, 0];
    const min = Math.min(...values), max = Math.max(...values);
    const step = tickSize(max - min);
    const lo = Math.floor(min / step) * step - (min === max ? step : 0);
    const hi = Math.max(lo + step, Math.ceil(max / step) * step);
    const x = time => left + (time+200)/300*(right-left);
    const y = value => bottom - (value-lo)/(hi-lo)*(bottom-top);
    const svg = svgNode("svg", {viewBox:`0 0 ${width} ${height}`,role:"img","aria-labelledby":"plot-title plot-description"});
    const add = (tag, attrs, label) => svg.append(svgNode(tag,attrs,label));
    add("title", {id:"plot-title"}, directions[axis]+" displacement history and 100 ms forecast");
    add("desc", {id:"plot-description"}, `Invented history from −200 to 0 ms. Forecast in millimetres: pelvis ${signed(endpoints[0])}, right heel ${signed(endpoints[1])}. The numeric table gives all three axes.`);
    const text = (xx,yy,anchor,label) => add("text",{x:xx,y:yy,"font-size":11,"text-anchor":anchor,fill:"#455951"},label);
    text(left-6,12,"end","mm");
    add("rect",{x:x(0),y:top,width:right-x(0),height:bottom-top,fill:"#f0f2e9"});
    for (let i=0; i<=Math.round((hi-lo)/step); i++) {
      const tick = lo + step*i;
      add("line",{x1:left,x2:right,y1:y(tick),y2:y(tick),stroke: tick===0?"#81958b":"#d8dfd5"});
      text(left-7,y(tick)+4,"end",String(tick).replace("-","−"));
    }
    add("line",{x1:x(0),x2:x(0),y1:top,y2:bottom,stroke:"#84988e"});
    for (const t of [-200,-100,0,100]) {
      const label = t===100?"+100":String(t).replace("-","−");
      text(x(t),bottom+16,t===100?"end":t===-200?"start":"middle",label);
    }
    text(right,height-2,"end","Time from cutoff (ms)");
    for (const [i,path] of series.entries()) {
      const points = path.map((v,k) => [x(-200+k*10),y(v)].join(",")).join(" ");
      add("polyline",{points,fill:"none",stroke:colors[i],"stroke-width":2.6,"stroke-linecap":"round","stroke-linejoin":"round"});
      const endX = x(100), endY = y(endpoints[i]);
      add("line",{x1:x(0),x2:endX,y1:y(0),y2:endY,stroke:colors[i],"stroke-width":1.8,"stroke-dasharray":i===0?"6 4":"2 3"});
      if (i===0) add("circle",{cx:endX,cy:endY,r:4.7,fill:"#fffef8",stroke:colors[i],"stroke-width":2.5});
      else {
        const radius=5;
        add("polygon",{points:[[endX,endY-radius],[endX+radius,endY],[endX,endY+radius],[endX-radius,endY]].map(p=>p.join(",")).join(" "),fill:"#fffef8",stroke:colors[i],"stroke-width":2.5});
      }
    }
    byId("chart").replaceChildren(svg);
  }

  function render() {
    const speed = Number(byId("speed").value), lift = Number(byId("lift").value), offset = Number(byId("offset").value);
    const cue = document.querySelector('input[name="cue"]:checked').value;
    const key = [speed,lift,offset].join("/");
    byId("speed-out").textContent = speed.toFixed(2)+" m/s";
    byId("lift-out").textContent = lift+" mm";
    byId("cue-note").textContent = cue === "none"
      ? "The motion-only fit receives the same invented history and strike timing."
      : "Switch phrases to change the task code while keeping every marker sample fixed.";
    try {
      if (current?.key !== key) {
        const history = WalkingExamples.history({speed,lift,offset});
        const predictions = {};
        for (const c of cueKeys) {
          const forecast = WalkingForecast.predict(WalkingWeights,{history_mm:history,offset,instruction:cueValue[c]});
          if (forecast.length !== 2 || forecast.some(p => p.length !== 3 || !p.every(Number.isFinite))) {
            throw new Error("The model returned an invalid displacement.");
          }
          predictions[c] = forecast;
        }
        current = {key,history,predictions};
      }
      const allBody = document.querySelector("#all-pred tbody");
      allBody.replaceChildren();
      for (const c of cueKeys) {
        current.predictions[c].forEach((vec,i) => {
          const row = allBody.insertRow();
          for (const value of [cueLabels[c],landmarks[i],...vec.map(signed)]) row.insertCell().textContent = value;
        });
      }
      current.predictions[cue].forEach((vec,i) => {
        const cells = document.querySelectorAll(`[data-landmark="${i}"] td`);
        vec.forEach((value,axis) => { cells[axis].textContent = signed(value); });
      });
      drawChart();
      const sr = current.predictions[cue].map((row,i) => landmarks[i]+": "+row.map(signed).join(", "));
      byId("result-status").textContent = cueLabels[cue]+". Forward, left and up displacement in millimetres. "+sr.join(". ");
      byId("fail").hidden=true;
    } catch (error) {
      current = null;
      document.querySelectorAll("#pred td").forEach(cell => {cell.textContent="—";});
      document.querySelector("#all-pred tbody").replaceChildren();
      byId("chart").replaceChildren();
      byId("result-status").textContent = "";
      byId("fail").hidden = false;
      byId("fail").textContent = "Forecast unavailable. Extract the complete offline reader or reload the page.";
      console.error(error);
    }
  }
  if (location.protocol === "file:") {
    byId("download").hidden = true;
    document.querySelectorAll('a[href^="/"]').forEach(a => {
      a.href = new URL(a.getAttribute("href"),"https://eliminatenoise.github.io/").href;
    });
  }
  for (const el of document.querySelectorAll('.controls input, .controls select')) el.addEventListener("input",render);
  byId("axis").addEventListener("change",drawChart);
  byId("reset").addEventListener("click",() => {
    byId("speed").value="1.10"; byId("lift").value="70"; byId("offset").value="30"; byId("axis").value="0";
    document.querySelector('input[name="cue"][value="4"]').checked=true;
    render();
  });
  const narrow = window.matchMedia("(max-width: 735px)");
  byId("history-options").open = !narrow.matches;
  narrow.addEventListener?.("change", event => { byId("history-options").open = !event.matches; });
  render();
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(drawChart).observe(byId("chart"));
  else window.addEventListener("resize",drawChart);
})();
