// Orthographic 3-D drawing, shaded in the laboratory coordinate system.
const LandmarkScene = (() => {
  const {plus,minus,times,mix,unit,mag}=Walk;
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const colors={body:[145,179,165], limbs:[152,185,173], leg:[125,161,156], dark:[84,119,116]};
  const presets = {Oblique:[-.67,.13], Side:[0,.02],Front:[-Math.PI/2,.02], Top:[0,Math.PI/2]};
  const light = unit([-0.2,0.45,0.85]);
  function skin(body) {
    const mesh=[];
    // Elliptical sections allow the thorax, calf, thigh, foot and forearm to
    // retain different silhouettes at every camera angle.
    function form(a,b,rings,color) {
      const axis=unit(minus(b,a));
      const across=unit(cross(axis, Math.abs(axis[0])<.88?[1,0,0]:[0,0,1]));
      const forward=unit(cross(across,axis));
      const n=16;
      const section=rings.map(([t,width,depth,offset=0])=>{
        const center=plus(mix(a,b,t),times(forward,offset));
        return Array.from({length:n},(_,i)=>{
          const u=2*Math.PI*i/n;
          return plus(plus(center,times(across,width*Math.cos(u))),times(forward,depth*Math.sin(u)));
        });
      });
      for(let k=1;k<section.length;k++)for(let i=0;i<n;i++){
        const j=(i+1)%n, face=[section[k-1][i],section[k-1][j],section[k][j],section[k][i]];
        const normal = unit(cross(minus(face[3],face[0]),minus(face[1],face[0])));
        const level=.64+.38*Math.max(0,dot(normal,light))+.08*normal[2];
        mesh.push({face,fill:'rgb('+color.map(x=>Math.round(x*level)).join(',')+')'});
      }
    }
    const root=body.pelvis;
    form(plus(root,[0,0,-92]),plus(root,[24,0,415]),[[0,37,36],[.06,108,82],[.16,143,102],
      [.30,129,91],[.45,112,83],[.60,128,92],[.78,159,103],[.89,172,94],[.94,155,81],[1,52,50]],colors.body);
    form(plus(body.neck,[0,0,-63]),plus(body.neck,[9,0,69]),[[0,59,50],[.38,49,48],[1,48,46]],colors.limbs);
    const h=body.head;
    form(plus(h,[-2,0,-101]),plus(h,[0,0,96]),[[0,19,33,14],[.09,49,65,12],[.27,65,84,6],[.46,73,92,3],[.64,75,91],[.82,67,78],[.95,42,50],[1,3,4]],colors.limbs);
    for(let s=0;s<2;s++){
      const q=body[s];
      form(q.hip,q.knee,[[0,61,63],[.12,76,76],[.32,78,76],[.58,67,69],[.8,52,52],[.94,49,48],[1.04,41,42]],colors.leg);
      form(q.knee,q.ankle,[[-.05,40,43],[.06,49,49],[.24,53,56],[.38,51,54],[.64,35,34],[.82,27,26],[1,30,29]],colors.limbs);
      const footBase=plus(q.ankle,[-45,0,-29]),front=plus(q.toe,[39,0,-4]);
      form(footBase,front,[[0,21,19],[.12,36,32],[.32,38,38],[.52,40,33],[.72,43,26],[.88,40,21],[1,13,11]],colors.limbs);
      form(q.shoulder,q.elbow,[[-.07,28,29],[.04,54,52],[.16,53,51],[.4,43,42],[.72,35,38],[1.02,29,29]],colors.body);
      form(q.elbow,q.wrist,[[-.04,28,29],[.14,37,36],[.36,35,34],[.68,27,24],[1.02,23,19]],colors.limbs);
      form(q.wrist,q.hand,[[-.03,22,17],[.25,28,22],[.58,30,20],[.85,22,16],[1,9,9]],colors.limbs);
    }
    return mesh;
  }
  function render(canvas,state) {
    const ctx=canvas.getContext('2d'); if(!ctx)return;
    const w=canvas.clientWidth,h=canvas.clientHeight,dpr=Math.min(window.devicePixelRatio||1,2);
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    const {sample,delta,yaw,tilt,selected}=state;
    const root=sample.body.pelvis, center=[root[0]+22,root[1],825];
    const scale=Math.min((h-35)/1700,(w-22)/1920);
    const sx=[Math.cos(yaw),Math.sin(yaw),0], horizontal=[-sx[1],sx[0],0];
    const sy=[-horizontal[0]*Math.sin(tilt),-horizontal[1]*Math.sin(tilt),Math.cos(tilt)];
    const sz=cross(sy,sx);
    const project=p=>{const d=minus(p,center);return [w*.5+scale*dot(d,sx),h*.52-scale*dot(d,sy),dot(d,sz)]};
    function line2(a,b,c,l=1,dash=[]) {
      ctx.beginPath();ctx.setLineDash(dash);ctx.strokeStyle=c;ctx.lineWidth=l;ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.setLineDash([]);
    }
    const note=(s,x,y,c,size=11)=>{ctx.font=size+'px Arial, sans-serif';ctx.fillStyle=c;ctx.fillText(s,x,y)};
    ctx.save();ctx.beginPath();ctx.rect(0,0,w,h);ctx.clip();
    for(let j=-6;j<=6;j++){
      const offset=j*250, color=j===0?'#3a574a':'#294237';
      line2(project([root[0]-1500,offset,0]),project([root[0]+1500,offset,0]),color);
      const x=250*Math.floor(root[0]/250)+offset;
      line2(project([x,-1500,0]),project([x,1500,0]),color);
    }
    const polys=state.mesh.map(p=>{const v=p.face.map(project);return {v,z:v.reduce((s,a)=>s+a[2],0)/4,fill:p.fill}});
    polys.sort((a,b)=>a.z-b.z);
    ctx.lineWidth=.6;
    for(const f of polys){ctx.beginPath();ctx.moveTo(f.v[0][0],f.v[0][1]);for(let i=1;i<4;i++)ctx.lineTo(f.v[i][0],f.v[i][1]);ctx.closePath();ctx.fillStyle=f.fill;ctx.fill();ctx.strokeStyle=f.fill;ctx.stroke()}
    const last=sample.observed[39];
    const sequence=[0,1,2,3,4,5].filter(v=>v!==selected).concat(selected);
    sequence.forEach(i=>{
      const focus=i===selected;ctx.globalAlpha=focus?1:.75;
      const origin=project(last[i]), target=project(plus(last[i],delta[i])), future=project(sample.next[i]);
      if(state.trails){
        ctx.beginPath();ctx.setLineDash([]);ctx.strokeStyle='#78dfbe';ctx.lineWidth=focus?2.8:1.65;
        sample.observed.forEach((f,j)=>{const p=project(f[i]);if(j===0)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1])});ctx.stroke();
      }
      if(state.future){ctx.strokeStyle='#ffb294';ctx.lineWidth=focus?2.4:1.75;const z=focus?4.4:3.4;ctx.strokeRect(future[0]-z,future[1]-z,2*z,2*z)}
      if(state.forecasts){line2(origin,target,'#dbff73',focus?2:1.35,[4,3]);const z=focus?5.8:4;ctx.beginPath();ctx.moveTo(target[0],target[1]-z);ctx.lineTo(target[0]+z,target[1]);ctx.lineTo(target[0],target[1]+z);ctx.lineTo(target[0]-z,target[1]);ctx.closePath();ctx.fillStyle='#dbff73';ctx.fill()}
      ctx.beginPath();ctx.arc(origin[0],origin[1],focus?4.5:3,0,2*Math.PI);ctx.fillStyle='#c3f9e7';ctx.fill();ctx.strokeStyle='#1d493a';ctx.lineWidth=1.25;ctx.stroke();
      if(focus){ctx.globalAlpha=1;const label=Walk.names[i], right=origin[0]<w*.68, dx=right?21:-21, tx=origin[0]+dx,ty=origin[1]-21;
        line2(origin,[tx,ty],'#c9dfcd',1);ctx.font='bold 12px Arial, sans-serif';let tw=ctx.measureText(label).width;
        const bx=right?tx:tx-tw-10;ctx.fillStyle='#18372c';ctx.fillRect(bx,ty-9,tw+10,17);note(label,bx+5,ty+4,'#ecf6df',12);
      }
    });
    ctx.restore();ctx.globalAlpha=1;
    const bar=scale*250;line2([14,26],[14+bar,26],'#9eb6a6',1.1);for(const x of [14,14+bar])line2([x,22],[x,30],'#9eb6a6');note('250 mm',14,17,'#c1d4c5',10);
    if(w>=625) {
      const left=w-178,top=62,width=147,height=68, bottom=top+height;
      const j=selected, zz=sample.observed.map(f=>f[j][2]),now=zz[39];
      const forecast=now+delta[j][2], truth=sample.next[j][2];
      const series=[...zz,forecast,truth], lo=Math.min(...series)-4,hi=Math.max(...series)+4;
      const xx=t=>left+(t+390)/590*width, yy=z=>bottom-7-(z-lo)/(hi-lo)*(height-15);
      note(Walk.names[j]+' height',left,top-13,'#d1dfd1',12);
      note(Math.round(hi)+' mm',left,top+2,'#abc0b1',9);
      line2([left,bottom],[left+width,bottom],'#577063');
      line2([xx(0),top+5],[xx(0),bottom],'#577063',1,[2,3]);
      if(state.trails){for(let k=1;k<40;k++)line2([xx(10*(k-40)),yy(zz[k-1])],[xx(10*(k-39)),yy(zz[k])],'#78dfbe',1.6)}
      const nowP=[xx(0),yy(now)],fP=[xx(200),yy(forecast)],nP=[xx(200),yy(truth)];
      if(state.forecasts){line2(nowP,fP,'#dbff73',1.3,[3,3]);ctx.save();ctx.translate(...fP);ctx.rotate(Math.PI/4);ctx.fillStyle='#dbff73';ctx.fillRect(-3,-3,6,6);ctx.restore()}
      if(state.future){ctx.strokeStyle='#ffb294';ctx.lineWidth=1.5;ctx.strokeRect(nP[0]-3.8,nP[1]-3.8,7.6,7.6)}
      note('−390 ms',left,bottom+14,'#abc0b1',10);note('now',xx(0)-8,bottom+14,'#abc0b1',10);note('+200',xx(200)-12,bottom+14,'#abc0b1',10);
    }
    const cx=w-36,cy=31;
    [[1,0,0],[0,1,0],[0,0,1]].forEach((axis,i)=>{const ex=cx+18*dot(sx,axis),ey=cy-18*dot(sy,axis);line2([cx,cy],[ex,ey],'#93b8a3');note('XYZ'[i],ex+2,ey+3,'#c8dccf',9)});
  }
  return {skin,render,presets};
})();
