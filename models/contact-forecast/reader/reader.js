(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const labels={bump:'Push before target',reach:'Go cue after a push',unbumped:'Go cue without a push'};
  const dates={test:'13 Sep 2017 · next-day test',validation:'12 Sep 2017 · validation'};
  const modes={all:'Movement + counts + cues',count_cue:'Counts + cues',wrong_movement:'Earlier trial’s movement',cue:'Cues only',movement:'Movement only',count:'Counts only',movement_cue:'Movement + cues'};
  const simple={mean:'Training mean per contact',persistence:'Previous 100-ms count'};
  const precision=x=>Number.isFinite(x)?x.toFixed(3):'—';
  const set=(id,value)=>{$(id).textContent=value;};
  function options(id, values, preferred) {
    const el=$(id);
    el.replaceChildren(...Object.entries(values).map(([v,label])=>new Option(label,v)));
    if (preferred!=null && [...el.options].some(o=>o.value===String(preferred))) el.value=String(preferred);
  }
  const query=new URLSearchParams(location.search);
  let packet=null, invented=false, row=null, result=null;
  function table(head,rows) {
    const t=document.createElement('table'), header=t.createTHead().insertRow();
    for(const name of head){const th=document.createElement('th');th.scope='col';th.textContent=name;header.append(th);}
    const body=t.createTBody();
    for(const values of rows){const tr=body.insertRow();for(const value of values){const cell=tr.insertCell();cell.textContent=value;}}
    return t;
  }
  function showHistory() {
    if(!packet){$('tokens').replaceChildren();return;}
    const col=Number($('contact').value), raw=ContactForecast.history(packet);
    const details=raw.map((v,i)=>{
      const seen=[v[30]?'push':null,v[33]?'target':null,v[36]?'go':null].filter(Boolean);
      return [(i*40-200)+' to '+(i*40-160),precision(v[0]),precision(v[1]),precision(v[2]),precision(v[3]),v[4+col],seen.join(', ')||'None'];
    });
    $('tokens').replaceChildren(table(['Interval (ms)','End X (cm)','End Y (cm)','ΔX (cm)','ΔY (cm)','Events · '+ContactCases.contact_ids[col],'Cues seen'],details));
  }
  function inspect() {
    const col=Number($('contact').value), id=ContactCases.contact_ids[col];
    const measured=row && !invented?row.recorded:null;
    const items=[];
    if(result)items.push(precision(result[col])+' forecast');
    if(measured)items.push(measured[col]+' recorded');
    set('readout',items.length?'Contact '+id+' · '+items.join(' · ')+' per 100 ms':'No count comparison available.');
    const els=[...$('counts').querySelectorAll('.column')];
    els.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===col)));
    showHistory();
  }
  function plot(observed){
    const plot=$('counts');plot.replaceChildren();
    if(!result && !observed){$('table').replaceChildren();set('scale','');inspect();return;}
    const peak=Math.max(1,Math.ceil(Math.max(...(result||[]),...(observed||[]))));
    const area=document.createElement('div');area.className='graph';
    const rows=[];
    for(const [c,id] of ContactCases.contact_ids.entries()) {
      const pred=result?.[c],obs=observed?.[c],btn=document.createElement('button');
      btn.className='column';btn.type='button';
      btn.title='Contact '+id+' · forecast '+precision(pred)+' · recorded '+(obs??'unavailable');
      btn.setAttribute('aria-label',btn.title);
      const inner=document.createElement('span');inner.className='bars';inner.setAttribute('aria-hidden','true');
      for(const [cls,v] of [['pred',pred],['obs',obs]])if(v!==undefined){
        const bar=document.createElement('i');bar.className=cls;bar.style.height=(100*v/peak)+'%';inner.append(bar);
      }
      const cid=document.createElement('span');cid.className='cid';cid.textContent=id;
      btn.append(inner,cid);btn.onclick=()=>{$('contact').value=String(c);inspect();};area.append(btn);
      rows.push([id,precision(pred),obs??'—',pred!==undefined&&obs!==undefined?precision(pred-obs):'—']);
    }
    plot.append(area);
    set('scale','Every contact uses the same scale from 0 to '+peak+' events per 100 ms. Select a contact to read its values.');
    $('table').replaceChildren(table(['Contact ID','Forecast','Recorded','Forecast − recorded'],rows));inspect();
  }
  function metric(m, digits=3) {
    const format=v=>v.toFixed(digits);
    if(!m || !Number.isFinite(m.estimate))return 'Unavailable';
    if(!Array.isArray(m.interval)||m.interval.some(v=>!Number.isFinite(v)))return format(m.estimate)+' (interval unavailable)';
    return format(m.estimate)+' ['+m.interval.map(format).join(', ')+']';
  }
  function support() {
    const el=$('support');el.replaceChildren();
    const phase=$('phase').value, date=$('date').value, s=ContactEvidence[date]?.phases[phase];
    const p=txt=>{const node=document.createElement('p');node.textContent=txt;el.append(node);};
    if(!s || !(s.all_eligible.windows>0)){p('This recording split has no eligible windows for this phase.');return;}
    p(dates[date]+' · '+labels[phase]+'. '+s.all_eligible.originals+' eligible original trials contributed '+s.all_eligible.windows+' windows. An earlier motion match was available for '+s.matched.windows+' windows from '+s.matched.originals+' trials. '+(s.all_eligible.windows-s.matched.windows)+' windows had no match.');
    if(s.matched.windows){
      const summary=[['Counts + cues',metric(s.countCue,6)],['Earlier trial’s movement',metric(s.wrong,6)]];
      const wrap=document.createElement('div');wrap.className='scroll';
      wrap.append(table(['Full model minus comparison','Mean deviance difference [95% interval]'],summary));el.append(wrap);
      if(s.fullMae)p('Full Transformer on the '+s.matched.originals+' matched trials · mean absolute error '+metric(s.fullMae)+' events per contact per 100 ms. The same model scored on all '+s.all_eligible.originals+' eligible trials can show a slightly different average and interval, because the trial sets differ.');
      const rep=s.all_eligible.scores?.persistence, full=s.all_eligible.scores?.transformer_all;
      if(rep&&full&&rep.mae.estimate<full.mae.estimate)p('Repeating the last count missed by less than the full Transformer across all '+s.all_eligible.originals+' eligible trials: mean absolute error '+metric(rep.mae)+' against '+metric(full.mae)+'.');
    }
    const family=$('family').value, mode=$('mode').value;
    const scoreId=family==='simple'?(mode==='mean'?'training_mean':'persistence'):family+'_'+mode;
    const group=mode==='wrong_movement'?'matched':'all_eligible';
    const selected=s[group].scores?.[scoreId];
    if(selected){
      const method=$('family').selectedOptions[0].textContent+' · '+$('mode').selectedOptions[0].textContent;
      p(method+' across '+(group==='matched'?'the '+s.matched.originals+' matched':'all '+s.all_eligible.originals+' eligible')+' original trials. Mean absolute error '+metric(selected.mae)+' events per contact per 100 ms. Mean deviance '+metric(selected.deviance)+'.'+(family==='transformer'?' Group scores average the three fits.':''));
    }
    if(date==='test' && phase==='bump'){
      const passed=ContactEvidence[date].passed;
      if(s.wrong?.interval?.[1]<0 && s.countCue?.interval?.[0]<=0 && s.countCue?.interval?.[1]>=0)
        p('Using the trial’s own movement improved forecasts over borrowing another trial’s movement. The interval for adding movement to counts and cues spans zero, so that gain remains uncertain.');
      if(passed===true)p('Both upper interval limits fall below zero. The full model passed the prespecified next-day push comparison.');
      else if(passed===false)p('The full model did not meet both conditions for a next-day benefit from movement.');
      else p('The primary comparison has no available decision.');
    }else if(date==='test')p('This go-cue comparison is descriptive. The model learned from pushes before the target appeared.');
    else p('Development results from 12 September. The primary comparison uses the 13 September push trials.');
  }
  function update() {
    try {
      const obs=Boolean(row && !invented), family=$('family').value, mode=$('mode').value;
      $('obs-legend').hidden=!obs;$('seed').disabled=family!=='transformer';
      $('edit').disabled=!row || invented;$('reset').disabled=!invented;$('editor').hidden=!invented;
      if(!row){result=null;set('source-state','No example exists in this split for this phase.');set('trace','');plot(null);support();return;}
      set('trace','Original '+row.trial+' · '+row.direction+'° event · '+(invented?'the edited history begins with':'the model reads')+' source bins '+(row.k-20)+'–'+(row.k-1)+'. '+(invented?'':'The recorded outcome occupies bins '+row.k+'–'+(row.k+9)+'. ')+'Each bin spans 10 ms.');
      result=ContactForecast.forecast(ContactWeights,ContactCases.means,row,packet,family,mode,Number($('seed').value));
      let status=invented?'Invented input · no recorded outcome for this history.':'Recorded input · measured outcome shown.';
      if(mode==='wrong_movement')status+=row.donor?' Motion comes from earlier trial '+row.donor.trial+' at source bin '+row.donor.k+'. Counts and cues come from the selected history.':' No earlier trial meets the matching rule. The wrong-movement forecast is unavailable.';
      if(family==='simple' && mode==='mean')status+=' Each contact uses its first-day training mean.';
      if(family==='simple' && mode==='persistence')status+=' Each contact repeats its total from the final 100 ms of the input.';
      set('source-state',dates[row.date]+' · '+labels[row.phase]+' · trial '+row.trial+' · '+row.offset+' ms. '+status);plot(obs?row.recorded:null);support();$('error').hidden=true;
    } catch(err) {result=null;plot(null);set('error','Could not compute this forecast. '+err.message);$('error').hidden=false;}
  }
  function currentRows(){return ContactCases.rows.filter(r=>r.date===$('date').value && r.phase===$('phase').value);}
  function loadRow() {
    row=currentRows().find(r=>r.trial===Number($('trial').value)&&r.offset===Number($('offset').value))||null;
    packet=row?.packet;invented=false;set('edit-status','');update();
  }
  function offsets() {
    const rows=currentRows().filter(r=>r.trial===Number($('trial').value));
    options('offset',Object.fromEntries(rows.map(r=>[r.offset,r.offset+' ms'])),$('offset').value);
    $('offset').disabled=!rows.length;loadRow();
  }
  function trials() {
    const rows=currentRows(),trialIds=[...new Set(rows.map(r=>r.trial))], matched=rows.find(r=>r.donor);
    options('trial',Object.fromEntries(trialIds.map(id=>[id,'Trial '+id])),matched?.trial);
    $('trial').disabled=!rows.length;offsets();
  }
  function modesForFamily() {
    const family=$('family').value;
    options('mode',family==='simple'?simple:modes,$('mode').value);update();
  }
  function editSample(){
    if(!invented)return;
    const t=Number($('sample').value),c=Number($('edit-contact').value);
    $('x').value=packet.position[t][0];$('y').value=packet.position[t][1];$('prior').value=packet.counts[t][c];
  }
  function init(){
    const list=Object.fromEntries(ContactCases.contact_ids.map((id,i)=>[i,String(id)]));
    options('contact',list,0);options('edit-contact',list,0);
    options('sample',Object.fromEntries(Array.from({length:20},(_,t)=>[t,(t*10-200)+' ms'])),19);
    options('date',Object.fromEntries(Object.keys(dates).filter(d=>ContactCases.rows.some(r=>r.date===d)).map(d=>[d,dates[d]])),'test');
    options('phase',labels,query.get('phase')||'bump');options('mode',modes,'all');
    if(query.get('embed')==='1')document.body.classList.add('embedded');
    if(location.protocol==='file:'){
      $('download').href='https://eliminatenoise.github.io/NeuroTranslation/contact-forecast-offline.zip';
      $('download').textContent='Online download';
    }
    for(const id of ['date','phase'])$(id).onchange=trials;
    $('trial').onchange=offsets;$('offset').onchange=loadRow;$('seed').onchange=update;$('mode').onchange=update;$('family').onchange=modesForFamily;
    $('contact').onchange=inspect;$('sample').onchange=editSample;$('edit-contact').onchange=editSample;
    $('edit').onclick=()=>{invented=true;packet=JSON.parse(JSON.stringify(row.packet));$('edit-contact').value=$('contact').value;editSample();set('edit-status','Apply a change to recompute the forecast.');update();};
    $('apply').onclick=()=>{
      const sample=Number($('sample').value),col=Number($('edit-contact').value);
      const [x,y,count]=['x','y','prior'].map(id=>$(id).valueAsNumber);
      if(!Number.isFinite(x)||!Number.isFinite(y)||!Number.isSafeInteger(count)||count<0){
        set('edit-status','Enter finite positions and a whole nonnegative event count.');return;
      }
      packet.position[sample]=[x,y];packet.counts[sample][col]=count;update();
      set('edit-status','Applied the sample at '+(sample*10-200)+' ms for contact '+ContactCases.contact_ids[col]+'.');
    };
    $('reset').onclick=loadRow;trials();
  }
  try{init();}catch(e){set('error','Reader files could not be loaded. Extract the complete folder and reopen index.html. '+e.message);$('error').hidden=false;}
})();
