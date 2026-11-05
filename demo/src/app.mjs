import {parsePacket,parseCsv,validatePacket,combinePackets,summarizePackets,assessCompatibility,alignPackets,examplePacket} from './core.mjs';
import {normalizeFinite,buildPlotSegments} from './plot.mjs';

const $=id=>document.getElementById(id);
const colors={neural:'#7757d8',muscle:'#cd6446',displacement:'#287dba',mechanics:'#278476'};
const state={packets:[],aligned:null,cursor:0,playing:false,previousFrame:0,traces:[]};
const isExample=()=>state.packets.length>0&&state.packets.every(p=>p.dataset.origin==='constructed_example');
const streams=()=>state.packets.flatMap(p=>p.streams.map(s=>({...s,dataset:p.dataset})));
function element(tag,className,text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;}
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function download(name,value){const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function stop(){state.playing=false;$('play').textContent='▶';$('play').setAttribute('aria-label','Play aligned signals');}
function clearAlignment(){stop();state.aligned=null;state.cursor=0;$('cursor').value=0;}
function getAlignedStreams(){return state.aligned?.streams||[];}
function render(){
  const all=streams();$('packet-count').textContent=`${state.packets.length} loaded`;
  $('example-notice').hidden=!isExample();
  for(const kind of Object.keys(colors)){
    const ss=all.filter(s=>s.modality===kind);$(`count-${kind}`).textContent=`${ss.length} stream${ss.length===1?'':'s'}`;
    $(`origin-${kind}`).textContent=ss.length?[...new Set(ss.map(s=>isExample()?'Example':s.origin))].join(' / '):'No data';
  }
  $('recording-list').replaceChildren();
  for(const p of state.packets){
    const card=element('article','recording-card'),top=element('div','recording-top');top.append(element('h3','',p.dataset.name));
    const remove=element('button','remove-recording','×');remove.setAttribute('aria-label',`Remove ${p.dataset.name}`);remove.addEventListener('click',()=>{state.packets=state.packets.filter(x=>x!==p);clearAlignment();render();message('Recording removed.');});top.append(remove);card.append(top);
    card.append(element('p','',p.dataset.origin==='constructed_example'?'Constructed software example':`${p.dataset.organism||'Unknown organism'} · subject: ${p.dataset.subjectId||'unknown'}`));
    card.append(element('p','',`Clock: ${p.dataset.timebase||'unknown'}`));
    const dots=element('div','type-dots');for(const modality of [...new Set(p.streams.map(s=>s.modality))]){const dot=element('span');dot.style.background=colors[modality];dot.title=modality;dots.append(dot);}card.append(dots);
    card.append(element('p','',`${p.streams.length} streams · ${p.streams.reduce((n,s)=>n+s.t.length,0).toLocaleString()} samples`));
    card.append(element('p','',`Partition: ${p.dataset.split||'unspecified'} · ${p.dataset.license||'permission unspecified'}`));
    $('recording-list').append(card);
  }
  $('neural-coverage').replaceChildren();
  for(const [region,label] of [['brain','Brain'],['spinal','Spinal'],['peripheral','Peripheral'],['autonomic','Autonomic'],['visceral','Visceral']]){
    const ss=all.filter(s=>s.modality==='neural'&&s.region===region);const measured=ss.filter(s=>s.origin==='measured'&&s.dataset.origin!=='constructed_example');
    const origins=[...new Set(ss.map(s=>s.dataset.origin==='constructed_example'?'Example':s.origin))];
    const row=element('div','regionrow');row.append(element('span','',label),element('span','',measured.length?`${measured.length} measured`:ss.length?origins.join(' / '):'No recording'));$('neural-coverage').append(row);
  }
  const unspecified=all.filter(s=>s.modality==='neural'&&!s.region).length;
  if(unspecified){const row=element('div','regionrow');row.append(element('span','','Region undeclared'),element('span','',`${unspecified} streams`));$('neural-coverage').append(row);}
  $('alignment-warnings').replaceChildren();
  const warnings=state.packets.length?summarizePackets(state.packets).warnings:[];
  $('alignment-warnings').hidden=!warnings.length;
  if(warnings.length){$('alignment-warnings').append(element('strong','','Check the recording metadata'));const list=element('ul');for(const warning of warnings)list.append(element('li','',warning));$('alignment-warnings').append(list);}
  const aligned=Boolean(state.aligned);$('mode-badge').textContent=aligned?'Aligned samples':'Original samples';
  $('alignment-caption').textContent=aligned?`${isExample()?'Example clock':'Declared common clock'} · ${state.aligned.t.length.toLocaleString()} points · ${$('method').selectedOptions[0].textContent}`:'Each trace uses its own declared clock. Cross-dataset synchronization has not been established.';
  $('play').disabled=!aligned;$('cursor').disabled=!aligned;$('export').disabled=!aligned;$('align').disabled=!all.length;
  renderTraces();
}
function renderTraces(){
  $('traces').replaceChildren();state.traces=[];
  const ss=state.aligned?getAlignedStreams():streams();
  if(!ss.length){$('traces').append(element('p','empty','Import a recording or load the constructed example.'));$('cursor-time').textContent='— s';return;}
  for(const s of ss){
    const trace=element('article','trace'),head=element('div','trace-head'),label=element('div');
    label.append(element('strong','',s.label||s.id),element('span','unit',s.unit));label.style.color=colors[s.modality];
    head.append(label,element('span','trace-origin',`${s.modality} · ${isExample()?'constructed example':s.origin}`));trace.append(head);
    const canvas=element('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`${s.label||s.id}, ${s.unit}, ${s.origin} ${s.modality} signal`);trace.append(canvas);
    const time=state.aligned?state.aligned.t:s.t;const clock=s.dataset?.timebase||'declared packet clock';
    trace.append(element('p','trace-clock',`${time[0].toFixed(3)}–${time.at(-1).toFixed(3)} s · ${clock}${s.frame?` · frame: ${s.frame}`:''}`));
    $('traces').append(trace);state.traces.push({canvas,stream:s,time});
  }
  draw();
}
function draw(){
  for(const {canvas,stream,time} of state.traces){
    const width=Math.max(100,canvas.clientWidth),height=68,dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=width*dpr;canvas.height=height*dpr;
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);ctx.strokeStyle='#edf1f6';ctx.lineWidth=1;
    for(const fraction of [.25,.5,.75]){ctx.beginPath();ctx.moveTo(0,height*fraction);ctx.lineTo(width,height*fraction);ctx.stroke();}
    const values=stream.values;let low=Infinity,high=-Infinity;for(const v of values){if(v!==null&&Number.isFinite(v)){low=Math.min(low,v);high=Math.max(high,v);}}
    if(low===Infinity){ctx.fillStyle='#9aa7b7';ctx.font='10px Arial, sans-serif';ctx.fillText('No samples within the allowed gap',10,36);continue;}
    const y=v=>height-8-normalizeFinite(v,low,high)*(height-16),x=i=>normalizeFinite(time[i],time[0],time.at(-1))*(width-1);
    ctx.strokeStyle=colors[stream.modality]||'#315ae6';ctx.lineWidth=1.35;
    // Bins retain extrema and break at missing samples; original/aligned values remain in export.
    for(const points of buildPlotSegments(values,Math.floor(width))){
      ctx.beginPath();ctx.moveTo(x(points[0]),y(values[points[0]]));
      for(const index of points.slice(1))ctx.lineTo(x(index),y(values[index]));ctx.stroke();
      if(points.length===1){ctx.fillStyle=colors[stream.modality]||'#315ae6';ctx.beginPath();ctx.arc(x(points[0]),y(values[points[0]]),1.4,0,Math.PI*2);ctx.fill();}
    }
    ctx.fillStyle='#9aa7b7';ctx.font='8px Arial, sans-serif';ctx.fillText(high.toPrecision(3),3,9);ctx.fillText(low.toPrecision(3),3,height-1);
    if(state.aligned){const px=state.cursor*(width-1);ctx.strokeStyle='#8798af';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(px,0);ctx.lineTo(px,height);ctx.stroke();ctx.setLineDash([]);}
  }
  if(state.aligned){const t=state.aligned.t;$('cursor-time').textContent=`${(t[0]*(1-state.cursor)+t.at(-1)*state.cursor).toFixed(2)} s`;}else $('cursor-time').textContent='— s';
}
function align(){
  try{
    stop();const compatibility=assessCompatibility(state.packets);
    state.aligned=alignPackets(state.packets,{stepSeconds:Number($('step').value),maxGapSeconds:Number($('max-gap').value),method:$('method').value});
    state.cursor=0;$('cursor').value=0;render();
    const missing=getAlignedStreams().reduce((n,s)=>n+s.values.filter(v=>v===null).length,0);
    message(`${isExample()?'Constructed example aligned':'Aligned using your declared subject, recording and clock'}. ${missing.toLocaleString()} missing values retained. No samples extrapolated.`);
  }catch(error){clearAlignment();render();message(error.message||String(error),true);}
}
function loadExample(){state.packets=[validatePacket(examplePacket())];clearAlignment();render();align();}
function openImport(){$('import-error').textContent='';$('import-dialog').showModal();}
function setCsvMode(enabled){
  const fields=$('csv-fields');fields.hidden=!enabled;
  for(const control of fields.querySelectorAll('input,select'))control.disabled=!enabled;
}
setCsvMode(false);
$('load-example').addEventListener('click',loadExample);$('import-open').addEventListener('click',openImport);$('add-source').addEventListener('click',openImport);$('import-close').addEventListener('click',()=>$('import-dialog').close());
$('clear-all').addEventListener('click',()=>{state.packets=[];clearAlignment();render();message('Recordings cleared.');});
$('file').addEventListener('change',()=>setCsvMode(Boolean($('file').files[0]?.name.toLowerCase().endsWith('.csv'))));
$('import-form').addEventListener('submit',async event=>{
  event.preventDefault();$('import-error').textContent='';const file=$('file').files[0];if(!file)return;
  try{
    if(file.size>5*1024*1024)throw new Error('Use a file no larger than 5 MiB.');const text=await file.text();let packet;
    if(file.name.toLowerCase().endsWith('.csv')){
      const f=Object.fromEntries(new FormData(event.target));
      packet=parseCsv(text,{dataset:{id:f.datasetId,name:f.name,sourceUrl:f.sourceUrl,license:f.license,organism:f.organism,subjectId:f.subjectId,recordingId:f.recordingId,task:f.task,timebase:f.timebase,split:f.split},stream:{id:`${f.datasetId}-${f.modality}`,modality:f.modality,region:f.modality==='neural'?(f.region||undefined):undefined,label:f.label,unit:f.unit,frame:f.frame||undefined,origin:f.origin}});
    }else packet=parsePacket(text);
    const kept=isExample()&&packet.dataset.origin!=='constructed_example'?[]:state.packets;
    if(kept.some(p=>p.dataset.id===packet.dataset.id))throw new Error('That dataset ID is already loaded. Remove it first or use a distinct ID.');
    const prospective=[...kept,packet];
    if(prospective.reduce((n,p)=>n+p.streams.length,0)>64)throw new Error('This browser preview supports 64 selected streams. Import a smaller channel selection.');
    combinePackets(prospective); // Enforce aggregate byte/row/identity bounds before mutating UI state.
    state.packets=prospective;clearAlignment();render();$('import-dialog').close();$('import-form').reset();setCsvMode(false);message('Recording imported. Inspect its metadata, then align compatible recordings.');
  }catch(error){$('import-error').textContent=error.message||String(error);}
});
$('align').addEventListener('click',align);
for(const id of ['step','max-gap','method'])$(id).addEventListener('change',()=>{clearAlignment();render();message('Settings changed. Align again to apply them.');});
$('cursor').addEventListener('input',()=>{state.cursor=Number($('cursor').value)/1000;draw();});
$('play').addEventListener('click',()=>{state.playing=!state.playing;$('play').textContent=state.playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',state.playing?'Pause aligned signals':'Play aligned signals');state.previousFrame=performance.now();if(state.playing)requestAnimationFrame(tick);});
function tick(now){if(!state.playing||!state.aligned)return;const elapsed=now-state.previousFrame;if(elapsed>=32){state.cursor=(state.cursor+elapsed/10000)%1;$('cursor').value=Math.round(state.cursor*1000);state.previousFrame=now;draw();}requestAnimationFrame(tick);}
$('export').addEventListener('click',()=>{if(state.aligned)download('neurotranslate-0.0-aligned.json',{application:'NeuroTranslate 0.0',operation:'declared-clock alignment, not learned translation',example:isExample(),sourcePackets:state.packets,alignment:state.aligned});});
$('download-template').addEventListener('click',()=>download('neurotranslate-0.0-example.json',examplePacket()));
window.addEventListener('resize',draw);
async function catalogue(){
  try{const response=await fetch('datasets.json');if(!response.ok)return;const data=await response.json();for(const d of data.datasets||data){const card=element('article','dataset-card');card.append(element('h3','',d.name),element('p','',d.modalities?.join(' · ')||d.modality||''),element('p','',d.description||d.coverage||''),element('p','catalogue-limit',d.limit||d.pairingLimit||''));card.append(element('p','',`Reference metadata · ${(d.license||[]).join(', ')} · recordings not included`));if(d.url&&/^https:\/\//i.test(d.url)){const link=element('a','',`Source ↗`);link.href=d.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}$('catalogue-list').append(card);}$('catalogue-section').hidden=!$('catalogue-list').children.length;}catch{/* Optional catalogue is independent of data import and alignment. */}
}
loadExample();catalogue();
