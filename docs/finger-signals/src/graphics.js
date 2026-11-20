// SPDX-License-Identifier: CC0-1.0
function drawingSurface(canvas) {
  const rect = canvas.getBoundingClientRect();
  const scale = Math.min(window.devicePixelRatio || 1, 3);
  canvas.width = Math.max(1, Math.round(rect.width * scale));
  canvas.height = Math.max(1, Math.round(rect.height * scale));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  return {ctx, width: rect.width, height: rect.height};
}

function drawGlove(canvas, finger) {
  const {ctx, width, height} = drawingSurface(canvas);
  // Fixed sensor-location diagram. No geometry depends on a sensor value.
  const s = Math.min(width / 230, height / 223);
  ctx.translate((width - s * 230) / 2, (height - s * 223) / 2);
  ctx.scale(s, s);
  const shape = new Path2D(
    "M72 209 L69 188 Q48 172 39 156 L17 124 Q11 114 17 110 Q24 105 31 112 " +
    "L58 139 Q62 142 63 132 L57 42 Q56 31 66 30 Q76 29 77 41 L84 104 " +
    "Q85 109 88 104 L92 17 Q93 6 103 6 Q114 6 113 19 L111 99 Q112 105 115 100 " +
    "L126 31 Q128 20 138 22 Q148 24 146 35 L140 108 Q140 114 144 110 " +
    "L158 68 Q161 57 170 60 Q180 63 176 74 L163 129 Q162 153 154 172 " +
    "L145 189 L144 209 Q109 219 72 209 Z");
  const fill = ctx.createLinearGradient(38, 30, 179, 194);
  fill.addColorStop(0, "#65817c"); fill.addColorStop(.53,"#496b69"); fill.addColorStop(1,"#345551");
  ctx.fillStyle = fill; ctx.fill(shape); ctx.lineWidth = 1.7; ctx.strokeStyle = "#bad0c4"; ctx.stroke(shape);
  ctx.lineWidth=1;ctx.strokeStyle="#9cafa2";
  ctx.stroke(new Path2D("M73 192 Q110 204 145 190 M72 200 Q110 211 144 199"));
  const channels = [
    "M23 116 Q40 141 60 156 Q79 171 84 185",
    "M67 40 Q70 93 75 122 Q81 153 94 186",
    "M103 16 Q102 90 104 126 L105 185",
    "M137 32 Q132 91 127 126 L117 185",
    "M168 69 Q156 110 153 132 Q147 157 130 185"
  ];
  // Draw the five cables as thin strips with a distinct marker on the cue.
  ctx.lineCap="round";
  channels.forEach((p, i) => {
    const path = new Path2D(p);
    ctx.strokeStyle = i === finger ? "#524631" : "#345553";
    ctx.lineWidth = i === finger ? 8 : 5; ctx.stroke(path);
    ctx.strokeStyle = i === finger ? "#f4c671" : "#9cc0b3";
    ctx.lineWidth = i === finger ? 4.4 : 2.1; ctx.stroke(path);
  });
}

function drawChart(canvas, finger, pred) {
  const {ctx,width,height} = drawingSurface(canvas);
  const observed = pred.glove.map(r=>r[finger]);
  const future = [pred.hold[finger], pred.cue[finger], pred.brain[finger]];
  const vals = [...observed,...future];
  const step = Math.max(10, Math.ceil((Math.max(...vals)-Math.min(...vals))/4/10)*10);
  const min = Math.floor(Math.min(...vals)/step)*step;
  const max = Math.max(min+step,Math.ceil(Math.max(...vals)/step)*step);
  const left=39,right=width-34,top=10,bottom=height-24;
  const x=t=>left+(t+120)/240*(right-left);
  const y=v=>bottom-(v-min)/(max-min)*(bottom-top);
  ctx.font="11px Arial, sans-serif"; ctx.lineWidth=1;
  ctx.fillStyle="#f1f3ee"; ctx.fillRect(x(0),top,right-x(0),bottom-top);
  for(let v=min;v<=max;v+=step) {
    ctx.beginPath();ctx.strokeStyle="#d7dcd4";ctx.moveTo(left,y(v));ctx.lineTo(right,y(v));ctx.stroke();
    ctx.fillStyle="#425a59";ctx.textAlign="right";ctx.fillText(String(v),left-5,y(v)+4);
  }
  ctx.fillStyle="#405757";ctx.textAlign="center";
  for(const t of [-120,0,120]) ctx.fillText((t>0?"+":"")+String(t).replace("-","−")+" ms",x(t),height-5);
  ctx.strokeStyle="#849893";ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(x(0),top);ctx.lineTo(x(0),bottom);ctx.stroke();ctx.setLineDash([]);
  ctx.lineWidth=2;ctx.strokeStyle="#19464b";ctx.beginPath();
  times.forEach((t,i)=>{ if(i===0) ctx.moveTo(x(t),y(observed[i]));else ctx.lineTo(x(t),y(observed[i])); });ctx.stroke();
  times.forEach((t,i)=>{ctx.beginPath();ctx.arc(x(t),y(observed[i]),3.3,0,Math.PI*2);ctx.fillStyle="#19464b";ctx.fill();});
  const fx=x(120);
  ctx.beginPath();ctx.arc(fx,y(future[0]),5.2,0,Math.PI*2);ctx.fillStyle="#fcfbf8";ctx.fill();ctx.lineWidth=2;ctx.strokeStyle="#536f74";ctx.stroke();
  ctx.fillStyle="#a44a18";ctx.fillRect(fx-4.2,y(future[1])-4.2,8.4,8.4);
  ctx.save();ctx.translate(fx,y(future[2]));ctx.rotate(Math.PI/4);ctx.fillStyle="#006560";ctx.fillRect(-4.2,-4.2,8.4,8.4);ctx.restore();
}
