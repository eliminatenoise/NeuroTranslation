const ForceCharts = (() => {
  const ns = 'http://www.w3.org/2000/svg';
  const ink = '#283d32', muted = '#53675a', grid = '#d9e2d8', orange = '#ae4324', blue = '#226696';
  function el(tag, attrs={}, text='') {
    const node=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attrs)) node.setAttribute(k,String(v));
    if(text) node.textContent=text;
    return node;
  }
  function svg(w,h,title,desc){
    const root=el('svg',{xmlns:ns,viewBox:'0 0 '+w+' '+h,role:'img','aria-label':title,'font-family':'Arial, sans-serif'});
    root.append(el('title',{},title),el('desc',{},desc),el('rect',{width:w,height:h,fill:'#fff'}));
    return root;
  }
  function label(x,y,txt,size=13,extra={}){return el('text',{x,y,fill:muted,'font-size':size,...extra},txt)}
  function nice(v){
    const p=10**Math.floor(Math.log10(Math.max(v,1e-6)));
    return ([1,2,2.5,5,10].find(n=>n>=v/p)||10)*p;
  }
  function curve(series,cursor,width,exporting=false,caption=''){
    const w=width, top=exporting?88:24, right=15, left=43, bottom=exporting?65:43, h=(width<430?217:285)+(exporting?91:0);
    const end=h-bottom, x=k=>left+(w-left-right)*k/(series.length-1);
    const step=nice(Math.max(10,...series.flatMap(p=>[p.edited_N,p.reference_N]))/4);
    const maxY=step*Math.ceil(Math.max(10,...series.flatMap(p=>[p.edited_N,p.reference_N]))/step);
    const y=n=>end-(end-top)*n/maxY;
    const title='Predicted platform load from invented inputs';
    const desc='Edited muscle signal in solid rust; reference signal in dashed blue. Same marker paths. Target times in seconds, force in newtons.';
    const s=svg(w,h,title,desc);
    if(exporting){
      s.append(label(left,21,title,17,{'font-weight':700,fill:ink}));
      s.append(label(left,42,caption,13),label(left,61,'Edited muscle signal (solid)   /   Reference signal (dashed)',13));
    }
    for(let tick=0;tick<=maxY;tick+=step){
      s.append(el('line',{x1:left,x2:w-right,y1:y(tick),y2:y(tick),stroke:grid}),label(left-7,y(tick)+4,String(tick),12,{'text-anchor':'end'}));
    }
    s.append(label(8,top-10,'N',12));
    const ticks=width<450?[0,12,24,36,48]:[0,8,16,24,32,40,48];
    for(const k of ticks) s.append(label(x(k),end+17,(series[k].target_ms/1000).toFixed(2),12,{'text-anchor':'middle'}));
    s.append(label((left+w-right)/2,end+38,'Target time in the invented walk (s)',12,{'text-anchor':'middle'}));
    const path=key=>series.map((row,i)=>(i?'L':'M')+x(i).toFixed(2)+' '+y(row[key]).toFixed(2)).join(' ');
    s.append(el('path',{d:path('edited_N'),fill:'none',stroke:orange,'stroke-width':3.5,'stroke-linejoin':'round'}));
    s.append(el('path',{d:path('reference_N'),fill:'none',stroke:blue,'stroke-width':2.4,'stroke-dasharray':'6 4','stroke-linejoin':'round'}));
    s.append(el('line',{x1:x(cursor),x2:x(cursor),y1:top,y2:end,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3'}));
    for(const [key,color] of [['edited_N',orange],['reference_N',blue]]){
      s.append(el('circle',{cx:x(cursor),cy:y(series[cursor][key]),r:3.9,fill:'#fff',stroke:color,'stroke-width':2.1}));
    }
    if(exporting)s.append(label(left,h-5,'Data: Moissenet & Schreiber (2020), figshare v8, CC BY 4.0. Model and invented example: NeuroTranslation.',11));
    s.setAttribute('data-left',left);s.setAttribute('data-right',w-right);
    return s;
  }
  function bars(rows,width,exporting=false,caption=''){
    const w=width,top=exporting?77:14,dy=40,left=2,right=57,xmax=w-right;
    const title='Absolute error on held-out walkers';
    const s=svg(w,top+rows.length*dy+(exporting?27:13),title,'All values are person-balanced mean absolute errors in newtons. Smaller is closer to the recorded plate load.');
    if(exporting){s.append(label(2,22,title,18,{'font-weight':700,fill:ink}),label(2,43,'Person-balanced mean absolute error (N). '+caption,13));}
    const max=Math.max(...rows.map(r=>r.mae));
    rows.forEach((r,i)=>{
      const y=top+i*dy, bar=(xmax-left)*r.mae/max;
      s.append(label(left,y+9,r.short,13,{fill:ink}),el('rect',{x:left,y:y+15,width:xmax-left,height:7,rx:3,fill:'#eaf0e9'}),
        el('rect',{x:left,y:y+15,width:bar,height:7,rx:3,fill:r.kind==='privileged'?blue:r.primary?orange:'#748b79'}),
        label(w-1,y+22,r.mae.toFixed(1)+' N',12,{'text-anchor':'end',fill:ink}));
    });
    if(exporting)s.append(label(2,top+rows.length*dy+13,'Data: Moissenet & Schreiber (2020), figshare v8, CC BY 4.0. Analysis: NeuroTranslation.',11));
    return s;
  }
  return {curve,bars};
})();
