/* Text selects an outcome; the single trained movement model supplies the forecast. CC0. */
(function(){
  'use strict';
  const labels=Object.freeze({
    human_touch_afferent:'Forecast spikes from a fingertip sensory nerve',
    human_leg_emg:'Forecast human lower-leg muscle electrical activity',
    human_sacrum_path:'Forecast the path of the human pelvis marker',
    macaque_cortex_to_motion:'Forecast macaque reaching movement',
    macaque_motion_to_cortex:'Forecast macaque cortical spike counts',
    rat_next_unit:'Rank the next recorded spike unit',
    optical_fluorescence:'Forecast neural calcium fluorescence',
    landmark_motion:'Forecast tracked points in a camera image'
  });
  const fail=(message)=>({kind:'unsupported',message});
  function validateProposal(p){
    if(!p||typeof p!=='object'||Array.isArray(p))return fail('Choose a supported outcome.');
    const keys=Object.keys(p).sort().join(',');
    if(p.kind==='forecast'&&keys==='kind,task'&&Object.hasOwn(labels,p.task))
      return {kind:'forecast',task:p.task,label:labels[p.task]};
    if(p.kind==='game_goal'&&keys==='effector,goal,kind'&&['left_hand','right_hand'].includes(p.effector)&&p.goal==='above_shoulder')
      return {kind:'game_goal',effector:p.effector,goal:p.goal,label:'Raise the avatar’s '+p.effector.split('_')[0]+' hand above its shoulder'};
    return fail('That proposal does not name a supported forecast or virtual action.');
  }
  function parseOutcome(text){
    if(typeof text!=='string'||text.length>1000)return fail('Enter a short description of the outcome you want.');
    const t=text.toLowerCase().normalize('NFKC').replace(/[_-]+/g,' ').replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim();
    if(!t)return fail('Enter an outcome, such as “predict the next spike” or “forecast my tracked points”.');
    if(/\b(stimulate|electrostimulate|shock|stimulator|implant control|deliver current)\b/.test(t))return fail('This interface forecasts measurements and controls a virtual avatar.');
    if(/\b(do not|don t|never|instead of|rather than)\b/.test(t))return {kind:'ambiguous',message:'Name the single outcome you want to forecast.',choices:Object.keys(labels)};
    if(/\b(raise|lift|put|place|move|bring|hold)\b/.test(t)&&/\b(hand|wrist|arm)\b/.test(t)&&/\b(shoulder|up|above|overhead)\b/.test(t)){
      const left=/\bleft\b/.test(t),right=/\bright\b/.test(t);
      if(left!==right)return validateProposal({kind:'game_goal',effector:left?'left_hand':'right_hand',goal:'above_shoulder'});
      return {kind:'ambiguous',message:'Which avatar hand should rise above its shoulder: left or right?',choices:[]};
    }
    const touch = /\b(touch|fingertip|tactile|cutaneous)\b/.test(t) && /\b(spikes?|nerve (activity|signals?)|firing)\b/.test(t);
    if(touch && !/\b(cortex|cortical|fluorescence|emg|calcium|muscle|pelvis|where|pressure|how much force|predict (the )?force|estimate (the )?force)\b/.test(t))
      return validateProposal({kind:'forecast',task:'human_touch_afferent'});
    if(/\b(force|tension|torque|newtons|pain|intentions?)\b/.test(t))return fail('This checkpoint has no direct measurement head for that quantity. Select a measured output such as EMG or tracked position.');
    const chosen=[];
    const use=(k)=>chosen.push(k);
    if(/\b(emg|electromyogra[a-z]*|muscle voltage|muscle electrical activity|muscle excitation|leg muscle activity|muscle activity in (the |my )?(leg|calf)|calf muscle activity)\b/.test(t))use('human_leg_emg');
    if(/\b(pelvis|pelvic|sacrum|sacral)\b/.test(t))use('human_sacrum_path');
    if(/\b(calcium|gcamp|fluorescen[a-z]*)\b/.test(t))use('optical_fluorescence');
    if(/\b(which (recorded )?(neuron|unit|cell)|next (recorded )?(neuron|unit|spike)|spike identity)\b/.test(t)&&!/(spike counts?|how many)/.test(t))use('rat_next_unit');
    if(/\b(cortical counts?|spike counts?|number of spikes|how many spikes|cortex activity|cortical activity)\b/.test(t))use('macaque_motion_to_cortex');
    if(/\b(macaque|monkey|handle|reaching task)\b/.test(t)&&/\b(reach|reaches|movement|path|displacement|motion|position|handle)\b/.test(t)&&!chosen.includes('macaque_motion_to_cortex'))use('macaque_cortex_to_motion');
    if(!chosen.includes('macaque_cortex_to_motion')&&!chosen.includes('human_sacrum_path')&&/\b(landmarks?|tracked points?|camera points?|on camera|wrist position|wrist movement|track my wrists?|where .*wrists?)\b/.test(t))use('landmark_motion');
    if(chosen.length===1)return validateProposal({kind:'forecast',task:chosen[0]});
    if(chosen.length>1)return {kind:'ambiguous',message:'This request matches multiple measured outcomes. Choose which to forecast first.',choices:chosen};
    return fail('Choose an outcome involving muscle voltage, pelvis movement, a reach, spike counts, the next recorded unit, fluorescence or tracked points.');
  }
  globalThis.NeuroOutcome=Object.freeze({parseOutcome,validateProposal,labels});
})();
