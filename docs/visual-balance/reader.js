(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  const colours = ["#006e64", "#ac4a20"];
  const names = ["Sacrum", "Head"];
  const axes = ["Mediolateral", "Superior–inferior", "Anterior–posterior"];
  const sourceURL = "https://eliminatenoise.github.io";
  if (location.protocol === "file:") {

    document.querySelectorAll("a[data-project]").forEach(link => {
      link.href = sourceURL + link.getAttribute("href");
    });
  }

  byId("download").hidden = location.protocol === "file:";

  const form = byId("inputs");
  let current = null;
  const digit = (v, n = 2) => Math.abs(v).toFixed(n);
  function signed(v, n = 2) {
    const label = digit(v, n);
    return Number(label) === 0 ? label : (v < 0 ? "−" : "+") + label;
  }

  function makeExample() {
    const direction = Number(form.elements.direction.value);
    const event = VisualWalkForecast.example(Number(byId("phase").value) * Math.PI / 180, direction);
    const motionGain = Number(byId("motion").value);
    event.motion_mm = event.motion_mm.map(frame => frame.map(marker => marker.map(x => x * motionGain)));
    const withholdScalp = byId("scalpMode").value === "no_scalp";
    const scalpGain = withholdScalp ? 0 : Number(byId("scalp").value);
    if (withholdScalp) event.eeg_good.fill(false);
    for (const field of ["eeg_mean_uv", "eeg_rms_uv"]) {
      event[field] = event[field].map(bin => bin.map(x => x * scalpGain));
    }
    const groups = {all: [], eyes: [2, 3, 4], neck: [0, 1], legs: [5, 6, 7, 8, 9, 10, 11, 12]};
    for (const channel of groups[byId("other").value]) {
      event.nuisance_good[channel] = false;
      for (const field of ["nuisance_mean_uv", "nuisance_rms_uv"]) {
        for (const bin of event[field]) bin[channel] = 0;
      }
    }
    return event;
  }

  function draw() {
    if (!current) return;
    const axis = Number(byId("axis").value);
    const {event, prediction} = current;
    const traces = names.map((_, i) => event.motion_mm.map(frame => frame[i][axis]));
    const end = prediction.map(row => row[axis]);
    const w = Math.max(235, Math.round(byId("chart").clientWidth));
    const h = w < 430 ? 184 : 212;
    const left = w < 430 ? 38 : 48, right = w - 13, top = 25, bottom = h - 33;
    const first = -159 * 1000 / 256, last = 125;
    const x = ms => left + (right - left) * (ms - first) / (last - first);
    const extent = Math.max(1, ...traces.flat().map(Math.abs), ...end.map(Math.abs));
    const pow = Math.pow(10, Math.floor(Math.log10(extent)));
    const limit = ([1, 2, 3, 4, 5, 7.5, 10].find(k => k * pow >= extent) || 10) * pow;
    const y = value => top + (bottom - top) * (.5 - value / (2 * limit));
    const f = n => n.toFixed(2);
    let svg = '<svg role="img" aria-labelledby="plot-title plot-desc" viewBox="0 0 '+w+' '+h+'" xmlns="http://www.w3.org/2000/svg">';
    svg += '<title id="plot-title">'+axes[axis]+' displacement in millimetres</title><desc id="plot-desc">Invented head and sacrum histories through zero milliseconds, then two separately predicted endpoints at +125 milliseconds. The line at about −125 milliseconds marks visual rotation onset.</desc>';
    svg += '<rect x="'+f(x(0))+'" y="'+top+'" width="'+f(right-x(0))+'" height="'+(bottom-top)+'" fill="#eef4ed"/>';
    for (const tick of [-limit, 0, limit]) {
      const yy = f(y(tick));
      svg += '<path d="M'+left+' '+yy+'H'+right+'" stroke="#d4dfdc" fill="none"/><text x="'+(left-6)+'" y="'+f(y(tick)+4)+'" text-anchor="end">'+signed(tick, Number.isInteger(limit) ? 0 : 1)+'</text>';
    }
    svg += '<path d="M'+f(x(-125))+' '+top+'V'+bottom+'" stroke="#748b84" stroke-dasharray="2 3"/>';
    svg += '<text x="'+f(x(-125))+'" y="15" text-anchor="middle">Rotation onset</text>';
    svg += '<path d="M'+f(x(0))+' '+top+'V'+bottom+'" stroke="#8b9e95"/>';
    for (let i=0; i<2; i++) {
      const points = traces[i].map((value, t) => f(x((t-159)*1000/256))+','+f(y(value))).join(' ');
      svg += '<polyline points="'+points+'" fill="none" stroke="'+colours[i]+'" stroke-width="2.4" '+(i===1?'stroke-dasharray="6 2"':'')+' stroke-linejoin="round"/>';
      const xx = x(125), yy = y(end[i]), r = i === 0 ? 5 : 3.5;
      svg += '<path d="M'+f(xx)+' '+f(yy-r)+'l'+r+' '+r+' -'+r+' '+r+' -'+r+' -'+r+'z" stroke="'+colours[i]+'" stroke-width="2" fill="white"/>';
    }
    for (const [ms,label,anchor] of [[first,"−621 ms","start"],[0,"0","end"],[last,w<430?"+125":"+125 ms","end"]]) {
      svg += '<text x="'+f(x(ms)+(ms===0?-3:ms===last?4:0))+'" y="'+(bottom+17)+'" text-anchor="'+anchor+'">'+label+'</text>';
    }
    svg += '<text x="2" y="15">mm</text></svg>';
    byId("chart").innerHTML = svg;
  }

  function update() {
    try {
      const mode = byId("scalpMode").value;
      byId("scalp").disabled = mode === "no_scalp";
      byId("scalpValue").value = mode === "full" ? digit(Number(byId("scalp").value)) + "×" : "Withheld";
      byId("motionValue").value = digit(Number(byId("motion").value)) + "×";
      byId("phaseValue").value = byId("phase").value + "°";
      const event = makeExample();
      const prediction = VisualWalkForecast.predict(event, VisualWalkWeights[mode]);
      if (prediction.length !== 2 || prediction.some(row => row.length !== 3 || row.some(value => !Number.isFinite(value)))) {
        throw new Error("Invalid forecast");
      }
      current = {event, prediction};
      byId("prediction").tBodies[0].innerHTML = prediction.map((v, i) => '<tr><th scope="row">'+names[i]+'</th>'+
        v.map(n => '<td>'+signed(n)+'</td>').join('')+'<td>'+digit(Math.hypot(...v))+'</td></tr>').join('');
      byId("which").textContent = mode === "full"
        ? "The full Transformer uses motion, cue direction and the available scalp, eye and muscle inputs."
        : "This second Transformer was fitted with scalp inputs withheld. Motion, cue direction and available eye and muscle signals still enter its forecast.";
      draw();
      byId("error").hidden = true;
    } catch (error) {
      current = null;
      byId("prediction").tBodies[0].replaceChildren(); byId("chart").replaceChildren();
      byId("which").textContent = "";
      byId("error").textContent = "The forecast could not run. Extract the complete download and open index.html beside its model files.";
      byId("error").hidden = false;
      console.error(error);
    }
  }
  form.addEventListener("input", update);
  form.addEventListener("reset", () => {setTimeout(() => {byId("axis").value="0";update();}, 0);});
  byId("axis").addEventListener("change", draw);
  new ResizeObserver(draw).observe(byId("chart"));
  update();
})();
