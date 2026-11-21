/* Orthographic views of the same three measured world coordinates. */
(() => {
  "use strict";
  function project(p, view) {
    if (view === "xy") return [p[0], -p[1]];
    if (view === "xz") return [p[0], -p[2]];
    if (view === "yz") return [p[1], -p[2]];
    return [(p[0] - p[1]) / Math.sqrt(2), (p[0] + p[1] - 2 * p[2]) / Math.sqrt(6)];
  }
  function niceScale(target) {
    const magnitude = 10 ** Math.floor(Math.log10(target));
    return [1, 2, 5, 10].filter(n => n * magnitude <= target).at(-1) * magnitude;
  }
  function draw(canvas, traces, horizon, view) {
    const box = canvas.getBoundingClientRect();
    const width = Math.max(16, box.width), height = Math.max(16, box.height);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const zero = [0,0,0];
    const points = [zero, ...traces.flatMap(trace => trace.points.filter(Boolean))];
    const uv = points.map(p => project(p, view));
    const xs = uv.map(p=>p[0]), ys = uv.map(p=>p[1]);
    const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    const padX = Math.min(50, width * .13), padY = 30;
    const span = Math.max(maxX-minX,maxY-minY,1e-8);
    const scale = Math.min((width - 2 * padX) / Math.max(maxX-minX, span*.15),
                           (height - 2 * padY - 24) / Math.max(maxY-minY, span*.15));
    function screen(point) {
      const [u,v] = project(point,view);
      return [width/2+(u-(minX+maxX)/2)*scale, (height-18)/2+(v-(minY+maxY)/2)*scale];
    }
    function line(a,b,color,thickness=1) {
      ctx.strokeStyle=color; ctx.lineWidth=thickness; ctx.beginPath();
      ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
    }
    const origin=screen(zero);
    const unit=niceScale(Math.min(width*.17,95)/scale);
    const grid=unit*scale;
    ctx.save();
    for(let x=origin[0]%grid; x<width; x+=grid) line([x,0],[x,height-23],"#2c4546");
    for(let y=origin[1]%grid; y<height-23; y+=grid) line([0,y],[width,y],"#2c4546");
    ctx.restore();
    for (const trace of traces) {
      ctx.strokeStyle=trace.color;ctx.fillStyle=trace.color;ctx.lineWidth=trace.kind==="input"?3:2;
      ctx.setLineDash(trace.kind === "input" ? [] : trace.kind === "forecast" ? [7,4] : [2,4]);
      const path=trace.kind==="input" ? trace.points : [zero,...trace.points];
      ctx.beginPath(); let started=false;
      for(const p of path) {
        if (!p) {started=false; continue;}
        if (started) ctx.lineTo(...screen(p)); else ctx.moveTo(...screen(p));
        started=true;
      }
      ctx.stroke();ctx.setLineDash([]);
      trace.points.forEach((p,i)=>{
        if(!p) return;
        const [x,y]=screen(p);
        const active=i===horizon && trace.kind!=="input";
        const r=trace.kind==="input"?3:active?6:4;
        ctx.fillStyle=trace.color;ctx.strokeStyle=trace.color;ctx.lineWidth=2;
        ctx.beginPath();
        if(trace.kind==="forecast") {ctx.moveTo(x,y-r);ctx.lineTo(x+r,y);ctx.lineTo(x,y+r);ctx.lineTo(x-r,y);ctx.closePath();}
        else if(trace.kind==="input") {ctx.rect(x-r,y-r,r*2,r*2);}
        else ctx.arc(x,y,r,0,2*Math.PI);
        if(trace.kind==="recorded" || trace.kind==="original") ctx.stroke(); else ctx.fill();
        if(active){ctx.beginPath();ctx.arc(x,y,r+4,0,2*Math.PI);ctx.lineWidth=1;ctx.stroke();}
      });
    }
    ctx.font="11px Arial, sans-serif";ctx.fillStyle="#d1e1db";ctx.textAlign="left";
    const x=8,y=height-9;
    line([x,y],[x+grid,y],"#d1e1db",2);line([x,y-3],[x,y+3],"#d1e1db",1);
    line([x+grid,y-3],[x+grid,y+3],"#d1e1db",1);
    const precision=Math.max(0,-Math.floor(Math.log10(unit)));
    ctx.fillText(unit.toFixed(Math.min(precision,10))+" m",x+grid+6,y+3);
    // The axis key shows camera directions, independent of the display's scale bar.
    const axisAt=[width-51,height-28];
    [[1,0,0],[0,1,0],[0,0,1]].forEach((p,i)=>{
      const a=project(p,view);
      if(Math.hypot(...a)<.1)return;
      const end=[axisAt[0]+a[0]*22,axisAt[1]+a[1]*22];
      line(axisAt,end,"#a6c4c5");ctx.fillText(["X","Y","Z"][i],end[0]+a[0]*5-3,end[1]+a[1]*5+3);
    });
  }
  globalThis.TargetReachPlot=Object.freeze({draw});
})();
