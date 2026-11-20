// Produce one page that double-clicks open without a server or network connection.
import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = new URL('./', import.meta.url);
const read = (name, encoding) => readFile(new URL(name, root), encoding);
const manifest = JSON.parse(await read('data/manifest.json','utf8'));
const files = ['manifest.json', ...manifest.clips.map(clip=>clip.file)];
const assets = Object.fromEntries(await Promise.all(files.map(async name => [name,(await read('data/'+name)).toString('base64')])));
const result = await build({entryPoints:[fileURLToPath(new URL('viewer/standalone.mjs',root))],bundle:true,write:false,format:'esm',target:'es2022',legalComments:'inline'});
const style = await read('viewer/activity-map.css','utf8');
const page = (await read('page.html.in','utf8'))
  .replace('/* GAME STYLES */', () => style)
  .replace('/* MODEL FILES */', () => JSON.stringify(assets))
  .replace('/* REPLAY PROGRAM */', () => result.outputFiles[0].text.replaceAll('</script', '<\\/script'));
await writeFile(new URL('index.html',root),page);
