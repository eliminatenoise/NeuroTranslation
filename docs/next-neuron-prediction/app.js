const fictional=['Amber','Birch','Cedar'],byId=id=>document.getElementById(id);
let units=[...fictional];
let bins=[];
function picks(){
  const el=byId('picks');el.replaceChildren();const legend=document.createElement('legend');legend.textContent='Units with a spike';el.append(legend);
  units.forEach((unit,i)=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=String(i);input.checked=i===1;label.append(input,document.createTextNode(' '+String(unit)));el.append(label);});
}
function paint(){
  const state=forecastSpikes(units,bins),table=byId('bars');table.replaceChildren();
  byId('clock').textContent=state.forecast_time_ms===null?'Waiting for the first observed spike.':'Using observations up to '+state.forecast_time_ms+' ms.';
  for(let i=0;i<units.length;i++){
    const row=document.createElement('div');row.className='prob';
    const label=document.createElement('span');label.textContent=units[i];
    const meter=document.createElement('meter');meter.min=0;meter.max=1;meter.value=state.next_unit_probabilities?.[i]??0;meter.setAttribute('aria-label',units[i]+' probability');
    const number=document.createElement('output');number.textContent=state.next_unit_probabilities?(100*state.next_unit_probabilities[i]).toFixed(2)+'%':'—';
    row.append(label,meter,number);table.append(row);
  }
  const hist=byId('history');hist.replaceChildren();
  for(const bin of bins){const li=document.createElement('li');li.textContent=bin.end_ms+' ms · '+(units.filter((_,i)=>bin.counts[i]).join(' and ')||'observed silence');hist.append(li);}
}
function add(time,counts){
  const prior=forecastSpikes(units,bins);
  bins.push({end_ms:time,counts});
  const label=counts.findIndex(c=>c>0);
  byId('feedback').textContent=prior.forecast_time_ms===null?'First observation recorded.':counts.reduce((a,b)=>a+b,0)!==1?'Several spikes shared this millisecond. Their order is unresolved.':'The previous forecast gave '+units[label]+' a '+(100*prior.next_unit_probabilities[label]).toFixed(2)+'% probability.';
  paint();
}
byId('event').onsubmit=e=>{
  e.preventDefault();const dt=Number(byId('dt').value),counts=Array.from(e.target.querySelectorAll('[type=checkbox]'),x=>Number(x.checked));
  if(!counts.some(Boolean)||!Number.isSafeInteger(dt)||dt<1||dt>60000){byId('feedback').textContent='Choose at least one unit and a time from 1 to 60,000 ms.';return;}
  add((bins.at(-1)?.end_ms??0)+dt,counts);
};
byId('replay').onclick=()=>{units=[...fictional];picks();byId('origin').textContent='These three units are fictional.';bins=[];for(const [t,counts] of [[1,[0,1,0]],[5,[1,0,0]],[9,[0,1,1]]])add(t,counts);};
byId('reset').onclick=()=>{bins=[];byId('feedback').textContent='';paint();};
byId('import').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
    if(file.size>4*1024*1024)throw Error('Choose a file smaller than 4 MB.');
    const x=JSON.parse(await file.text());
    if(!Array.isArray(x.local_units)||x.local_units.length>256||!Array.isArray(x.bins)||x.bins.length>4096)throw Error('Use 2–256 local units and at most 4,096 observed bins.');
    forecastSpikes(x.local_units,x.bins);
    units=x.local_units;bins=x.bins;picks();paint();
    byId('origin').textContent='This history uses your local unit names. No fit on your recording was needed.';
    byId('fileStatus').textContent='Opened '+file.name+' locally.';byId('feedback').textContent='';
  }catch(err){byId('fileStatus').textContent=err.message;}
  e.target.value='';
};
picks();paint();
