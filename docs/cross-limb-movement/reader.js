'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const {domains, time, example, prepare} = MovementHistory;
  const stories = [example(0), example(1)];
  let domain = 1, joint, comparison, features, pending = false;

  const spec = () => domains[domain], current = () => stories[domain];
  const fmt = (value, places = 3) => value == null ? '—' : Number(value.toFixed(places)).toLocaleString('en-US', {maximumFractionDigits: places, useGrouping: false});
  const option = (select, value, label) => select.add(new Option(label, value));
  const words = {
    arm: 'In the grasp-and-lift study, the forecast starts 400 ms after a light tells the participant to move. Five electrodes followed the right arm and hand. The wrist tracker kept its own X, Y and Z coordinates.',
    balance: 'In the balance study, the scene rotated while a person stood or walked. Eight electrodes followed the lower legs. An optical marker on the lower back followed the sacrum. The forecast starts 32 samples after the first sample at or after the rotation onset.'
  };
  function buildMenus() {
    const s = spec(), h = current();
    $('setting').textContent = words[s.key];
    $('balance-context').hidden = domain !== 0;
    $('posture').value = String(h.session); $('direction').value = String(h.direction);
    for (const id of ['channel','axis','edit-channel']) $(id).replaceChildren();
    s.names.forEach((name, i) => {
      option($('channel'), i, name);
      option($('edit-channel'), 'emg.' + i, name + ' · voltage');
    });
    s.axes.forEach((name, i) => {
      option($('axis'), i, name);
      option($('edit-channel'), 'pose.' + i, s.marker + ' ' + name + ' · position');
    });
    $('editing').textContent = '';
    fillEditor();
  }
  function fillEditor() {
    const s = spec(), h = current(), [kind, i] = $('edit-channel').value.split('.');
    $('mask-label').hidden = domain !== 1 || kind !== 'emg';
    $('mask').value = h.enabled[i] ? 'include' : 'mask';
    const unit = kind === 'emg' ? s.unit : 'mm', hz = kind === 'emg' ? s.emgHz : s.poseHz;
    $('edit-info').textContent = h[kind].length + ' samples in ' + unit + ' at ' + hz + ' Hz, ending at the cutoff. Enter values from −1,000,000 to +1,000,000. ' +
      (domain === 1 && kind === 'emg' ? 'Keep at least three of the five acquired channels. Masking removes this channel’s history and forecast.' : '');
    $('samples').value = h[kind].map(row => row[i]).join(', ');
    $('samples').setAttribute('aria-invalid', 'false');
    pending = false;
  }
  function compute() {
    const h = current();
    features = prepare(h);
    const m = $('method').value;
    const maps = m === 'maps';
    const scalp = m === 'scalp';
    $('map-note').hidden = !maps;
    $('scalp-controls').hidden = !scalp;
    $('first-legend').textContent = scalp ? 'With scalp' : maps ? 'Body-part maps' : 'Shared';
    $('second-legend').textContent = scalp ? 'Reference' : maps ? 'Early/late maps' : 'Comparison';
    if (scalp) {
      Object.assign(features, editScalpHistory(exampleScalpHistory(domain), Number($('scalp-gain').value),
        $('scalp-order').value === 'reverse', $('scalp-sites').value));
      joint = MovementPredict(ScalpModels.central, features);
      comparison = MovementPredict(ScalpModels.reference, features);
      draw();
      return;
    }
    joint = MovementPredict(maps ? MovementMapWeights.separate : MovementWeights.joint, features);
    if (maps) comparison = MovementPredict(MovementMapWeights.matched, features);
    else if (m === 'matched' || m === 'equal') comparison = MovementPredict(MovementWeights[spec().key][m], features);
    else {
      const path_mm = features.repeat_path_mm.map((row, index) => {
        if (m === 'repeat') return row;
        if (m === 'velocity') {
          const dt=1/32 + features.age_s[18] - features.age_s[19];
          return features.patch_xyz_mm[18].map(v => -v * (index + 1) / (256 * dt));
        }
        return [0,0,0];
      });
      comparison = {path_mm, rms: features.past_rms.map((v, i) => features.muscle_mask[i] ? v : null)};
    }
    draw();
  }
  const svgNS = 'http://www.w3.org/2000/svg';
  function svgNode(name, attrs, text) {
    const n = document.createElementNS(svgNS, name);
    for (const [key, val] of Object.entries(attrs)) n.setAttribute(key, val);
    if (text != null) n.textContent = text;
    return n;
  }
  function plot(id, title, curves, cursorTime, masked = false) {
    const parent = $(id), width = Math.max(232, Math.round(parent.getBoundingClientRect().width));
    const left = width < 400 ? 42 : 54, right = width - 15, top = 10, height = width < 400 ? 138 : 158, bottom = height - 26;
    const X = t => left + (t + 625) / 750 * (right - left);
    const exact = curves.flatMap(c => c.points.map(p => p[1]));
    let lo = Math.min(0, ...exact), hi = Math.max(0, ...exact);
    if (hi - lo < 1e-10) {hi += 1; lo -= 1;}
    const pad = (hi - lo) * .08;
    const Y = val => top + (hi + pad - val) * (bottom - top) / (hi - lo + 2 * pad);
    const svg = svgNode('svg',{viewBox:'0 0 ' + width + ' ' + height, role:'img','aria-label':title});
    const add = (tag, attrs, text) => svg.append(svgNode(tag,attrs,text));
    add('rect',{x:X(0),y:top,width:right-X(0),height:bottom-top,fill:'#edf5f2'});
    const label=(x,y,v,anchor='middle')=>add('text',{x,y,fill:'#425a60','text-anchor':anchor,'font-size':12},v);
    const ticks = lo<0 && hi>0 ? [lo,0,hi] : [lo,hi];
    for (const val of ticks) {
      add('line',{x1:left,x2:right,y1:Y(val),y2:Y(val),stroke:val===0?'#a3b3b0':'#e0e8e6'});
      const magnitude = Math.max(Math.abs(lo),Math.abs(hi));
      label(left-4,Y(val)+4, magnitude >= 1000 || (magnitude < .001 && magnitude > 0) ? val.toExponential(0) : fmt(val,magnitude<.1?3:1),'end');
    }
    for (const c of curves) {
      if (!c.points.length) continue;
      add('polyline',{points:c.points.map(([t,v])=>X(t).toFixed(2)+','+Y(v).toFixed(2)).join(' '),stroke:c.color,fill:'none','stroke-width':c.width||2,'stroke-dasharray':c.dash||'none','stroke-linejoin':'round'});
    }
    add('line',{x1:X(0),x2:X(0),y1:top,y2:bottom,stroke:'#6f827d','stroke-dasharray':'3 3'});
    if (cursorTime != null) {
      add('line',{x1:X(cursorTime),x2:X(cursorTime),y1:top,y2:bottom,stroke:'#00777d','stroke-dasharray':'2 3'});
      for (const c of curves.slice(1)) {
        const p=c.points.find(point=>point[0]===cursorTime);
        if (p) add('circle',{cx:X(cursorTime),cy:Y(p[1]),r:3,fill:c.color});
      }
    }
    for(const t of (width<400?[-625,-312.5,0,125]:[-625,-500,-375,-250,-125,0,125]))
      label(X(t),bottom+17,t===125?(width<400?'+125':'+125 ms'):(t===-625 && width<400?'−625 ms':String(t).replace('-', '−')),t===-625?'start':(t===125 || (t===0 && width<400))?'end':'middle');
    if(masked)label((left+X(0))/2,(top+bottom)/2,'Channel masked');
    parent.replaceChildren(svg);
  }
  function table(host, title, headings, rows) {
    const caption=document.createElement('caption'); caption.textContent=title;
    const t=document.createElement('table'); t.append(caption);
    const header=t.createTHead().insertRow();
    for(const h of headings){const el=document.createElement('th');el.scope='col';el.textContent=h;header.append(el);}
    const body=t.createTBody();
    for(const row of rows){const tr=body.insertRow();row.forEach((v,i)=>{const td=document.createElement(i?'td':'th');if(!i)td.scope='row';td.textContent=v;tr.append(td);});}
    const wrap=document.createElement('div');wrap.className='scroll';wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',title);wrap.append(t);host.append(wrap);
  }
  function draw() {
    const s=spec(),h=current(),a=+$('axis').value,c=+$('channel').value,k=s.offset+c;
    const step=+$('step').value,t=1000*step/256, axis=s.axes[a], active=h.enabled[c];
    const first = $('first-legend').textContent, second = $('second-legend').textContent;
    if ($('method').value === 'scalp') {
      const site = Number($('scalp-site').value), active = features.scalp_mask[site];
      const name = ['C3','Cz','C4'][site], native = ['D19','A1','B22'][site];
      const unit = domain ? 'original scalp amplitude units' : 'µV';
      $('scalp-description').textContent = domain
        ? name+' is a site on the grasp-study cap. Its stored voltage scale has no verified conversion to microvolts.'
        : name+' is the nominal position of balance electrode '+native+'. Its recorded voltage is in microvolts.';
      const series = k => active ? features.scalp_values.map((bin,i)=>[(i-19)*31.25,bin[site][k]]) : [];
      plot('scalp-plot',name+' scalp history in '+unit,[
        {points:series(0),color:'#304d5a'},{points:series(1),color:'#a64f21',dash:'5 3'}],null,!active);
      $('scalp-caption').textContent = active
        ? 'Each point summarizes 31.25 ms. Solid shows the signed mean and dashed shows signal size (RMS). The last bin reads '+fmt(features.scalp_values[19][site][0],3)+' and '+fmt(features.scalp_values[19][site][1],3)+' '+unit+', respectively.'
        : 'This site is excluded from both forecasts. The selected site mask still enters both models.';
    }
    $('time').value='+'+fmt(t,4)+' ms';
    $('path-title').textContent=s.marker+' displacement · '+axis+' (mm)';
    $('voltage-title').textContent=s.names[c]+' · signed voltage';
    $('voltage-unit').textContent=s.unit;
    const history=h.pose.map((row,i)=>[1000*time(i,h.pose.length,s.poseHz),row[a]-h.pose.at(-1)[a]]).filter(row=>row[0]>=-625);
    const curve=path=>[[0,0],...path.map((row,i)=>[1000*(i+1)/256,row[a]])];
    plot('path-chart',$('path-title').textContent,[
      {points:history,color:'#47575f'},
      {points:curve(joint.path_mm),color:'#00757c',width:2.8},
      {points:curve(comparison.path_mm),color:'#ad5724',dash:'5 3'}
    ],t);
    $('path-caption').textContent='The vertical line marks the last available reading. The shaded interval contains 32 forecasts in the '+(domain?'wrist tracker’s X/Y/Z frame.':'balance study’s mediolateral, superior–inferior and anterior–posterior frame. The anatomical sign of each axis is unresolved.');
    const signed=active?h.emg.map((row,i)=>[1000*time(i,h.emg.length,s.emgHz),row[c]]):[];
    plot('voltage-chart',$('voltage-title').textContent,[{points:signed,color:'#47575f',width:1.0}],null,!active);
    $('voltage-caption').textContent= active ? 'The line shows signed invented readings at '+s.emgHz+' Hz. The model reads the root-mean-square amplitude in each of twenty 31.25 ms bins. It predicts one RMS amplitude for the next 125 ms.' : 'This acquired arm channel is masked. Its values are excluded from the calculation. The '+(domain?'eight lower-leg':'five arm')+' channels belong to the other study and were never acquired here.';
    $('position-heading').textContent=s.marker+' '+axis+' at +'+fmt(t,4)+' ms';
    $('position-readout').textContent=first+' '+fmt(joint.path_mm[step-1][a])+' mm · '+second+' '+fmt(comparison.path_mm[step-1][a])+' mm';
    $('rms-heading').textContent=s.names[c]+' · 125 ms RMS';
    $('rms-readout').textContent=active?first+' '+fmt(joint.rms[k],domain?6:3)+' '+s.unit+' · '+second+' '+fmt(comparison.rms[k],domain?6:3)+' '+s.unit:'Masked · no input or forecast';
    $('coordinates').replaceChildren(); $('amplitudes').replaceChildren();
    table($('coordinates'),s.marker+' path in mm',['Time (ms)',...s.axes.map(k=>first+' '+k),...s.axes.map(k=>second+' '+k)],
      joint.path_mm.map((row,i)=>[fmt((i+1)*1000/256,4),...row.map(x=>fmt(x,4)),...comparison.path_mm[i].map(x=>fmt(x,4))]));
    table($('amplitudes'),'Muscle amplitude in '+s.unit,['Muscle','Prior 125 ms RMS',first+' forecast',second+' forecast'],
      s.names.map((n,i)=>[n,...(h.enabled[i]?[features.past_rms[i+s.offset],joint.rms[i+s.offset],comparison.rms[i+s.offset]].map(x=>fmt(x,domain?7:4)):['Masked','Masked','Masked'])]));
    const note=document.createElement('p');note.className='caption';note.textContent=domain?'The eight leg channels were never acquired in the wrist study. Source-native arm amplitudes have no verified conversion to microvolts.':'The five right arm channels were never acquired in the balance study. All eight leg channels must be present for this model.';$('amplitudes').append(note);
  }
  function fold(host,label) {
    const el=document.createElement('details'),title=document.createElement('summary');
    el.className='fold';title.textContent=label;el.append(title);host.append(el);return el;
  }
  function evaluation() {
    const host=$('evaluation');
    const results=MovementResults;
    const add=(tag,txt,cls)=>{const n=document.createElement(tag);n.textContent=txt;if(cls)n.className=cls;host.append(n);};
    add('p',results.scope,'scope');
    for(const group of results.groups){
      const container = group.collapsed ? fold(host,group.title) : host;
      if (!group.collapsed) add('h3',group.title);
      const detail=document.createElement('p');detail.textContent=group.detail;container.append(detail);
      const more=fold(container,'Channel, task and control details');
      for(const item of group.tables) {
        const target=item.detail?more:container;
        table(target,item.caption,item.headers,item.rows);
      }
      container.append(more);
    }
    for(const text of results.notes)add('p',text);
  }
  document.querySelectorAll('input[name="domain"]').forEach(el=>el.addEventListener('change',()=>{domain=+el.value;buildMenus();compute();}));
  for(const id of ['method','posture','direction'])$(id).addEventListener('change',()=>{
    if(!domain){current().session=+$('posture').value;current().direction=+$('direction').value;}compute();});
  for(const id of ['axis','channel','step'])$(id).addEventListener('input',draw);
  for(const id of ['scalp-gain','scalp-order','scalp-sites']) $(id).addEventListener('change',compute);
  $('scalp-site').addEventListener('change',draw);
  $('edit-channel').addEventListener('change',()=>{fillEditor();$('editing').textContent='';});
  $('samples').addEventListener('input',()=>{pending=true;$('editing').textContent='Edits pending. The charts show the last applied history.';});
  $('mask').addEventListener('change',()=>{
    const i=+$('edit-channel').value.split('.')[1],h=current();
    if($('mask').value==='mask'&&h.enabled[i]&&h.enabled.filter(Boolean).length===3){
      $('mask').value='include';$('editing').textContent='Keep at least three arm channels in this example.';return;
    }
    h.enabled[i]=$('mask').value==='include';compute();$('editing').textContent='Channel selection applied.'+(pending?' Sample edits still pending.':'');
  });
  $('apply').addEventListener('click',()=>{
    const h=current(),[kind,i]=$('edit-channel').value.split('.');
    const text=$('samples').value.trim(),parts=text.split(/\s*,\s*|\s+/);
    const values=parts.map(v=>Number(v)),expected=h[kind].length;
    if(!text||parts.some(x=>!x.length)||values.length!==expected||values.some(v=>!Number.isFinite(v)||Math.abs(v)>1e6)){
      $('samples').setAttribute('aria-invalid','true');$('editing').textContent='Enter exactly '+expected+' finite samples between −1,000,000 and +1,000,000. Your last applied history is still shown.';return;
    }
    values.forEach((v,index)=>{h[kind][index][i]=v;});$('samples').setAttribute('aria-invalid','false');pending=false;
    compute();$('editing').textContent='Samples applied to this task.';
  });
  $('reset').addEventListener('click',()=>{stories[domain]=example(domain);buildMenus();compute();$('editing').textContent='This task’s original example has been restored.';});
  if(location.protocol==='file:'){$('download').hidden=true;$('offline').hidden=false;}
  function chooseLinkedComparison() {
    if (location.hash === '#scalp-input') $('method').value = 'scalp';
    if (location.hash === '#path-maps') $('method').value = 'maps';
  }
  chooseLinkedComparison();
  addEventListener('hashchange',()=>{chooseLinkedComparison();compute();});
  document.querySelector('.jump a[href="#scalp-input"]').addEventListener('click', () => {
    if (location.hash === '#scalp-input') { chooseLinkedComparison(); compute(); }
  });
  buildMenus();compute();evaluation();
  let observedWidth=0;
  new ResizeObserver(entries=>{const width=Math.round(entries[0].contentRect.width);if(width!==observedWidth){observedWidth=width;draw();}}).observe($('path-chart'));
})();
