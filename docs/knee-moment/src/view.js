(() => {
  const el = id => document.getElementById(id);
  const weights = JSON.parse(el('weights').textContent);
  const errors = JSON.parse(el('study-results').textContent).mean_person_mae_Nm_per_kg;
  const labels = {trained:'Task-trained Transformer', train_walker_match:'Match to a training walker',
    ridge:'Linear model on angles', shared:'Frozen movement encoder', scrambled:'Shuffled encoder weights', mean:'Training mean'};
  let imported = null, current = null, fileGeneration = 0;
  const signed = (n, digits) => (n < 0 ? '−' : '+') + Math.abs(n).toFixed(digits);

  function trace() {
    const canvas = el('angles'), width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !current) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(width*scale); canvas.height = Math.round(height*scale);
    const c = canvas.getContext('2d'); c.scale(scale,scale);
    const pair = Number(el('joint').value), series = current.angles_deg;
    const values = series.flatMap(row => row.slice(pair,pair+2));
    const min = Math.min(...values), max = Math.max(...values);
    // Scale by the largest absolute angle first so near-limit numbers cannot overflow.
    const magnitude = Math.max(1,Math.abs(min),Math.abs(max));
    const bot = Math.min(0,min/magnitude), top = Math.max(0,max/magnitude);
    const left = 50, right = width-10, lower = height-25, upper = 12;
    const x = i => left+(right-left)*i/399;
    const y = v => lower-(lower-upper)*(v/magnitude-bot)/(top-bot || 1);
    const tick = v => Math.abs(v)>=1e4 ? v.toExponential(0) : String(Math.round(v));
    c.font = '12px Arial, sans-serif'; c.textAlign = 'right'; c.fillStyle = '#52675f';
    for (let n=0;n<3;n++) {
      const v = (bot+(top-bot)*n/2)*magnitude;
      c.strokeStyle = '#d7ddd5'; c.lineWidth=1;c.beginPath();c.moveTo(left,y(v));c.lineTo(right,y(v));c.stroke();
      c.fillText(tick(v)+'°',left-6,y(v)+4);
    }
    c.textAlign='left'; c.fillText('−3.99 s',left,height-3);
    c.textAlign='right'; c.fillText('Cutoff · 0 s',right,height-3);
    for (let j=0;j<2;j++) {
      c.setLineDash(j ? [6,4]:[]);c.strokeStyle=j?'#a14329':'#006855';c.lineWidth=2.2;c.beginPath();
      series.forEach((row,i) => {if(i===0)c.moveTo(x(i),y(row[pair+j]));else c.lineTo(x(i),y(row[pair+j]));});c.stroke();
    }
    const label = el('joint').selectedOptions[0].textContent.toLowerCase();
    const last = series[399];
    const text = 'At the cutoff, '+label+' read '+signed(last[pair],1)+'° right and '+signed(last[pair+1],1)+'° left.';
    canvas.setAttribute('aria-label','Four seconds of '+label+' in degrees. '+text);el('angle-caption').textContent=text;
  }

  function showMoments(result) {
    const values = result.internal_knee_moment_Nm_per_kg[0];
    const limit = Math.max(.5, ...values.map(Math.abs));
    el('readouts').replaceChildren();
    for (let i=0; i<2; i++) {
      const side = i ? 'Left' : 'Right', v = values[i];
      const group = document.createElement('div'); group.className = side.toLowerCase();
      const head = document.createElement('div');head.className='value-head';
      const name=document.createElement('span');name.textContent=side+' knee';
      const number=document.createElement('strong');number.textContent=signed(v,3)+' ';
      const units=document.createElement('span');units.className='unit';units.textContent='N·m/kg';number.append(units);
      head.append(name,number);
      const track=document.createElement('div');track.className='track';track.setAttribute('aria-hidden','true');
      const fill=document.createElement('i');fill.className='fill';
      const delta=v/limit*50;fill.style.width=Math.abs(delta)+'%';fill.style.left=Math.min(50,50+delta)+'%';
      track.append(fill);group.append(head,track);el('readouts').append(group);
    }
    el('lag').textContent='The closest earlier knee-angle pattern was '+result.period_frames[0]+' frames back. Both bars use the same ±'+limit.toPrecision(2)+' N·m/kg scale.';
  }

  function render() {
    const phase = Number(el('phase').value);
    current = imported || makeKneeMomentExample(phase);
    el('phase-out').textContent=imported?'From file':phase+'% of cycle';
    const result = kneeMoment.predict({...current,mode:el('mode').value},weights);
    showMoments(result);trace();
  }
  for (const [key,label] of Object.entries(labels)) {
    const row=el('scores').insertRow();row.insertCell().textContent=label;row.insertCell().textContent=errors[key].toFixed(4);
  }
  el('phase').addEventListener('input',render);el('mode').addEventListener('change',render);
  el('joint').addEventListener('change',trace);
  new ResizeObserver(trace).observe(el('angles'));

  function setSource(record, filename) {
    imported=record;el('phase').disabled=!!record;el('reset').hidden=!record;
    el('source-flag').textContent=record?'Local history':'Invented walk';
    el('phase-help').textContent=record?'The cutoff is the last frame in your file. Return to the invented walk to move through its cycle.':'Move through one cycle of an invented walk. Each stop supplies a new history of both knees, hips and ankles.';
    if (record) el('mode').value=record.mode;
    render();el('message').textContent=record?'Showing '+filename+'.':'';
  }
  el('file').addEventListener('change',async () => {
    const file=el('file').files[0]; if(!file) return;
    const generation=++fileGeneration;
    try {
      if(file.size>2*1024*1024)throw Error('Use one 400-frame history smaller than 2 MB.');
      const record=JSON.parse(await file.text());
      if(generation!==fileGeneration)return;
      if(!Array.isArray(record?.frames) || Array.isArray(record.frames[0]))throw Error('Use one history in the browser. Node also accepts batches.');
      // Check every selectable estimator before accepting the file for interactive use.
      kneeMoment.predict(record,weights);
      for(const mode of Object.keys(labels).filter(k=>k!=='train_walker_match')) kneeMoment.predict({...record,mode},weights);
      setSource(record,file.name);
    } catch(error){if(generation===fileGeneration)el('message').textContent='Could not open this history. '+error.message;}
    if(generation===fileGeneration)el('file').value='';
  });
  el('reset').addEventListener('click',()=>{++fileGeneration;setSource(null);});
  el('save').addEventListener('click',()=>{
    const record=makeKneeMomentExample(Number(el('phase').value));record.mode=el('mode').value;
    const url=URL.createObjectURL(new Blob([JSON.stringify(record)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='invented-knee-history.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  render();
})();
