(() => {
  'use strict';
  const el=id=>document.getElementById(id), box=el('stage'), slider=el('scrub');
  const pack=JSON.parse(el('data').textContent), schema=pack.schema;
  const names=Object.fromEntries(schema.siteNames.map((s,i)=>[i,s.replace(/([A-Z])/g,' $1').toLowerCase()]));
  const parameters={};
  function weights(id) {return parameters[id] ??= loadParameters(pack.models[id]);}
  const state={frame:16,point:15,yaw:-35,pitch:12,last:true,model:true,alternative:false,reference:false};
  let scene=null,clock=0,drag=null,revision=0,activeExample=null,playFromStart=true;
  const layers=['last','model','alternative','reference'];
  const activity=word=>word[0].toUpperCase()+word.slice(1);
  function stop() {
    cancelAnimationFrame(clock);clock=0;
    el('play').textContent=state.frame===22?'Replay':'Play';
  }
  function setStatus(message,error=false) {el('status').textContent=message;el('status').classList.toggle('error',error);}
  function clear(message,error=false) {
    stop();scene=null;el('readout').replaceChildren();el('comparison').textContent='';el('phase').textContent='No forecast';
    el('grid').textContent='Lab coordinates · +Z up';el('time').textContent='—';el('view-label').textContent='';
    for(const id of ['play','scrub','point','reset','method',...layers])el(id).disabled=true;
    renderScene(box,null,state,schema);setStatus(message,error);
  }
  function readout(label,frame) {
    const p=document.createElement('span'), point=frame[state.point];
    p.textContent=label+' · '+point.map(n=>n.toFixed(1)).join(', ')+' mm';
    p.dataset.xyz=point.join(',');p.dataset.label=label;el('readout').append(p);
  }
  function draw() {
    if(!scene)return;
    const step=renderScene(box,scene,state,schema);
    el('grid').textContent='Lab +Z up · '+(step/10).toLocaleString()+' cm grid';
    const t=state.frame-10,past=t<=0, offset=t/20;
    slider.value=state.frame;el('time').textContent=(t>0?'+':'')+offset.toFixed(2)+' s';
    el('phase').textContent=t<0?'Observed movement':t===0?'Last observed frame':'Forecast · '+scene.action;
    el('view-label').textContent=past?'Recorded history':'Future frame '+t+' / 12';
    el('readout').replaceChildren();
    if(past){readout('Observed',scene.history.positionsMm[state.frame]);return;}
    if(state.last)readout('Last observed',scene.history.positionsMm[10]);
    if(state.model)readout('Forecast',scene.forecast.positionsMm[t-1]);
    if(state.alternative)readout('Comparison',scene.baseline.positionsMm[t-1]);
    if(state.reference && scene.reference)readout('Recorded',scene.reference.positionsMm[t-1]);
  }
  function compareCaption() {
    if(!scene)return;
    const s=[];
    if(state.alternative) s.push(el('method').value==='ridge'?'The linear model fits the same eleven poses without a word.':'The second transformer was trained on movement alone.');
    if(state.reference && activeExample) s.push('Hollow rings follow the recorded '+activeExample.action+' in training clip '+activeExample.id+'.');
    if(!activeExample)s.push('A local input has no verified later recording here.');
    el('comparison').textContent=s.join(' ');
  }
  function updateBounds() {
    const motions=[scene.history.positionsMm,scene.forecast.positionsMm];
    if(state.alternative)motions.push(scene.baseline.positionsMm);
    if(state.reference && scene.reference)motions.push(scene.reference.positionsMm);
    scene.bounds=sceneBounds(motions);
  }
  function setBaseline() {
    const method=el('method').value;
    scene.baseline=makeForecast(scene.history,scene.action,method,weights(method));
  }
  function run(history,action,example) {
    stop();
    try {
      const forecast=makeForecast(history,action,'conditional',weights('conditional'));
      scene={history,action,forecast,reference:example?.observedFuture??null};
      activeExample=example;
      state.frame=16;playFromStart=true;
      el('action').value=action;state.reference=false;el('reference').checked=false;
      if(state.alternative)setBaseline();
      updateBounds();
      for(const id of ['play','scrub','point','reset','method',...layers])el(id).disabled=false;
      el('reference').disabled=!example;
      el('play').textContent='Play';
      setStatus(example?'Forecast from 11 frames of CMU '+example.id+' ('+example.action+', training recording).':'Forecast from your eleven observed frames.');
      compareCaption();draw();
    } catch(err) {clear(err.message,true);}
  }
  function select() {
    revision++;
    const id=el('example').value;
    const custom=id==='custom';el('drop').hidden=!custom;
    if(custom){activeExample=null;clear('Paste a window or choose a local JSON file.');return;}
    const s=pack.examples[id];run(s.history,s.action,s);
  }
  function edit() {
    revision++;activeExample=null;clear('Apply the edited coordinates to make a new forecast.');
  }
  function parsePacket(text) {
    if (!text.trim())throw Error('Paste a pose window or choose a local JSON file.');
    if(text.length>300000)throw Error('Use one pose window under 300 KB.');
    let data;try{data=JSON.parse(text);}catch{throw Error('This is not valid JSON. Download an example input for the expected format.');}
    if(!data || typeof data!=='object' || Array.isArray(data))throw Error('Use a JSON object with action, timesS and positionsMm.');
    const input=data.history ?? data;
    for(const p of [data,input]) {
      if(!p || typeof p!=='object')throw Error('Use a history object with timesS and positionsMm.');
      if(('units'in p && p.units!=='mm') || ('sampleRateHz'in p && p.sampleRateHz!==20) ||
        ('siteNames'in p && JSON.stringify(p.siteNames)!==JSON.stringify(schema.siteNames)) ||
        ('axes'in p && p.axes!==schema.axes))throw Error('Use the example’s site order, millimetres, 20 Hz and right-handed lab frame (+Z up).');
    }
    validateWindow(input,data.action);
    return {action:data.action,history:{positionsMm:input.positionsMm,timesS:input.timesS}};
  }
  function apply() {
    revision++;
    try{const parsed=parsePacket(el('packet').value);run(parsed.history,parsed.action,null);}
    catch(e){clear(e.message,true);}
  }
  async function fileInput(file) {
    edit();const at=revision;
    if(!file){el('packet').value='';return;}
    el('packet').value='';
    if(file.size>300000){clear('Use one pose window under 300 KB.',true);return;}
    try {
      const text=await file.text();
      if(at!==revision || el('example').value!=='custom')return;
      el('packet').value=text;apply();
    } catch {if(at===revision)clear('The local file could not be read.',true);}
  }
  const originalPage='<!doctype html>\n'+document.documentElement.outerHTML;
  el('save').href=URL.createObjectURL(new Blob([originalPage],{type:'text/html;charset=utf-8'}));
  for(const [id,s] of Object.entries(pack.examples))el('example').add(new Option(activity(s.action)+' · CMU '+s.id,id));
  el('example').add(new Option('My pose window','custom'));
  el('example').addEventListener('change',select);el('packet').addEventListener('input',edit);
  el('apply').addEventListener('click',apply);el('file').addEventListener('change',e=>fileInput(e.target.files[0]));
  const drop=el('drop');
  for(const event of ['dragover','dragenter'])drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add('over');});
  drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
  drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');fileInput(e.dataTransfer.files[0]);});
  el('action').addEventListener('change',()=>{if(scene)run(scene.history,el('action').value,activeExample);});
  for(const id of layers)el(id).addEventListener('change',()=>{
    if(!scene)return;state[id]=el(id).checked;
    if(id==='alternative' && state.alternative && !scene.baseline)setBaseline();
    updateBounds();compareCaption();draw();
  });
  el('method').addEventListener('change',()=>{if(!scene)return;state.alternative=el('alternative').checked=true;setBaseline();updateBounds();compareCaption();draw();});
  schema.siteNames.forEach((_,i)=>{
    el('point').add(new Option(names[i],i));
    const item=document.createElement('li');item.textContent=names[i]+' ('+schema.sites[i].join(', ')+')';el('site-order').append(item);
  });
  el('point').value=state.point;el('point').addEventListener('change',()=>{state.point=Number(el('point').value);draw();});
  slider.addEventListener('input',()=>{state.frame=Number(slider.value);playFromStart=false;stop();draw();});
  el('play').addEventListener('click',()=>{
    if(!scene)return;
    if(clock){stop();return;}
    if(playFromStart || state.frame===22){state.frame=0;draw();}
    playFromStart=false;
    const start=performance.now(),from=state.frame;el('play').textContent='Pause';
    function tick(now) {
      const frame=Math.min(22,from+Math.floor((now-start)/50));
      if(frame!==state.frame){state.frame=frame;draw();}
      if(frame===22)stop();else clock=requestAnimationFrame(tick);
    }
    clock=requestAnimationFrame(tick);
  });
  const turn=(y,p)=>{state.yaw=((y%360)+360)%360;state.pitch=Math.max(-65,Math.min(65,p));draw();};
  el('reset').addEventListener('click',()=>turn(-35,12));
  box.addEventListener('keydown',e=>{
    if(!scene || !['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(e.key))return;
    e.preventDefault();
    if(e.key==='Home'){turn(-35,12);return;}
    const s=e.shiftKey?15:5;
    turn(state.yaw+(e.key==='ArrowRight'?s:e.key==='ArrowLeft'?-s:0),state.pitch+(e.key==='ArrowUp'?s:e.key==='ArrowDown'?-s:0));
  });
  box.addEventListener('pointerdown',e=>{if(!scene || !e.isPrimary || e.button!==0)return;
    box.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.clientX,y:e.clientY,a:state.yaw,b:state.pitch};});
  box.addEventListener('pointermove',e=>{if(drag?.id===e.pointerId)turn(drag.a+(e.clientX-drag.x)*.5,drag.b+(e.clientY-drag.y)*.35);});
  box.addEventListener('lostpointercapture',()=>{drag=null;});
  new ResizeObserver(draw).observe(box);window.addEventListener('pagehide',stop);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  el('sample').addEventListener('click',()=>{
    const s=activeExample||Object.values(pack.examples)[0];
    const url=URL.createObjectURL(new Blob([JSON.stringify({action:s.action,...s.history,units:'mm',sampleRateHz:20,axes:schema.axes,siteNames:schema.siteNames,source:s.source},null,1)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='example-'+s.action+'-input.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);
  });
  el('outcome').textContent=pack.study.outcome;el('measure').textContent=pack.study.measure;el('counts').textContent=pack.study.counts;
  const table=document.createElement('table'),head=table.createTHead().insertRow();
  for(const label of ['Method','Body error (mm)']){const c=document.createElement('th');c.scope='col';c.textContent=label;head.append(c);}
  const body=table.createTBody();
  for(const [name,n] of pack.study.rows){const row=body.insertRow(),th=document.createElement('th');th.scope='row';th.textContent=name;row.append(th);row.insertCell().textContent=n.toFixed(1);}
  el('scores').append(table);
  el('source-info').textContent=Object.values(pack.examples).map(s=>'CMU '+s.id+' ('+s.action+'). '+s.description).join(' ');
  select();
})();
