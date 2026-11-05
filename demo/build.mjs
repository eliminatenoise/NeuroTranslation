import {constants} from 'node:fs';
import {lstat, mkdtemp, open, realpath, rename, rm, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {basename, dirname, extname, isAbsolute, join, relative, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

// This is the reviewed selection for the existing data companion, not the game.
// New production inputs require an explicitly reviewed extension of this list.
export const SOURCE_FILES = Object.freeze([
  'app.mjs', 'core.mjs', 'datasets.json', 'index.html', 'plot.mjs', 'style.css'
]);
const sha256 = value => createHash('sha256').update(value).digest('hex');

function containsPath(parent, child) {
  const part = relative(parent, child);
  return part === '' || (!isAbsolute(part) && part !== '..' && !part.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`));
}

async function plainDirectory(path) {
  const info = await lstat(path);
  if (!info.isDirectory() || info.isSymbolicLink() || await realpath(path) !== path) {
    throw new Error('Build paths must be real directories without symlink components.');
  }
}

async function outputExists(path) {
  try {
    const info = await lstat(path);
    if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('Output must be an owned directory, never a symlink or file.');
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function readSources(sourceDir) {
  const files = [];
  for (const source of SOURCE_FILES) {
    const path = join(sourceDir, source);
    const info = await lstat(path);
    if (!info.isFile() || info.isSymbolicLink()) throw new Error(`Selected source must be a regular file: ${source}`);
    const handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
    try {
      if (!(await handle.stat()).isFile()) throw new Error(`Selected source is not a regular file: ${source}`);
      const bytes = await handle.readFile();
      files.push({source, bytes, sourceSha256: sha256(bytes)});
    } finally {
      await handle.close();
    }
  }
  return files;
}

function identity(files) {
  return sha256(JSON.stringify({selection: 'data-companion-v1', files: files.map(file => [file.source, file.bytes.length, file.sourceSha256])}));
}

function rewriteURL(value, mapping, allowBare) {
  const match = /^(\.\/|\/)?([^/?#]+)([?#][\s\S]*)?$/.exec(value);
  if (!match || (!allowBare && !match[1]) || !mapping.has(match[2])) return value;
  return `${match[1] || ''}${mapping.get(match[2])}${match[3] || ''}`;
}

function quotedEnd(text, start) {
  const quote = text[start];
  for (let at = start + 1; at < text.length; at++) {
    if (text[at] === '\\') at++;
    else if (text[at] === quote) return at + 1;
  }
  throw new Error('Unterminated source string.');
}

// Literal import/export specifiers and fetch/new URL arguments only. A small
// lexer keeps comments, unrelated strings, regexes and template text intact.
function rewriteModule(text, mapping) {
  const edits = [];
  function scan(start, interpolation = false) {
    const previous = [];
    let depth = 0;
    for (let at = start; at < text.length;) {
      const char = text[at];
      const last = previous.at(-1);
      if (/\s/.test(char)) { at++; continue; }
      if (text.startsWith('//', at)) { const end = text.indexOf('\n', at + 2); at = end < 0 ? text.length : end; continue; }
      if (text.startsWith('/*', at)) { const end = text.indexOf('*/', at + 2); if (end < 0) throw new Error('Unterminated source comment.'); at = end + 2; continue; }
      if (char === '"' || char === "'") {
        const end = quotedEnd(text, at);
        const value = text.slice(at + 1, end - 1);
        const directImport = last === 'from' || last === 'import';
        const call = last === '(' ? previous.at(-2) : null;
        const callOwner = previous.at(-3);
        const localCall = (call === 'import' || call === 'fetch') && callOwner !== '.' && callOwner !== '?.';
        const urlCall = call === 'URL' && callOwner === 'new';
        if (directImport || localCall || urlCall) {
          const replacement = rewriteURL(value, mapping, call === 'fetch' || urlCall);
          if (replacement !== value) edits.push({start: at + 1, end: end - 1, replacement});
        }
        previous.push('literal'); at = end; continue;
      }
      if (char === '`') {
        at++;
        while (at < text.length && text[at] !== '`') {
          if (text[at] === '\\') at += 2;
          else if (text.startsWith('${', at)) at = scan(at + 2, true);
          else at++;
        }
        if (at >= text.length) throw new Error('Unterminated source template.');
        previous.push('literal'); at++; continue;
      }
      const regexStart = char === '/' && (!last || (last.length === 1 && '({[=,:;!?&|+*%<>~^-'.includes(last)) || ['return', 'throw', 'case', 'yield', '=>'].includes(last));
      if (regexStart) {
        at++; let bracket = false;
        while (at < text.length) {
          if (text[at] === '\\') at += 2;
          else if (text[at] === '/' && !bracket) { at++; break; }
          else { if (text[at] === '[') bracket = true; if (text[at] === ']') bracket = false; at++; }
        }
        while (/[a-z]/i.test(text[at] || '') && at < text.length) at++;
        previous.push('literal'); continue;
      }
      if (/[\w$]/.test(char)) {
        const match = /^[\w$]+/.exec(text.slice(at))[0]; previous.push(match); at += match.length; continue;
      }
      if (char === '}' && interpolation && depth === 0) return at + 1;
      if (char === '{') depth++;
      if (char === '}') depth--;
      const punctuation = text.startsWith('?.', at) || text.startsWith('=>', at) ? text.slice(at, at + 2) : char;
      previous.push(punctuation); at += punctuation.length;
    }
    if (interpolation) throw new Error('Unterminated source template expression.');
    return text.length;
  }
  scan(0);
  for (const edit of edits.sort((a, b) => b.start - a.start)) text = text.slice(0, edit.start) + edit.replacement + text.slice(edit.end);
  return text;
}

function rewriteHTML(text, mapping) {
  return text.replace(/<!--[\s\S]*?-->|<script\b(?:[^"'<>]|"[^"]*"|'[^']*')*>[\s\S]*?<\/script\s*>|<(?:[^"'<>]|"[^"]*"|'[^']*')*>/gi, tag => {
    if (tag.startsWith('<!--')) return tag;
    const end = /^<(?:[^"'<>]|"[^"]*"|'[^']*')*>/.exec(tag)?.[0].length || tag.length;
    const opening = tag.slice(0, end).replace(/(\s+)([^\s"'<>/=]+)(\s*=\s*)(?:(["'])([\s\S]*?)\4|([^\s"'=<>`]+))/g, (whole, space, name, equals, quote, quoted, bare) => {
      if (!/^(src|href)$/i.test(name)) return whole;
      const value = quoted ?? bare;
      const next = rewriteURL(value, mapping, true);
      return next === value ? whole : `${space}${name}${equals}${quote || ''}${next}${quote || ''}`;
    });
    const body = tag.slice(end);
    if (/^<script\b/i.test(opening) && /\btype\s*=\s*(["'])module\1/i.test(opening) && !/\bsrc\s*=/i.test(opening)) {
      const close = /<\/script\s*>$/i.exec(body);
      return opening + rewriteModule(body.slice(0, close.index), mapping) + close[0];
    }
    return opening + body;
  });
}

/** Replace one explicitly owned output directory; never scan/copy its siblings. */
export async function build({sourceDir = 'src', outputDir = 'dist'} = {}) {
  sourceDir = resolve(sourceDir); outputDir = resolve(outputDir);
  if (containsPath(sourceDir, outputDir) || containsPath(outputDir, sourceDir)) throw new Error('Source and output directories must not overlap.');
  await plainDirectory(sourceDir);
  await plainDirectory(dirname(outputDir));
  await outputExists(outputDir);
  const files = await readSources(sourceDir);
  const buildId = identity(files);
  const mapping = new Map(files.map(({source}) => [source, extname(source) === '.html' ? source : `${basename(source, extname(source))}.${buildId}${extname(source)}`]));
  const outputs = files.map(file => {
    let bytes = file.bytes;
    if (/\.(html|mjs)$/.test(file.source)) {
      const text = bytes.toString('utf8');
      if (!Buffer.from(text).equals(bytes)) throw new Error(`Selected text must be valid UTF-8: ${file.source}`);
      bytes = Buffer.from(extname(file.source) === '.html' ? rewriteHTML(text, mapping) : rewriteModule(text, mapping));
    }
    return {...file, output: mapping.get(file.source), outputBytes: bytes};
  });
  const manifest = {schemaVersion: 1, selection: 'data-companion-v1', hashAlgorithm: 'sha256', buildId, files: outputs.map(file => ({source: file.source, sourceBytes: file.bytes.length, sourceSha256: file.sourceSha256, output: file.output, outputBytes: file.outputBytes.length, outputSha256: sha256(file.outputBytes)}))};
  let stage = await mkdtemp(join(dirname(outputDir), `.${basename(outputDir)}-build-`));
  let backup;
  let installed = false;
  try {
    for (const file of outputs) await writeFile(join(stage, file.output), file.outputBytes, {flag: 'wx'});
    await writeFile(join(stage, 'build-manifest.json'), `${JSON.stringify(manifest)}\n`, {flag: 'wx'});
    if (identity(await readSources(sourceDir)) !== buildId) throw new Error('Selected source changed during build; output was not replaced.');
    if (await outputExists(outputDir)) {
      backup = `${stage}-previous`;
      await rename(outputDir, backup);
    }
    try {
      await rename(stage, outputDir);
      stage = undefined; installed = true;
    } catch (error) {
      if (backup) { await rename(backup, outputDir); backup = undefined; }
      throw error;
    }
    if (backup) { await rm(backup, {recursive: true}); backup = undefined; }
    return manifest;
  } finally {
    if (stage) await rm(stage, {recursive: true, force: true});
    // A failed rollback must retain the previous build for explicit recovery.
    if (backup && installed) await rm(backup, {recursive: true, force: true});
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const manifest = await build();
  console.log(`Built browser-local data companion ${manifest.buildId} (${manifest.files.length} selected files).`);
}
