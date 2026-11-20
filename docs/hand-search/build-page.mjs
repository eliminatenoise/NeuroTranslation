// Produce one page that double-clicks open without a server or network connection.
import { build } from 'esbuild';
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
