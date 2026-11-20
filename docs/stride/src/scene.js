// Orthographic lab-frame camera adapted from the NeuroTranslation whole-body viewer.
function sceneBounds(motions) {
  const lower = [Infinity,Infinity,Infinity], upper = [-Infinity,-Infinity,-Infinity];
  for (const motion of motions) for (const frame of motion) for (const point of frame) {
    point.forEach((n,i) => {lower[i]=Math.min(lower[i],n);upper[i]=Math.max(upper[i],n);});
  }
  return {lower,upper};
}
function camera(bounds,width,height,yaw,pitch) {
  const rad = Math.PI/180, a=yaw*rad, b=pitch*rad;
  const right=[Math.cos(a),-Math.sin(a),0], down=[Math.sin(a)*Math.sin(b),Math.cos(a)*Math.sin(b),-Math.cos(b)];
  const near=[Math.sin(a)*Math.cos(b),Math.cos(a)*Math.cos(b),Math.sin(b)];
  const centre=bounds.lower.map((v,i)=>v/2+bounds.upper[i]/2);
  const half=bounds.upper.map((v,i)=>v/2-bounds.lower[i]/2);
  const span=axis=>2*axis.reduce((s,v,i)=>s+Math.abs(v)*half[i],0);
  const scale=Math.min((width-36)/Math.max(80,span(right)),(height-32)/Math.max(80,span(down)));
  const dot=(p,axis)=>axis.reduce((s,v,i)=>s+v*(p[i]-centre[i]),0);
  return {project:p=>[width/2+dot(p,right)*scale,height/2+dot(p,down)*scale,dot(p,near)], right,down};
}
function renderScene(canvas,scene,state,schema) {
  const {width,height}=canvas.getBoundingClientRect();
  if (width < 50 || height < 50) return;
  const dpr=Math.min(devicePixelRatio || 1,2), w=Math.round(width*dpr), h=Math.round(height*dpr);
  if(canvas.width!==w || canvas.height!==h){canvas.width=w;canvas.height=h;}
  const ctx=canvas.getContext('2d');ctx.setTransform(w/width,0,0,h/height,0,0);ctx.clearRect(0,0,width,height);
  if(!scene)return;
  const {project,right,down}=camera(scene.bounds,width,height,state.yaw,state.pitch);
  function line(p,q,color,thickness,dash=[]) {
    ctx.lineWidth=thickness;ctx.strokeStyle=color;ctx.setLineDash(dash);
    ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.stroke();
  }
  const {upper,lower}=scene.bounds;
  const span=Math.max(upper[0]-lower[0],upper[1]-lower[1]);
  const step=250*Math.max(1,Math.ceil(span/4000)),z=lower[2];
  const from=lower.slice(0,2).map(v=>step*(Math.floor(v/step)-2));
  const to=upper.slice(0,2).map(v=>step*(Math.ceil(v/step)+2));
  // Limit grid work even for an out-of-domain upload.
  for(let j=0;j<24;j++){
    const x=from[0]+j*step,y=from[1]+j*step;
    if(x<=to[0])line(project([x,from[1],z]),project([x,to[1],z]),'#274246',1);
    if(y<=to[1])line(project([from[0],y,z]),project([to[0],y,z]),'#274246',1);
  }
  const ranges=state.frame<=10 ? [{kind:'observed',motion:scene.history.positionsMm,index:state.frame}] : [];
  if(state.frame>10) {
    if(state.last)ranges.push({kind:'last',motion:scene.history.positionsMm,index:10});
    if(state.model)ranges.push({kind:'model',motion:scene.forecast.positionsMm,index:state.frame-11});
    if(state.alternative)ranges.push({kind:'alternative',motion:scene.baseline.positionsMm,index:state.frame-11});
    if(state.reference && scene.reference)ranges.push({kind:'reference',motion:scene.reference.positionsMm,index:state.frame-11});
  }
  const styles={
    observed:{colour:'#92ddde',thick:3,dash:[]},last:{colour:'#69a9ac',thick:2,dash:[2,5]},
    model:{colour:'#f8ce68',thick:3.1,dash:[]},alternative:{colour:'#d3a7ff',thick:2.4,dash:[6,4]},
    reference:{colour:'#ecfcf1',thick:1.8,dash:[2,3]}
  };
  const r=Math.min(4.8,Math.max(3.2,width/145)),items=[];
  for(const {kind,index,motion} of ranges) {
    const {colour,thick,dash}=styles[kind],dots=motion[index].map(project);
    const path=motion.map(frame=>project(frame[state.point]));
    for(let i=1;i<path.length;i++)line(path[i-1],path[i],colour,.9,[2,3]);
    for (const [a,b] of schema.edges) items.push({z:(dots[a][2]+dots[b][2])/2,paint:()=>line(dots[a],dots[b],colour,thick,dash)});
    for(const [i,p] of dots.entries()) items.push({z:p[2]+.0001,paint:()=>{
      ctx.beginPath();ctx.setLineDash([]);ctx.arc(p[0],p[1],r+(kind==='reference'?1.55:0),0,Math.PI*2);
      if(kind!=='reference'){ctx.fillStyle=colour;ctx.fill();}
      ctx.strokeStyle=kind==='reference'?colour:'#183336';ctx.lineWidth=kind==='reference'?1.5:1;ctx.stroke();
      if(i===state.point){ctx.beginPath();ctx.arc(p[0],p[1],r+3,0,Math.PI*2);ctx.strokeStyle=colour;ctx.lineWidth=.9;ctx.stroke();}
    }});
  }
  ctx.lineCap='round';items.sort((a,b)=>a.z-b.z);items.forEach(item=>item.paint());
  const ox=31,oy=33;
  ctx.font='10px Arial, sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
  for(let i=0;i<3;i++){line([ox,oy],[ox+right[i]*17,oy+down[i]*17],'#cedeD7',1);ctx.fillStyle='#d9e7e0';ctx.fillText('XYZ'[i],ox+right[i]*25,oy+down[i]*25);}
  return step;
}
