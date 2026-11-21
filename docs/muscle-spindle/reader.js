'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const {trial,rows,summary,synthetic} = SpindleRecording;
  const {neural,poisson,secondary} = SpindleModels;
  const ns='http://www.w3.org/2000/svg';
  let timer=null, mode='recorded';
  const f=(v,n=3)=>Number(v.toFixed(n)).toLocaleString('en-US',{maximumFractionDigits:n,useGrouping:false});
  const notes={
    all:'The Transformer uses all five measurements in each earlier bin: mean force, mean position, their two rates of change and the spike count.',
    history:'This version learned from the five earlier spike counts alone.',
    mechanics:'This version learned from force and apparatus position, including how quickly they changed.',
    force:'This version learned from tendon force and its rate of change.',
    position:'This version learned from apparatus position and its rate of change.',
    glm:'The Poisson model combines the earlier signals with fitted weights. An exponential converts their sum into a positive expected count.',
    recent:'The recent-rate rule repeats the mean spike count across the five earlier bins.'
  };
  function makeRow(cells){
    const row=document.createElement('tr');
    cells.forEach((v,i)=>{const c=document.createElement(i===0?'th':'td');if(!i)c.scope='row';c.textContent=v;row.append(c);});
    return row;
  }
  function atTime(v){const ms=Math.round(v*1000);return f(ms===0?0:ms,0)+' ms';}
  function glm(model,input){
    if (model.zero_boundary) return 0;
    let value=model.intercept;
    for(let t=0;t<5;t++)model.fields.forEach((col,j)=>{
      const z=(input[t][col]-model.mean[j])/model.scale[j];value+=model.coefficients[t][j]*Math.max(-10,Math.min(10,z));
    });
    return Math.exp(value);
  }
  function mechanics(input,kind){
    const x=input.flatMap((bin,t)=>bin.map((v,j)=>kind==='mechanics'&&j===4?0:(v-secondary.mean[t][j])/secondary.scale[t][j]));
    x.push(1);
    return [0,1].map(j=>x.reduce((sum,v,i)=>sum+v*secondary.coefficients[kind][i][j],input[4][j+2]*.02));
  }
  function plottedSignal(svg,x,y0,h,arr,name,color,total){
    const [lo,hi]=[Math.min(...arr),Math.max(...arr)];
    const y=v=>y0+h-3-(v-lo)/Math.max(hi-lo,1e-12)*(h-10);
    const line=add(svg,'path',{d:'',fill:'none',stroke:color,'stroke-width':1.8});
    const points=arr.map((v,i)=>(i?'L':'M')+x(i*total/(arr.length-1)).toFixed(2)+','+y(v).toFixed(2));
    line.setAttribute('d',points.join(' '));
    add(svg,'text',{x:6,y:y0+4,fill:color},name);
  }
  function add(svg,tag,attrs,txt){
    const el=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);
    if(txt!==undefined)el.textContent=txt;svg.append(el);return el;
  }
  function chart(row){
    const w=Math.max(274,Math.floor($('trace').clientWidth)),h=198,l=6,r=w-8,duration=trial.duration;
    const x=sec=>l+sec/duration*(r-l);
    const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 '+w+' '+h);svg.setAttribute('role','img');
    svg.setAttribute('aria-label','Recorded tendon force, apparatus position and detected spike times across the whole stretch. Cutoff '+atTime(row.time)+'.');
    for (const [a,b,col] of [[row.time-.1,row.time,'#c5e6df'],[row.time,row.time+.02,'#f7d5b9']])
      add(svg,'rect',{x:x(a),y:1,width:Math.max(1,x(b)-x(a)),height:h-23,fill:col});
    const data=trial.preview;
    for(const [top,v,name,color] of [[14,data.force,'Tendon force','#13616b'],[78,data.position,'Apparatus position','#4c4877']])
      plottedSignal(svg,x,top,45,v,name,color,duration);
    add(svg,'text',{x:6,y:143,fill:'#854021'},'Detected spikes');
    for(const time of trial.spikes)add(svg,'line',{x1:x(time),x2:x(time),y1:148,y2:167,stroke:'#a1491c','stroke-width':1});
    add(svg,'line',{x1:x(row.time),x2:x(row.time),y1:1,y2:174,stroke:'#203a3a','stroke-dasharray':'3 3'});
    add(svg,'text',{x:l,y:190,fill:'#46565b'},'0 s');
    add(svg,'text',{x:r,y:190,'text-anchor':'end',fill:'#46565b'},f(duration,3)+' s');
    $('trace').replaceChildren(svg);
  }
  function invented(){
    const changes={rise:1,fall:-1,hold:0},counts={irregular:[0,2,0,1,3],steady:[1,1,1,1,1],none:[0,0,0,0,0]};
    const rates=[changes[$('force').value]*synthetic.forceRate,changes[$('position').value]*synthetic.positionRate];
    const endpoints=[],input=[];
    for(let t=0;t<5;t++){
      const last=synthetic.origin.map((v,j)=>v+(t-2)*.02*rates[j]);
      const mean=last.map((v,j)=>v-(.02-synthetic.sampleInterval)*.5*rates[j]);
      const count=counts[$('counts').value][t];
      input.push([...mean,...rates,count]);endpoints.push([...last,...rates,count]);
    }
    return {input,endpoints};
  }
  function render(){
    const index=Number($('cursor').value),record=rows[index],real=mode==='recorded';
    $('recorded').hidden=!real;$('invented').hidden=real;
    const event=real?record:invented(),method=$('method').value;
    const expected=method==='glm'?glm(poisson,event.input):method==='recent'?event.input.reduce((s,b)=>s+b[4],0)/5:
      SpindleCount.predictCount(neural[method],event.input);
    $('prediction').textContent=f(expected,3);$('observation').textContent=real?String(record.count):'—';
    $('method-note').textContent=notes[method];$('time').value=atTime(record.time);
    $('clock').textContent='Elapsed time starts at '+f(trial.start,3)+' s on the original archive clock. This cutoff is '+f(trial.start+record.time,3)+' s on that clock. The history runs from '+atTime(record.time-.1)+' to '+atTime(record.time)+'. The following 20 ms contains '+record.count+(record.count===1?' detected spike.':' detected spikes.');
    if(real)chart(record);
    $('previous').disabled=index===0;$('next').disabled=index===rows.length-1;
    const noSpikes=mechanics(event.endpoints,'mechanics'),withSpikes=mechanics(event.endpoints,'combined');
    $('delta').replaceChildren(...['Tendon force','Position'].map((name,j)=>makeRow([name,f(noSpikes[j],5),f(withSpikes[j],5),real?f(record.delta[j],5):'—'])));
    $('inputs').replaceChildren(...event.input.map((bin,i)=>makeRow([String((i-4)*20),...bin.map((v,j)=>j===4?String(v):f(v,5))])));
  }
  function stop(){
    if(timer!==null){clearInterval(timer);timer=null;}
    $('play').textContent='Play';
  }
  function set(i){$('cursor').value=String(Math.min(rows.length-1,Math.max(0,i)));render();}
  $('cursor').max=String(rows.length-1);$('cursor').value='0';
  $('duration').textContent=f(trial.duration,3)+' s · rat sensory fiber';
  $('cursor').addEventListener('input',()=>{stop();render();});
  $('previous').onclick=()=>{stop();set(+$('cursor').value-1);};
  $('next').onclick=()=>{stop();set(+$('cursor').value+1);};
  $('play').onclick=()=>{
    if(timer!==null){stop();return;}
    if(+$('cursor').value>=rows.length-1)set(0);
    $('play').textContent='Pause';
    timer=setInterval(()=>{set(+$('cursor').value+1);if(+$('cursor').value===rows.length-1)stop();},100);
  };
  document.querySelectorAll('input[name=mode]').forEach(el=>el.onchange=()=>{stop();mode=el.value;render();});
  for(const id of ['method','force','position','counts'])$(id).onchange=render;
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  $('finding').textContent=summary.finding;$('scope').textContent=summary.scope;
  $('scores').replaceChildren(...summary.scores.map(v=>makeRow([v.name,f(v.mae,4),f(v.deviance,4)])));
  if(location.protocol==='file:')$('download').hidden=true;
  render();
  let previousWidth=$('trace').clientWidth;
  new ResizeObserver(()=>{const width=$('trace').clientWidth;if(width && width!==previousWidth){previousWidth=width;render();}}).observe($('trace'));
})();
