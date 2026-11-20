(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const data = JSON.parse(get('motion-data').textContent);
  const {schema,weights,refs,study} = data;
  const save = get('save');
  save.href = URL.createObjectURL(new Blob(['<!doctype html>\n',document.documentElement.outerHTML],{type:'text/html;charset=utf-8'}));
  const canvas=get('stage'), points=get('point'), details=get('point-details');
  const prompt=get('words'), slider=get('scrub'), play=get('play');
  const modes=[...document.querySelectorAll('input[name="layer"]')];
  const state={frame:0,mode:'generated',yaw:-31,pitch:10,selected:-1};
  let scene, animation=0, activeTick=null, drag;
  const bodyName = name => name.replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().replace(/^./,c=>c.toUpperCase());
  const node = (type,text) => {
    const el=document.createElement(type);
    if (text !== undefined) el.textContent=text;
    return el;
  };

  function render() {
    if (!scene) return;
    state.selected=details.open ? points.selectedIndex : -1;
    drawMovement(canvas,scene,state);
    const frame=state.frame, time=frame/schema.rateHz, pick=points.selectedIndex;
    slider.value=frame; slider.setAttribute('aria-valuetext',time.toFixed(3)+' seconds, sample '+(frame+1));
    get('time').textContent=time.toFixed(3)+' s';
    const readout=get('readout');
    readout.replaceChildren();
    if (details.open && pick>=0) {
      for (const [kind,frames] of [['Generated',scene.gen],['Recorded',scene.rec]]) {
        if ((kind==='Generated' && state.mode==='recorded')||(kind==='Recorded'&&state.mode==='generated')) continue;
        const p=frames[frame][pick], line=node('p',kind+' · '+p.map((v,i)=>'XYZ'[i]+' '+v.toFixed(1)).join(' / ')+' mm');
        line.dataset.kind=kind;line.dataset.xyz=p.join(',');readout.append(line);
      }
    }
  }
  function halt() {
    activeTick=null;
    window.cancelAnimationFrame(animation); animation=0;
    play.textContent=scene && state.frame===scene.gen.length-1 ? 'Replay':'Play';
  }
  function clearScene(message,error=false) {
    halt();scene=null;state.frame=0;slider.value=0;get('time').textContent='—';
    const ctx=canvas.getContext('2d');if(ctx) {ctx.save();ctx.resetTransform();ctx.clearRect(0,0,canvas.width,canvas.height);ctx.restore();}
    get('motion-title').textContent='No movement selected';get('layer-caption').replaceChildren();get('readout').replaceChildren();
    get('reference-caption').textContent='';get('coordinate-note').textContent='';
    play.disabled=slider.disabled=points.disabled=get('reset').disabled=true;modes.forEach(el=>el.disabled=true);
    get('status').textContent=message;get('status').classList.toggle('err',error);
  }
  function caption() {
    const box=get('layer-caption');box.replaceChildren();
    for(const [kind,label] of [['gen','Generated'],['rec','Recorded']]) {
      if((kind==='gen'&&state.mode==='recorded')||(kind==='rec'&&state.mode==='generated')) continue;
      if(box.childNodes.length)box.append('  /  ');
      const marker=node('i');marker.className='legend '+kind;box.append(marker,label);
    }
    const ref=refs[scene.action];
    get('reference-caption').textContent='CMU '+ref.trialId+' supplies the recorded '+scene.action+'. It is one of the training trials. Its frames '+ref.sourceFrames[0]+'–'+ref.sourceFrames.at(-1)+' appear at one third of the original sample rate.';
  }
  function load() {
    halt();
    try {
      const clip=generateMotion(prompt.value,weights);
      if (!clip) {clearScene('Use one of the action words shown above. Other requests have no trained trajectory here.',true);return;}
      const ref=refs[clip.action];
      if (!ref) throw Error('The recording for this action is unavailable.');
      const gen=translatedFrames(clip,schema),rec=translatedFrames(ref,schema);
      scene={action:clip.action,gen,rec,edges:schema.edges,bounds:sceneBounds(gen,rec)};
      state.frame=0;state.mode=modes.find(el=>el.checked).value;
      get('motion-title').textContent=bodyName(clip.action);
      get('status').textContent='Generated from “'+clip.action+'” using the fitted model.';get('status').classList.remove('err');
      play.disabled=slider.disabled=points.disabled=get('reset').disabled=false;modes.forEach(el=>el.disabled=false);
      slider.max=gen.length-1;caption();
      get('coordinate-note').textContent='Each grid square spans 25 cm. Coordinates use the first pelvis position as their origin. Y follows the overall course, X points right of it and Z points up.';
      play.textContent='Play';render();
    } catch(e) {clearScene('The viewer could not open this movement. '+e.message,true);}
  }
  schema.joints.forEach((name,i)=>points.add(new Option(bodyName(name),String(i))));
  points.value=String(Math.max(0,schema.joints.indexOf('rightWrist')));
  for(const word of study.examples) {
    const button=node('button',word);button.type='button';
    button.addEventListener('click',()=>{prompt.value=word;load();});get('examples').append(button);
  }
  get('form').addEventListener('submit',e=>{e.preventDefault();load();});
  prompt.addEventListener('input',()=>clearScene('Generate to see the movement for this word.'));
  points.addEventListener('change',render);details.addEventListener('toggle',render);
  for(const el of modes)el.addEventListener('change',()=>{if(scene){state.mode=el.value;caption();render();}});
  slider.addEventListener('input',()=>{if(scene){state.frame=Number(slider.value);halt();render();}});
  play.addEventListener('click',()=>{
    if (!scene) return;
    if(activeTick){halt();return;}
    const last=scene.gen.length-1;
    if(state.frame===last){state.frame=0;render();}
    const from=state.frame;
    let start;
    function tick(now) {
      if(activeTick!==tick)return;
      start ??= now;
      const next=Math.min(last,from+Math.floor((now-start)*schema.rateHz/1000));
      if(next>state.frame){state.frame=next;render();}
      if(next===last){halt();}else{animation=requestAnimationFrame(tick);}
    }
    activeTick=tick;
    play.textContent='Pause';animation=requestAnimationFrame(tick);
  });
  function turn(yaw,pitch) {
    state.yaw=((yaw+180)%360+360)%360-180;state.pitch=Math.max(-65,Math.min(65,pitch));render();
  }
  get('reset').addEventListener('click',()=>turn(-31,10));
  canvas.addEventListener('keydown',e=>{
    const key=e.key;
    if(!scene || !['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(key))return;
    e.preventDefault();
    if(key==='Home'){turn(-31,10);return;}
    const step=e.shiftKey?15:5;
    turn(state.yaw+(key==='ArrowLeft'?-step:key==='ArrowRight'?step:0),state.pitch+(key==='ArrowUp'?step:key==='ArrowDown'?-step:0));
  });
  canvas.addEventListener('pointerdown',e=>{
    if(!scene || !e.isPrimary || e.button!==0)return;
    canvas.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.clientX,y:e.clientY,yaw:state.yaw,pitch:state.pitch};
  });
  canvas.addEventListener('pointermove',e=>{
    if(drag?.id===e.pointerId)turn(drag.yaw+(e.clientX-drag.x)*.5,drag.pitch+(e.clientY-drag.y)*.35);
  });
  canvas.addEventListener('lostpointercapture',()=>{drag=null;});
  new ResizeObserver(render).observe(canvas);
  window.addEventListener('pagehide',halt);document.addEventListener('visibilitychange',()=>{if(document.hidden)halt();});
  get('scope').textContent=study.scope;get('bench-note').textContent=study.metric;
  const table=node('table'),head=table.createTHead().insertRow();
  for(const text of ['Method','Error (mm)']){const th=node('th',text);th.scope='col';head.append(th);}
  const tbody=table.createTBody();
  for(const [title,mm] of study.rows){
    const row=tbody.insertRow(),th=node('th',title);th.scope='row';row.append(th);
    row.insertCell().textContent=mm.toFixed(1);
  }
  get('bench').append(table,node('p',study.conclusion));
  for(const text of study.sourceNotes)get('sources').append(node('p',text));
  for(const pair of study.links){
    const row=node('p'),a=node('a',pair[0]);a.href=pair[1];row.append(a);get('sources').append(row);
  }
  load();
})();
