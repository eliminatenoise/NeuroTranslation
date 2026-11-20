(function (host) {
  'use strict';
  const joint = '#13654a', other = '#76518e', history = '#89968b';
  function surface(canvas) {
    if (!canvas.clientWidth || !canvas.clientHeight) return null;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * ratio);
    canvas.height = Math.round(h * ratio);
    const ctx = canvas.getContext('2d');
    ctx.scale(ratio, ratio);
    ctx.font = '11px Arial, sans-serif';
    ctx.lineJoin = 'round';
    return {ctx, w, h};
  }
  function line(ctx, points, stroke, width, dash = []) {
    ctx.beginPath();
    points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width;
    ctx.setLineDash(dash);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  function dot(ctx, p, color, radius, outline = false) {
    ctx.beginPath();
    ctx.arc(...p, radius, 0, Math.PI * 2);
    ctx.fillStyle = outline ? '#fffefa' : color;
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  function tickStep(value) {
    const power = 10 ** Math.floor(Math.log10(Math.max(1e-12, value)));
    const mantissa = value / power;
    return power * (mantissa <= 1 ? 1 : mantissa <= 2 ? 2 : mantissa <= 5 ? 5 : 10);
  }
  function drawPath(canvas, input, j, b, view, sample) {
    const surfaceInfo = surface(canvas);
    if (!surfaceInfo) return;
    const {ctx, w, h} = surfaceInfo;
    const last = input.sacrum_mm.at(-1);
    const past = input.sacrum_mm.slice(-33).map(row => row.map((v, k) => v - last[k]));
    const project = view === '3d' ? ([x, y, z]) => [(x - z) / Math.SQRT2, (x + z) / Math.sqrt(6) - 2 * y / Math.sqrt(6)] : row => [row[Number(view[0])], -row[Number(view[1])]];
    const points = [...past, ...j, ...b].map(project);
    const [minX, maxX, minY, maxY] = [Math.min(...points.map(p => p[0])), Math.max(...points.map(p => p[0])), Math.min(...points.map(p => p[1])), Math.max(...points.map(p => p[1]))];
    const left = 12, right = w - 50, top = 13, bottom = h - 28;
    const scale = Math.min((right - left) / Math.max(0.001, maxX - minX), (bottom - top) / Math.max(0.001, maxY - minY)) * .88;
    const toPx = ([x, y]) => [(left + right) / 2 + (x - (minX + maxX) / 2) * scale, (top + bottom) / 2 + (y - (minY + maxY) / 2) * scale];
    const pp = row => toPx(project(row));
    const origin = toPx([0,0]);
    const step = tickStep(24 / scale), stepPx = step * scale;
    for (let x = origin[0] % stepPx; x <= w; x += stepPx) line(ctx, [[x,top],[x,bottom]], '#edf0e8', 1);
    for (let y = origin[1] % stepPx; y <= bottom; y += stepPx) line(ctx, [[0,y],[w,y]], '#edf0e8', 1);
    line(ctx, past.map(pp), history, 2);
    line(ctx, [origin,...j.map(pp)], joint, 3.3);
    line(ctx, [origin,...b.map(pp)], other, 2.3, [5,4]);
    dot(ctx, origin, '#525f54', 3.1, true);
    dot(ctx, pp(b[sample-1]), other, 4.4, true);
    dot(ctx, pp(j[sample-1]), joint, 2.6);
    const scaleBar = tickStep(33 / scale);
    line(ctx, [[8,h-11],[8+scaleBar*scale,h-11]], '#627165', 1.5);
    ctx.fillStyle = '#4a5a4b';
    ctx.fillText(Number(scaleBar.toPrecision(3)) + ' mm', 13 + scaleBar*scale, h-7);
    const labels = ['ML','SI','AP'];
    const originAxis = [w-31,bottom-23];
    for (let k=0; k<3; k++) {
      if (view !== '3d' && !view.includes(String(k))) continue;
      const v = [0,0,0]; v[k] = 1;
      const [a,c] = project(v), tip = [originAxis[0]+a*22, originAxis[1]+c*22];
      line(ctx, [originAxis,tip], '#516458', 1.25);
      ctx.fillStyle = '#4b5c4f';ctx.font = '10px Arial, sans-serif';
      ctx.fillText(labels[k],tip[0]+(a<0?-14:1),tip[1]+(c<0?-2:9));
    }
  }
  function drawSignal(canvas, input, channel) {
    const s = surface(canvas);
    if (!s) return;
    const {ctx,w,h} = s;
    const values = input.leg_uv.map(row => row[channel]);
    const peak = Math.max(.001,...values.map(Math.abs));
    const y = v => (h-22)/2 - v/peak*(h-38)/2 + 2;
    line(ctx, [[0,y(0)],[w,y(0)]], '#c0c9bd', 1);
    line(ctx, values.map((v,i) => [i*(w-2)/159+1,y(v)]), joint, 1.4);
    ctx.fillStyle='#4a5a4b';
    ctx.fillText('±' + Number(peak.toPrecision(3)) + ' µV', 4, 12);
    ctx.fillText('−621.1 ms', 2, h-3);
    ctx.textAlign='right'; ctx.fillText('Cutoff · 0 ms', w-2, h-3);
  }
  host.MuscleMotionPlots = {drawPath, drawSignal};
})(globalThis);
