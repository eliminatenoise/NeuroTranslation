import {mountWristForecast} from './wrist-future.mjs';

const host=document.getElementById('wrist-forecast');
try {
  const text=document.getElementById('fitted-coefficients').textContent;
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
  const hex=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
  if(hex!==__WRIST_FIT_SHA256__) throw Error('Changed model file');
  mountWristForecast(host,JSON.parse(text));
} catch {
  host.setAttribute('role','status');
  host.textContent='The fitted coefficients could not be verified. Download a fresh copy of this page to run the forecast.';
}
