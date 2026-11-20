// Produce one page that double-clicks open without a server or network connection.
import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = new URL('./', import.meta.url);
const read = (name, encoding) => readFile(new URL(name, root), encoding);
const manifest = JSON.parse(await read('assets/asset-index.json','utf8'));
const files = ['asset-index.json', ...Object.keys(manifest)];
const assets = Object.fromEntries(await Promise.all(files.map(async name => [name,(await read('assets/'+name)).toString('base64')])));
const result = await build({entryPoints:[fileURLToPath(new URL('app/standalone.mjs',root))],bundle:true,write:false,format:'esm',target:'es2022',legalComments:'inline'});
const style = (await read('app/hand-search.css','utf8')) + '\n' + (await read('app/hand-replay.css','utf8'));
const page = (await read('page.html.in','utf8'))
  .replace('/* GAME STYLES */', () => style)
  .replace('/* MODEL FILES */', () => JSON.stringify(assets))
  .replace('/* REPLAY PROGRAM */', () => result.outputFiles[0].text.replaceAll('</script', '<\\/script'));
await writeFile(new URL('index.html',root),page);

// The predictor-only download contains coefficients and an invented past path.
// It can open independently of the separate, licensed recording search.
const fit = await read('assets/wrist-forecast-fit.json','utf8');
const fitHash = createHash('sha256').update(fit,'utf8').digest('hex');
if (fitHash!==manifest['wrist-forecast-fit.json']) throw new Error('The fit does not match the published asset index.');
const forecast = await build({entryPoints:[fileURLToPath(new URL('app/forecast-standalone.mjs',root))],
  bundle:true,write:false,format:'esm',target:'es2022',legalComments:'inline',define:{__WRIST_FIT_SHA256__:JSON.stringify(fitHash)}});
const forecastPage = (await read('forecast.html.in','utf8'))
  .replace('/* FORECAST STYLES */',()=>style)
  .replace('/* FORECAST FIT */',()=>fit)
  .replace('/* FORECAST PROGRAM */',()=>forecast.outputFiles[0].text.replaceAll('</script','<\\/script'));
await writeFile(new URL('forecast.html',root),forecastPage);
