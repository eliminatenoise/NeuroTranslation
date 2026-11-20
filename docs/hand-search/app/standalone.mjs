import { mountHandSearch } from './hand-search.mjs';

const base = new URL('./assets/', new URL('.', document.baseURI));
const assets = JSON.parse(document.getElementById('recorded-bytes').textContent);
async function readAsset(rawUrl) {
  const url = new URL(rawUrl, base);
  const name = url.pathname.split('/').pop();
  if (url.href !== new URL(name, base).href || !Object.hasOwn(assets, name)) {
    return new Response(null, {status:404});
  }
  const bytes = Uint8Array.from(atob(assets[name]), ch => ch.charCodeAt(0));
  return new Response(bytes, {headers:{'Content-Type':'application/json'}});
}
const viewer = mountHandSearch(document.getElementById('hand-search'), {baseUrl:base, fetchImpl:readAsset,headingLevel:1});
const openSelected = () => location.hash === '#forecast' ? viewer.showForecastOnly() : viewer.show();
openSelected();
window.addEventListener('hashchange',openSelected);
window.addEventListener('pagehide', () => viewer.hide());
window.addEventListener('pageshow', event => { if (event.persisted) openSelected(); });
