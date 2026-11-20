'use strict';
(() => {
  const $=id=>document.getElementById(id), data=CorticalExample, models=CorticalModels;
  const ns='http://www.w3.org/2000/svg', dots=(x,b)=>x.reduce((s,v,i)=>s+v*b[i],0);
  const f=(n,p=3)=>Number(n.toFixed(p)).toLocaleString('en-US',{maximumFractionDigits:p,useGrouping:false});
  const make=(svg,name,attrs,text)=>{const e=document.createElementNS(ns,name);for(const [k,v] of Object.entries(attrs)) e.setAttribute(k,v);if(text!==undefined)e.textContent=text;svg.append(e);return e;};
  const tr=(cells)=>{const r=document.createElement('tr');cells.forEach((s,i)=>{const e=document.createElement(i?'td':'th');if(!i)e.scope='row';e.textContent=s;r.append(e);});return r;};
  const names={movement_cue:'Motion and cue',neural_cue:'Spikes and cue',neural_only:'Spikes only',cue_only:'Cue only',movement_only:'Motion only',linear:'Linear · all signals',velocity:'Recent velocity',stationary:'Stay in place'};
  const desc={movement_cue:'Both networks see the same handle history and the same available event cues. Only the teal forecast also reads the earlier neural spikes.',neural_cue:'Both networks read the sorted neural counts and the available event cues. The comparison omits the handle history.',neural_only:'The comparison reads only the five earlier bins of sorted spikes.',cue_only:'The comparison reads only the available event flags and directions.',movement_only:'The comparison sees the positions and earlier displacements of the handle.',linear:'A regularized linear model gives a second way to combine the same sorted counts, handle measurements and available cues.',velocity:'The comparison extends the last 40 ms of handle movement in a straight line for another 100 ms.',stationary:'The comparison keeps the handle exactly at the last measured position.'};
  let real=true,last=null;
  function secondary(h,method){
    const keys={body_control:['movement','cue'],body_markers:['movement','cue','marker'],full:['movement','cue','marker','neural']}[method];
    const x=keys.flatMap(key=>h[key].flat().map((v,j)=>(v-models.landmarks.scales[key][0][j])/models.landmarks.scales[key][1][j]));x.push(1);
    const b=models.landmarks.coef[method];
    return [0,1].map(j=>x.reduce((s,v,k)=>s+v*b[k][j],h.cv[0][j]));
  }
  function invented(epoch,offset){
    const gain=Number($('travel').value), regime=$('activity').value;
    const dx=epoch ? .18 : .08,dy=epoch ? .06 : -.14;
    const path=Array.from({length:21},(_,i)=>[gain*(dx*(i-20)/4),gain*(dy*(i-20)/4+.015*Math.sin(i*.3)-.015*Math.sin(6))]);
    const neural=[],movement=[],cue=[];
    for(let t=0;t<5;t++){
      const j=(t+1)*4,p=path[j],prior=path[j-4];
      movement.push([...p,p[0]-prior[0],p[1]-prior[1]]);
      neural.push(Array.from({length:30},(_,u)=>regime==='none'?0:(u+3*t)%17===0?(regime==='more'?3:1):(regime==='more'&&(u+t)%11===0?1:0)));
      const elapsed=offset-20+j,bump=epoch===1||elapsed>0,go=epoch===1&&elapsed>0;
      cue.push([Number(bump),0,Number(bump),Number(go),Number(go),0,Number(go)]);
    }
    return {session:data.session,unit_ids:data.unit_ids,movement,cue,neural,path,cv:[[2.5*(path[20][0]-path[16][0]),2.5*(path[20][1]-path[16][1])]]};
  }
  function svg(host,w,h,label){
    const s=document.createElementNS(ns,'svg');s.setAttribute('viewBox','0 0 '+w+' '+h);s.setAttribute('role','img');s.setAttribute('aria-label',label);host.replaceChildren(s);return s;
  }
  function plot(h,pred,other,truth){
    const points=h.path,anchor=points.at(-1), shifted=v=>v.map((x,i)=>x-anchor[i]);
    const past=points.map(shifted),future=truth?h.future.map(shifted):[];
    const span=[...past,...future,[0,0],pred,other];
    const w=Math.max(270,$('plot').clientWidth),height=Math.min(w*.64,335),pad=33;
    const xlo=Math.min(...span.map(x=>x[0])),xhi=Math.max(...span.map(x=>x[0]));
    const ylo=Math.min(...span.map(x=>x[1])),yhi=Math.max(...span.map(x=>x[1]));
    const scale=Math.min((w-2*pad)/Math.max(.12,xhi-xlo),(height-2*pad)/Math.max(.12,yhi-ylo));
    const X=x=>w/2+(x-(xlo+xhi)/2)*scale,Y=y=>height/2-(y-(ylo+yhi)/2)*scale;
    const s=svg($('plot'),w,height,'Planar handle displacement in centimetres relative to the forecast cutoff');
    make(s,'rect',{x:0,y:0,width:w,height,rx:3,fill:'#edf1eb'});
    make(s,'line',{x1:pad/2,x2:w-8,y1:Y(0),y2:Y(0),stroke:'#adbfb5','stroke-dasharray':'3 4'});
    make(s,'line',{x1:X(0),x2:X(0),y1:8,y2:height-12,stroke:'#adbfb5','stroke-dasharray':'3 4'});
    for(const [arr,color,width,dash] of [[past,'#233d45',2.2,''],[future,'#ac4923',2.8,''],[[[0,0],pred],'#09676f',2.3,'6 3'],[[[0,0],other],'#74528c',2,'2 3']]){
      if(!arr.length)continue;make(s,'polyline',{points:arr.map(p=>X(p[0])+','+Y(p[1])).join(' '),stroke:color,'stroke-width':width,fill:'none','stroke-dasharray':dash,'stroke-linecap':'round'});
    }
    make(s,'circle',{cx:X(0),cy:Y(0),r:4.5,stroke:'#172e35','stroke-width':2,fill:'#fff'});
    const px=X(pred[0]),py=Y(pred[1]);make(s,'rect',{x:px-3.8,y:py-3.8,width:7.6,height:7.6,fill:'#09676f'});
    make(s,'circle',{cx:X(other[0]),cy:Y(other[1]),r:3.7,fill:'#74528c'});
    if(truth)make(s,'circle',{cx:X(truth[0]),cy:Y(truth[1]),r:3.7,stroke:'#ac4923','stroke-width':2,fill:'white'});
    const barCandidates=[.005,.01,.025,.05,.1,.25,.5,1,2,5,10];const bar=barCandidates.filter(v=>v*scale<=w*.22).at(-1)||.001;
    make(s,'line',{x1:10,x2:10+bar*scale,y1:height-10,y2:height-10,stroke:'#172e35','stroke-width':2});
    make(s,'text',{x:10,y:height-15,fill:'#243d43','font-size':11},bar+' cm');
    make(s,'text',{x:w-8,y:height-8,fill:'#384d55','font-size':11,'text-anchor':'end'},'X →   Y ↑');
  }
  function heat(h){
    const n=Number($('unit').value),width=Math.max($('heat').clientWidth,270),pad=44,step=(width-pad-3)/30,row=20;
    const s=svg($('heat'),width,5*row+22,'Spike count of each session-local unit in five 40-millisecond bins');
    const max=Math.max(1,...h.neural.flat());
    for(let t=0;t<5;t++){
      make(s,'text',{x:pad-5,y:t*row+14,'font-size':11,fill:'#354b50','text-anchor':'end'},String((t-4)*40));
      for(let u=0;u<30;u++){
        const ratio=h.neural[t][u]/max;const color='rgb('+[220-195*ratio,235-127*ratio,226-119*ratio].map(Math.round).join(',')+')';
        make(s,'rect',{x:pad+u*step,y:t*row,width:Math.max(1,step-.7),height:row-2,fill:color,stroke:u===n?'#ac4923':'none','stroke-width':u===n?1.4:0});
      }
    }
    make(s,'text',{x:0,y:115,'font-size':11,fill:'#354b50'},'Bin end (ms)');make(s,'text',{x:width,y:115,'font-size':11,fill:'#354b50','text-anchor':'end'},'Scale: 0 to '+max+' spikes per bin');
    const counts=h.neural.map(bin=>bin[n]);
    $('unit-values').textContent=data.unit_ids[n]+', oldest to newest: '+counts.join(' · ')+' spikes per 40 ms.';
  }
  function render(){
    const epoch=Number($('event').value),offset=Number($('offset').value),m=$('comparison').value;
    last=real?data.rows.find(r=>r.epoch===epoch&&r.offset===offset):invented(epoch,offset);
    $('edit').hidden=real;$('truth-legend').hidden=!real;$('arm').hidden=!real;
    if(!last){
      for(const id of ['plot','heat','numbers','landmark-rows','unit-values'])$(id).replaceChildren();
      $('cue').textContent='This registered window did not meet the source criteria. Choose another time or event to inspect an available measurement.';$('scope').textContent='';$('comparison-note').textContent='';$('arm').hidden=true;return;
    }
    const h=last;h.session=data.session;h.unit_ids=data.unit_ids;
    const a=Area2Forecast.predict(models.neural.all,h);
    const b=m==='linear'?Area2Ridge.predict(models.linear,h):m==='velocity'?h.cv[0]:m==='stationary'?[0,0]:Area2Forecast.predict(models.neural[m],h);
    const truth=real?h.y:null;
    const cells=(n,xy)=>[n,f(xy[0]),f(xy[1]),truth?f(Math.hypot(xy[0]-truth[0],xy[1]-truth[1])):'—'];
    $('numbers').replaceChildren(tr(cells('With spikes',a)),tr(cells(names[m],b)),...(truth?[tr(['Recorded',f(truth[0]),f(truth[1]),'—'])]:[]));
    $('comparison-note').textContent=desc[m];$('scope').textContent=real?'The displayed models use one fixed training seed. This entire original trial was held out, including both events.':'The inputs are invented. The models use weights fitted to the recorded training trials.';
    const c=h.cue[4], angle=(cos,sin)=>Math.round((Math.atan2(sin,cos)*180/Math.PI+360)%360)+'°';
    const cues=[c[0]?'perturbation '+angle(c[1],c[2]):'perturbation not yet available',c[3]?'target '+angle(c[4],c[5]):'target not yet available',c[6]?'go cue visible':'no prior go cue'];
    $('cue').textContent=(real?'Original trial '+data.trial+', '+f((h.k-data.start)*.01,2)+' s from its start. ':'Invented example. ')+'At the last bin end: '+cues.join(' · ')+'.';
    $('landmark-rows').replaceChildren();
    if(real && h.marker && h.markerGood){
      for(const [k,label] of [['body_control','Handle and cue'],['body_markers','Add two markers'],['full','Also add spikes']])$('landmark-rows').append(tr(cells(label,secondary(h,k))));
    }else $('arm').hidden=true;
    plot(h,a,b,truth);heat(h);
  }
  data.unit_ids.forEach((v,i)=>$('unit').add(new Option(v,i)));
  $('trial-label').textContent='Original trial '+data.trial+' · one session';
  $('finding').textContent=data.summary.finding;$('timing').textContent=data.summary.timing;
  $('results').replaceChildren(...data.summary.methods.map(v=>tr([v.name,f(v.both),f(v.bump),f(v.reach)])));
  document.querySelectorAll('input[name=mode]').forEach(el=>el.addEventListener('change',()=>{real=el.value==='real';render();}));
  for(const id of ['event','offset','comparison','travel','activity','unit'])$(id).addEventListener('change',render);
  if(location.protocol==='file:')$('download').hidden=true;
  render();let old=$('plot').clientWidth;
  new ResizeObserver(()=>{if($('plot').clientWidth!==old){old=$('plot').clientWidth;render();}}).observe($('plot'));
})();
