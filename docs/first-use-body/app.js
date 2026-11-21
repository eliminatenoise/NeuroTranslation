(function(){
  'use strict';
  const byId = id => document.getElementById(id);
  const canvas=byId('plane'),ctx=canvas.getContext('2d');
  const select=byId('figure'),slider=byId('frame');
  const sample=(type)=>{
    const n=60, fps=25, seconds=Array.from({length:n},(_,i)=>i/fps);
    const nodes=type==='strand'?15:type==='six'?10:8;
    const xy=seconds.map((t,frame)=>Array.from({length:nodes},(_,j)=>{
      if(type==='strand'){
        const q=j/(nodes-1);return [35+95*q+19*t,62+12*Math.sin(6*q-5*t)+3*Math.cos(t+2*q)];
      }
      const core=[[0,0],[22,0],[-20,0],[-32,4]];
      const legs=nodes-4;
      const p=j<4?core[j]:[18-38*Math.floor((j-4)/2)/Math.max(1,legs/2-1)+6*Math.sin(t*5+j),(j%2===0?1:-1)*(12+3*Math.cos(t*5+j))];
      return [52+24*t+p[0],62+6*Math.sin(t*2)+p[1]];
    }));
    return {seconds,xy};
  };
  let data=sample('strand'),timer=null,localFile=null;
  const valid=bodyForecast.valid;
  function draw(){
    const i=Number(slider.value),dt=Number(byId('horizon').value),mode=byId('method').value,here=data.xy[i];
    const earlier=data.xy.slice(Math.max(0,i-4),i+1),times=data.seconds.slice(Math.max(0,i-4),i+1);
    const result=bodyForecast.predict(earlier,times,dt,bodyFit,mode);
    const target=data.seconds[i]+dt;
    const exact=data.seconds.findIndex((t,j)=>j>i&&Math.abs(t-target)<1e-7);
    const after=exact<0?null:data.xy[exact];
    const reveal=byId('reveal').checked;
    const dots=[...earlier.flat().filter(valid),...result.map(p=>p.xy).filter(valid),...(reveal&&after?after.filter(valid):[])];
    ctx.fillStyle='#10252e';ctx.fillRect(0,0,canvas.width,canvas.height);
    if(dots.length){
      const xs=dots.map(v=>v[0]),ys=dots.map(v=>v[1]);
      const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
      const scale=Math.min(700/Math.max(1,xmax-xmin),285/Math.max(1,ymax-ymin));
      const pixel=p=>[430+(p[0]-(xmin+xmax)/2)*scale,205+(p[1]-(ymin+ymax)/2)*scale];
      ctx.strokeStyle='#24404b';ctx.lineWidth=1;
      for(let x=30;x<860;x+=50){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,410);ctx.stroke();}
      for(let y=5;y<410;y+=50){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(860,y);ctx.stroke();}
      const mark=Math.max(1, Math.min(2.2, canvas.width/Math.max(1,canvas.clientWidth)));
      if(select.value!=='private'){
        const links=select.value==='strand'?here.slice(1).map((_,j)=>[j,j+1]):
          [[1,0],[0,2],[2,3],...here.slice(4).map((_,j)=>[j<2?1:j>=here.length-6?2:0,j+4])];
        ctx.strokeStyle='#718c95';ctx.lineWidth=1.6*mark;
        for(const [a,b] of links){if(!valid(here[a])||!valid(here[b]))continue;
          ctx.beginPath();ctx.moveTo(...pixel(here[a]));ctx.lineTo(...pixel(here[b]));ctx.stroke();}
      }
      here.forEach((point,j)=>{
        if(!valid(point))return;
        const [x,y]=pixel(point);ctx.strokeStyle='#58a6a5';ctx.lineWidth=2;ctx.beginPath();let gap=true;
        for(const frame of earlier){if(!valid(frame[j])){gap=true;continue;}const q=pixel(frame[j]);if(gap)ctx.moveTo(...q);else ctx.lineTo(...q);gap=false;}ctx.stroke();
        ctx.fillStyle='#75e0d9';ctx.beginPath();ctx.arc(x,y,4*mark,0,2*Math.PI);ctx.fill();
        if(valid(result[j].xy)){const f=pixel(result[j].xy);ctx.strokeStyle='#ffbd78';ctx.lineWidth=1.8*mark;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(...f);ctx.stroke();ctx.beginPath();ctx.arc(...f,6*mark,0,2*Math.PI);ctx.stroke();}
        if(reveal&&after&&valid(after[j])){const [a,b]=pixel(after[j]);ctx.strokeStyle='#f3a3d7';ctx.beginPath();ctx.moveTo(a-4*mark,b-4*mark);ctx.lineTo(a+4*mark,b+4*mark);ctx.moveTo(a-4*mark,b+4*mark);ctx.lineTo(a+4*mark,b-4*mark);ctx.stroke();}
      });
    }
    const label={learned:'Fitted model',last_position:'Last position',unobserved:'Unseen'};
    const show=v=>valid(v)?v.map(x=>x.toFixed(2)).join(', '):'—';
    const rows=byId('rows');rows.replaceChildren();
    result.forEach((r,j)=>{const tr=rows.insertRow();for (const value of [String(j+1),show(here[j]),show(r.xy),label[r.how]])tr.insertCell().textContent=value;});
    byId('frameLabel').textContent=(i+1)+' of '+data.xy.length+' · '+data.seconds[i].toFixed(3)+' s';
    const learned=result.filter(p=>p.how==='learned').length,visible=here.filter(valid).length;
    const gap=times.slice(1).some((t,j)=>t-times[j]>bodyFit.protocol.maximum_interframe_gap_s)||times.at(-1)-times[0]>bodyFit.protocol.maximum_history_span_s;
    byId('status').textContent=learned+' of '+visible+' visible points use the fitted model. '+
      (mode==='persistence'?'This comparison holds each visible point at its last position.':earlier.length<5?'The first four frames hold each visible point at its last position.':gap?'A timing gap interrupts the recent history. Visible points stay at their last positions until five sufficiently close frames are available.':'Points need at least three observations in the latest five frames to use the fit.')+
      (reveal&&exact<0?' There is no recorded frame at this exact horizon.':'');
    return result;
  }
  function stop(){if(timer!==null)clearTimeout(timer);timer=null;byId('play').textContent='Play';}
  function tick(){
    const n=+slider.value;
    if(n>=data.xy.length-1){stop();return;}
    timer=setTimeout(()=>{slider.value=String(n+1);draw();tick();},Math.max(12,Math.min(2000,1000*(data.seconds[n+1]-data.seconds[n]))));
  }
  byId('play').onclick=()=>{if(timer!==null){stop();return;}if(+slider.value>=data.xy.length-1){slider.value='0';draw();}byId('play').textContent='Pause';tick();};
  function reset(){stop();slider.min='0';slider.max=String(data.xy.length-1);slider.value='0';draw();}
  select.onchange=()=>{if(select.value==='private'){data=localFile;byId('source').textContent='Local positions supplied by you. The page sends no coordinates to a server.';reset();return;}data=sample(select.value);byId('source').textContent='This is an invented motion. The fitted model learned from optical recordings of rodents, flies and worms.';reset();};
  slider.oninput=()=>{stop();draw();};for(const k of ['horizon','method','reveal'])byId(k).onchange=draw;
  byId('import').onchange=async e=>{
    const file=e.target.files[0]; if(!file)return;
    try{if(file.size>8*1024*1024)throw Error('Please choose a file smaller than 8 MB.');
      const j=JSON.parse(await file.text()),t=j.seconds,x=j.xy;
      if(!Array.isArray(t)||!Array.isArray(x)||!t.length||t.length>20000||x.length!==t.length||!t.every((v,i)=>Number.isFinite(v)&&(!i||v>t[i-1])))throw Error('Check the frame count and increasing times in seconds.');
      const k=Array.isArray(x[0])?x[0].length:0;
      if(k<1||k>256||!x.every(f=>Array.isArray(f)&&f.length===k&&f.every(v=>v===null||valid(v))))throw Error('Each frame needs the same 1 to 256 points. Use null for missing positions.');
      data={seconds:t,xy:x};localFile=data;if(!select.querySelector('[value="private"]'))select.add(new Option('Local file','private'));select.value='private';
      byId('fileStatus').textContent='Opened '+file.name+' locally.';byId('source').textContent='Local positions supplied by you. The page sends no coordinates to a server.';reset();
    }catch(err){byId('fileStatus').textContent=err.message;}
    e.target.value='';
  };
  byId('evidence').textContent='The study used 16 recordings from six species in three phyla. On ten held recordings near 120 ms, training on rodents, a fly and two worms increased average error from 0.140 to 0.156 compared with training on rodents alone. These errors use each observed set of points’ radius as the unit and give each recording equal weight. On the single 200 ms locust recording, the broader training reduced error from 0.161 to 0.146.';
  globalThis.bodyPreview={sample,draw};reset();
})();
