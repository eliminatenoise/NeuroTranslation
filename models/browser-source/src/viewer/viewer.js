"use strict";

const data = JSON.parse(document.getElementById("dataset").textContent);
const element = id => document.getElementById(id);
const methods = [
  ["motion", "Movement only"],
  ["combined", "Movement + firing"],
  ["earlier_trip", "Movement + earlier-trip firing"],
  ["constant_speed", "Continue at last speed"]
];
const intervalLabels = ["1,000–750", "750–500", "500–250", "250–0"];
let selected = 0;
let revealed = false;
let donorView = false;

function observations(anchor) {
  return {
    times: anchor.history.map(i => data.times[i]),
    positions: anchor.history.map(i => data.xy[i]),
    counts: Array.from({length:4}, (_, i) => data.counts.map(region => region[anchor.end_bin - 4 + i]))
  };
}

function measured(anchor) {
  const start = data.xy[anchor.history[4]];
  const end = data.xy[anchor.target];
  return Math.hypot(end[0] - start[0], end[1] - start[1]);
}

function drawCamera(anchor) {
  // Fixed equal-distance axes leave every cutoff in the same physical coordinate frame.
  const x = value => 61 + (value - 20) * 2.28;
  const y = value => 268 - value * 2.28;
  const grid = [];
  for (let tick = 20; tick <= 140; tick += 20) {
    grid.push('<path d="M'+x(tick)+' 17V268" stroke="#dce2d8"/>',
      '<text x="'+x(tick)+'" y="285" text-anchor="middle">'+tick+'</text>');
  }
  for (let tick = 0; tick <= 100; tick += 20) {
    grid.push('<path d="M61 '+y(tick)+'H335" stroke="#dce2d8"/>',
      '<text x="51" y="'+(y(tick)+4)+'" text-anchor="end">'+tick+'</text>');
  }
  function path(from, through) {
    const commands = [];
    let penDown = false;
    for (let i = from; i <= through; i++) {
      const pair = data.xy[i];
      if (!pair.every(Number.isFinite)) {
        penDown = false;
        continue;
      }
      const connected = penDown && data.times[i] - data.times[i-1] <= 0.1;
      commands.push((connected ? "L" : "M") + x(pair[0]).toFixed(2) + " " + y(pair[1]).toFixed(2));
      penDown = true;
    }
    return commands.join("");
  }
  const latest = anchor.history[4];
  const coords = i => 'cx="'+x(data.xy[i][0])+'" cy="'+y(data.xy[i][1])+'"';
  const whole = revealed && element("whole").checked;
  const lines = [
    '<text x="198" y="310" text-anchor="middle">X (cm)</text>',
    '<text transform="translate(18 145) rotate(-90)" text-anchor="middle">Y (cm)</text>'
  ];
  if (whole) lines.push('<path data-role="whole" d="'+path(0, data.times.length-1)+'" stroke="#bec7bb" fill="none" stroke-width="1.5"/>');
  lines.push('<path data-role="past" d="'+path(0, latest)+'" stroke="#718c7d" fill="none" stroke-width="2"/>');
  if (revealed) {
    lines.push('<path d="'+path(latest, anchor.target)+'" fill="none" stroke="#9c492d" stroke-width="2.2"/>');
  }
  anchor.history.forEach(i => lines.push('<circle '+coords(i)+' r="3.8" fill="#176b51" stroke="white" stroke-width="1.1"/>'));
  lines.push('<circle '+coords(latest)+' r="5.5" fill="none" stroke="#162920" stroke-width="1.9"/>');
  if (revealed) {
    const [tx, ty] = data.xy[anchor.target];
    lines.push('<rect data-role="target" x="-3.7" y="-3.7" width="7.4" height="7.4" fill="#9c492d" stroke="white" stroke-width="1" transform="translate('+x(tx)+' '+y(ty)+') rotate(45)"/>');
  }
  element("map").innerHTML='<g font-size="12">'+grid.join("")+lines.join("")+'</g>';
  element("map").setAttribute("aria-label", 'Recorded camera positions in centimetres. Five input frames. Last input at X '+data.xy[latest][0].toFixed(2)+', Y '+data.xy[latest][1].toFixed(2)+'.'+(revealed?' Later frame at X '+data.xy[anchor.target][0].toFixed(2)+', Y '+data.xy[anchor.target][1].toFixed(2)+'.':''));
}

function drawFiring(counts, anchor) {
  const displayed = donorView ? anchor.donor : counts;
  const floor = 155;
  const chart = ['<text x="38" y="13" font-size="13">Spikes per 250 ms</text>'];
  for (const tick of [0, 20, 40, 60]) {
    const y = floor - tick * 1.75;
    chart.push('<path d="M36 '+y+'H441" stroke="#cbd4c7"/>',
               '<text x="28" y="'+(y+4)+'" text-anchor="end">'+tick+'</text>');
  }
  displayed.forEach((pair, i) => {
    const center = 90 + 98*i;
    pair.forEach((n, region) => {
      const x = center - 16 + region * 17, h = 1.75 * n;
      chart.push('<rect x="'+x+'" y="'+(floor-h)+'" width="15" height="'+h+'" fill="'+(region ? "#9c492d" : "#176b51")+'"/>');
    });
    chart.push('<text x="'+center+'" y="174" text-anchor="middle">'+intervalLabels[i]+'</text>');
  });
  chart.push('<text x="239" y="198" text-anchor="middle">Milliseconds before cutoff</text>');
  element("activity").innerHTML='<g font-size="12">'+chart.join("")+'</g>';
  const trip = donorView ? anchor.donor_trip : 1;
  const time = donorView ? anchor.donor_cutoff : anchor.cutoff;
  element("donor-note").textContent='Showing JS21, trip '+trip+' · cutoff '+time.toFixed(3)+' s on the recording clock.';
  element("activity").setAttribute("aria-label",'Four intervals from trip '+trip+'. CA1 spikes: '+displayed.map(p=>p[0]).join(", ")+'. PFC spikes: '+displayed.map(p=>p[1]).join(", ")+'.');
  element("count-rows").innerHTML=displayed.map((p,i)=>'<tr><td>'+intervalLabels[i]+'</td><td>'+p[0]+'</td><td>'+p[1]+'</td></tr>').join("");
  element("counts-heading").textContent='Four firing intervals · trip '+trip;
}

function drawBars(id, methodList, anchor, estimates) {
  const truth = revealed ? measured(anchor) : null;
  const bars = methodList.map(([key,label]) => {
    const score = estimates[key];
    const error = revealed ? '<span class="delta">Error '+Math.abs(score - truth).toFixed(2)+' cm</span>' : '';
    return '<div class="forecast-row" data-method="'+key+'"><div class="bar-label"><span>'+label+error+'</span><strong>'+score.toFixed(2)+' cm</strong></div><div class="bar-track"><div class="bar-fill" style="width:'+Math.min(100,score/20*100)+'%"></div></div></div>';
  });
  element(id).innerHTML=bars.join("");
}

function drawForecasts(anchor, estimates) {
  const truth = revealed ? measured(anchor) : null;
  drawBars("bars", methods, anchor, estimates);
  element("actual").hidden = !revealed;
  element("target-key").hidden = !revealed;
  element("whole-control").hidden = !revealed;
  element("reveal").setAttribute("aria-expanded", String(revealed));
  element("reveal").textContent = revealed ? "Hide the later frame" : "Reveal the later frame";
  if (revealed) {
    const after = (data.times[anchor.target] - anchor.cutoff)*1000;
    const span = (data.times[anchor.target] - data.times[anchor.history[4]])*1000;
    element("actual").innerHTML='<strong>Camera measurement · '+truth.toFixed(2)+' cm</strong><div>The later frame came '+after.toFixed(1)+' ms after cutoff. The two measured positions were '+span.toFixed(1)+' ms apart.</div>';
  } else {
    element("actual").textContent = "";
  }
}

let renderVersion = 0;
async function drawShared(anchor, inputs, version) {
  const bars = element("shared-bars");
  bars.setAttribute("aria-busy", "true");
  bars.textContent = "Calculating forecasts…";
  const camera = {domain:"rat_population", cutoffS:anchor.cutoff, priorTimeS:inputs.times, priorXyCm:inputs.positions};
  const combined = {...camera, mode:"combined", unitCounts:data.units};
  try {
    const [motion, aligned, earlier] = await Promise.all([
      SharedMotion.forecastMovement({...camera, mode:"motion"}),
      SharedMotion.forecastMovement({...combined, regionalCounts:inputs.counts}),
      SharedMotion.forecastMovement({...combined, regionalCounts:anchor.donor})
    ]);
    if (version !== renderVersion) return;
    drawBars("shared-bars", methods.slice(0,3), anchor,
             {motion:motion.distanceCm, combined:aligned.distanceCm, earlier_trip:earlier.distanceCm});
    element("announce").textContent += " Shared movement and firing forecast "+aligned.distanceCm.toFixed(2)+" centimetres.";
  } catch (error) {
    if (version !== renderVersion) return;
    bars.textContent = "Shared forecast unavailable. " + error.message;
  }
  bars.setAttribute("aria-busy", "false");
}

function render() {
  const a = data.anchors[selected];
  const inputs = observations(a);
  const predictions = forecast(a.cutoff, inputs.times, inputs.positions, inputs.counts, a.donor, data.units, data.weights);
  element("prev").disabled = selected === 0;
  element("next").disabled = selected === data.anchors.length-1;
  element("cutoff").value = String(selected+1);
  element("cutoff-number").textContent = (selected+1)+" of "+data.anchors.length;
  const elapsed = (a.cutoff-data.start).toFixed(0)+' s into trip';
  element("elapsed").textContent = elapsed;
  element("cutoff").setAttribute("aria-valuetext", (selected+1)+" of "+data.anchors.length+", "+elapsed);
  drawCamera(a);
  drawFiring(inputs.counts, a);
  drawForecasts(a, predictions);
  drawShared(a, inputs, ++renderVersion);
  element("camera-rows").innerHTML=inputs.times.map((t,i)=>'<tr><td>'+((a.cutoff-t)*1000).toFixed(1)+'</td><td>'+inputs.positions[i][0].toFixed(2)+'</td><td>'+inputs.positions[i][1].toFixed(2)+'</td></tr>').join("");
  element("announce").textContent='Cutoff '+(selected+1)+', '+elapsed+'. Movement and firing forecast '+predictions.combined.toFixed(2)+' centimetres.'+(revealed?' Camera measurement '+measured(a).toFixed(2)+' centimetres.':'');
}
function choose(value) {
  selected = Math.min(data.anchors.length - 1, Math.max(0,value));
  revealed = false;
  element("whole").checked = false;
  render();
}
element("prev").addEventListener("click", () => choose(selected - 1));
element("next").addEventListener("click", () => choose(selected + 1));
element("cutoff").addEventListener("input", e => choose(Number(e.target.value)-1));
element("reveal").addEventListener("click", () => {
  revealed = !revealed;
  element("whole").checked = false;
  render();
});
element("whole").addEventListener("change", () => drawCamera(data.anchors[selected]));
document.querySelectorAll('input[name="activity"]').forEach(input => {
  input.addEventListener("change", () => {
    donorView = input.value === "donor";
    const a = data.anchors[selected];
    drawFiring(observations(a).counts, a);
  });
});

const scoreOrder = ["constant_speed","motion","combined","earlier_trip"];
function scoreRow(label, count, result, order=scoreOrder) {
  return '<tr><th scope="row">'+label+'</th><td>'+count+'</td>'+order.map(k=>'<td>'+result[k].toFixed(3)+'</td>').join("")+'</tr>';
}
element("rat-rows").innerHTML = data.scores.map(r => scoreRow(r.rat,r.anchors,r)).join("");
element("mean-row").innerHTML = scoreRow("Equal weight per rat",data.scores.reduce((n,r)=>n+r.anchors,0),data.mean);
const sharedOrder = ["shared_motion","shared_combined","shared_donor","scrambled_combined"];
element("shared-rat-rows").innerHTML = data.sharedScores.map(r => scoreRow(r.rat, r.windows, r, sharedOrder)).join("");
element("shared-mean-row").innerHTML = scoreRow("Equal weight per rat",
  data.sharedScores.reduce((n, r) => n + r.windows, 0), data.sharedMean, sharedOrder);
render();
