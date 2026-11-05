import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {lstat, mkdir, mkdtemp, readFile, readdir, realpath, rm, symlink, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {basename, join} from 'node:path';
import {build, SOURCE_FILES} from '../build.mjs';

const ownedScratch = await mkdtemp(join(tmpdir(), 'neurotranslate-build-versioning-'));
after(() => rm(ownedScratch, {recursive: true, force: true}));
const scratch = await realpath(ownedScratch);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const fixtures = {
  'index.html': `<!doctype html>\n<link rel="stylesheet" href="style.css">\n<script type="module" src='./app.mjs'></script>\n<a href="./datasets.json?download=1#catalogue">Data</a>\n<link rel="preload" href=/core.mjs>\n<script type="module">import './core.mjs';</script>\n<link rel="icon" href="data:image/svg+xml,%3Csvg%3Eapp.mjs%3C/svg%3E">\n<script src="https://example.test/app.mjs"></script>\n<a href="//example.test/style.css">External</a>\n<div data-note='href="app.mjs"'>app.mjs</div>\n<!-- <script src="./app.mjs"></script> -->\n`,
  'app.mjs': `import {value} from './core.mjs';\nimport './plot.mjs';\nexport {value as other} from './core.mjs?rev=1#entry';\nconst lazy = () => import('./plot.mjs');\nconst data = () => fetch('./datasets.json');\nconst bareData = () => fetch('datasets.json?mode=1#data');\nconst resource = new URL('./datasets.json', import.meta.url);\nconst external = () => fetch('https://example.test/datasets.json');\nconst bareModule = () => import('core.mjs');\nconst words = "fetch('./datasets.json')";\nconst template = \`fetch('./datasets.json')\`;\nconst regex = /fetch\\('datasets.json'\\)/;\nconst embedded = \`value \${JSON.stringify({x: fetch('./datasets.json')})}\`;\nconst nested = \`value \${\`inner \${fetch("./datasets.json")}\`}\`;\n// fetch('./datasets.json')\n/* import './core.mjs'; */\n`,
  'core.mjs': `export {normalize} from "./plot.mjs";\nexport const value = 'é';\n`,
  'plot.mjs': 'export const normalize = value => value;\n',
  'style.css': '/* app.mjs is ordinary text here. */\nbody { font-family: Arial, sans-serif; }\n',
  'datasets.json': '{"datasets":[],"note":"app.mjs is ordinary JSON text"}\n'
};

async function fixture(label) {
  const root = await mkdtemp(join(scratch, `${label}-`));
  const sourceDir = join(root, 'src');
  const outputDir = join(root, 'dist');
  await mkdir(sourceDir);
  for (const file of SOURCE_FILES) await writeFile(join(sourceDir, file), fixtures[file]);
  return {root, sourceDir, outputDir};
}

function outputFor(manifest, source) {
  const file = manifest.files.find(file => file.source === source);
  assert.ok(file, `${source} is selected`);
  return file.output;
}

async function checkManifest(paths, manifest) {
  assert.match(manifest.buildId, /^[a-f0-9]{64}$/);
  assert.equal(outputFor(manifest, 'index.html'), 'index.html');
  assert.deepEqual((await readdir(paths.outputDir)).sort(), [...manifest.files.map(file => file.output), 'build-manifest.json'].sort());
  const saved = await readFile(join(paths.outputDir, 'build-manifest.json'), 'utf8');
  assert.deepEqual(JSON.parse(saved), manifest);
  assert.ok(saved.length < 3500, 'manifest is compact');
  assert.ok(!saved.includes(scratch) && !saved.includes(paths.root) && !saved.includes('/home/'), 'no local absolute paths');
  for (const file of manifest.files) {
    assert.equal(file.source, basename(file.source));
    assert.equal(file.output, basename(file.output));
    assert.ok((await lstat(join(paths.outputDir, file.output))).isFile());
    const source = await readFile(join(paths.sourceDir, file.source));
    const output = await readFile(join(paths.outputDir, file.output));
    assert.equal(hash(source), file.sourceSha256);
    assert.equal(source.length, file.sourceBytes);
    assert.equal(hash(output), file.outputSha256);
    assert.equal(output.length, file.outputBytes);
    if (file.source !== 'index.html') assert.ok(file.output.includes(`.${manifest.buildId}.`));
    let restored = output.toString('utf8');
    for (const dependency of manifest.files) restored = restored.replaceAll(dependency.output, dependency.source);
    assert.equal(restored, source.toString('utf8'), 'only selected reference substitutions alter source bytes');
  }
  assert.ok(!(await readdir(paths.root)).some(name => name.startsWith('.dist-')), 'no staged/backup siblings remain');
}

async function checkFixtureReferences(paths, manifest) {
  const module = await readFile(join(paths.outputDir, outputFor(manifest, 'app.mjs')), 'utf8');
  const html = await readFile(join(paths.outputDir, 'index.html'), 'utf8');
  const core = await readFile(join(paths.outputDir, outputFor(manifest, 'core.mjs')), 'utf8');
  const app = outputFor(manifest, 'app.mjs');
  const plot = outputFor(manifest, 'plot.mjs');
  const data = outputFor(manifest, 'datasets.json');
  const coreName = outputFor(manifest, 'core.mjs');
  const style = outputFor(manifest, 'style.css');
  const expected = [
    [html, `href="${style}"`, style], [html, `src='./${app}'`, app],
    [html, `href="./${data}?download=1#catalogue"`, `${data}?download=1#catalogue`],
    [html, `href=/${coreName}>`, `/${coreName}`], [html, `import './${coreName}'`, coreName],
    [module, `from './${coreName}'`, coreName], [module, `import './${plot}'`, plot],
    [module, `from './${coreName}?rev=1#entry'`, `${coreName}?rev=1#entry`],
    [module, `import('./${plot}')`, plot], [module, `fetch('./${data}')`, data],
    [module, `fetch('${data}?mode=1#data')`, `${data}?mode=1#data`],
    [module, `new URL('./${data}',`, data], [module, `fetch("./${data}")`, data],
    [core, `from "./${plot}"`, plot]
  ];
  for (const [text, reference, url] of expected) {
    assert.ok(text.includes(reference), `rewritten reference ${reference}`);
    const resolved = basename(new URL(url, 'https://build.test/').pathname);
    const file = manifest.files.find(file => file.output === resolved);
    assert.ok(file, 'reference resolves to current selected output');
    assert.equal(hash(await readFile(join(paths.outputDir, resolved))), file.outputSha256);
  }
  for (const unchanged of [
    `fetch('https://example.test/datasets.json')`, `import('core.mjs')`,
    `const words = "fetch('./datasets.json')"`, `const template = \`fetch('./datasets.json')\``,
    `const regex = /fetch\\('datasets.json'\\)/`, `// fetch('./datasets.json')`, `/* import './core.mjs'; */`
  ]) assert.ok(module.includes(unchanged), `unrelated module text stays exact: ${unchanged}`);
  for (const unchanged of [
    'href="data:image/svg+xml,%3Csvg%3Eapp.mjs%3C/svg%3E"',
    'src="https://example.test/app.mjs"', 'href="//example.test/style.css"',
    `<div data-note='href="app.mjs"'>app.mjs</div>`, '<!-- <script src="./app.mjs"></script> -->'
  ]) assert.ok(html.includes(unchanged), `unrelated HTML stays exact: ${unchanged}`);
}

test('identical source builds deterministically with current imports and catalogue URLs', {timeout: 10000}, async () => {
  const paths = await fixture('same-source');
  const first = await build(paths);
  const firstManifest = await readFile(join(paths.outputDir, 'build-manifest.json'));
  const second = await build(paths);
  assert.equal(first.buildId, second.buildId);
  assert.deepEqual(first, second);
  assert.deepEqual(await readFile(join(paths.outputDir, 'build-manifest.json')), firstManifest);
  await checkManifest(paths, second);
  const html = await readFile(join(paths.outputDir, 'index.html'), 'utf8');
  const app = await readFile(join(paths.outputDir, outputFor(second, 'app.mjs')), 'utf8');
  assert.ok(html.includes(outputFor(second, 'app.mjs')) && html.includes(outputFor(second, 'style.css')));
  for (const source of ['core.mjs', 'plot.mjs', 'datasets.json']) assert.ok(app.includes(outputFor(second, source)));
  await checkFixtureReferences(paths, second);
});

test('dependency-only change refreshes every URL, resolves the graph and replaces old generated assets', {timeout: 10000}, async () => {
  const paths = await fixture('version-change');
  const first = await build(paths);
  await checkFixtureReferences(paths, first);
  await writeFile(join(paths.outputDir, 'obsolete.mjs'), 'obsolete');
  await mkdir(join(paths.outputDir, 'obsolete-directory'));
  await writeFile(join(paths.outputDir, 'obsolete-directory', 'old.json'), '{}');
  await writeFile(join(paths.sourceDir, 'core.mjs'), fixtures['core.mjs'] + 'export const revision = 2;\n');
  const second = await build(paths);
  assert.notEqual(first.buildId, second.buildId);
  for (const old of first.files.filter(file => file.source !== 'index.html')) {
    assert.notEqual(old.output, outputFor(second, old.source));
    await assert.rejects(lstat(join(paths.outputDir, old.output)), {code: 'ENOENT'});
  }
  assert.equal(first.files.find(file => file.source === 'app.mjs').sourceSha256, second.files.find(file => file.source === 'app.mjs').sourceSha256, 'app source did not change');
  await checkManifest(paths, second);
  await checkFixtureReferences(paths, second);
});

test('each selected input, including stable HTML, changes the whole-source identity', {timeout: 10000}, async () => {
  const paths = await fixture('each-input');
  const baseline = await build(paths);
  for (const source of SOURCE_FILES) {
    await writeFile(join(paths.sourceDir, source), fixtures[source] + '\n');
    const changed = await build(paths);
    assert.notEqual(changed.buildId, baseline.buildId, `${source} participates in identity`);
    for (const dependency of SOURCE_FILES.filter(file => file !== 'index.html')) assert.notEqual(outputFor(changed, dependency), outputFor(baseline, dependency));
    await writeFile(join(paths.sourceDir, source), fixtures[source]);
  }
});

test('unselected flat files, directories, siblings and symlinks never enter output or identity', {timeout: 10000}, async () => {
  const paths = await fixture('selection');
  const first = await build(paths);
  const sentinel = join(paths.root, 'private-sentinel.txt');
  await writeFile(sentinel, 'private sentinel');
  for (const name of ['.env', '.hidden.json', 'raw.json', 'quarantine.json', 'protected.json', 'experiment.mjs', 'notes.txt']) await writeFile(join(paths.sourceDir, name), 'NEVER COPY');
  for (const name of ['claude-returns', 'tests', 'raw', 'quarantine', 'protected']) {
    await mkdir(join(paths.sourceDir, name));
    await writeFile(join(paths.sourceDir, name, 'app.mjs'), 'NEVER COPY');
    await mkdir(join(paths.root, name));
    await writeFile(join(paths.root, name, 'app.mjs'), 'NEVER COPY');
  }
  await symlink(sentinel, join(paths.sourceDir, 'leak.json'));
  await symlink(join(paths.root, 'raw'), join(paths.sourceDir, 'linked-directory'));
  const second = await build(paths);
  assert.deepEqual(first, second, 'unreviewed inputs cannot affect a selected build');
  await checkManifest(paths, second);
  assert.equal(await readFile(sentinel, 'utf8'), 'private sentinel');
});

test('unsafe overlaps, symlink paths and selected symlink files fail without changing existing output', {timeout: 10000}, async () => {
  const paths = await fixture('unsafe-paths');
  await build(paths);
  const before = await readFile(join(paths.outputDir, 'build-manifest.json'));
  for (const outputDir of [paths.sourceDir, join(paths.sourceDir, 'nested'), paths.root]) await assert.rejects(build({...paths, outputDir}), /overlap/);
  const outside = join(paths.root, 'outside');
  await mkdir(outside);
  await writeFile(join(outside, 'sentinel'), 'keep');
  const outputLink = join(paths.root, 'output-link');
  await symlink(outside, outputLink);
  await assert.rejects(build({...paths, outputDir: outputLink}), /symlink/);
  await assert.rejects(build({...paths, outputDir: join(outputLink, 'new-dist')}), /symlink/);
  const sourceLink = join(paths.root, 'source-link');
  await symlink(paths.sourceDir, sourceLink);
  await assert.rejects(build({...paths, sourceDir: sourceLink}), /symlink/);
  await rm(join(paths.sourceDir, 'core.mjs'));
  await symlink(join(outside, 'sentinel'), join(paths.sourceDir, 'core.mjs'));
  await assert.rejects(build(paths), /regular file/);
  assert.deepEqual(await readFile(join(paths.outputDir, 'build-manifest.json')), before);
  assert.deepEqual(await readdir(outside), ['sentinel']);
  assert.equal(await readFile(join(outside, 'sentinel'), 'utf8'), 'keep');
  assert.ok(!(await readdir(paths.root)).some(name => name.startsWith('.dist-')));
});

