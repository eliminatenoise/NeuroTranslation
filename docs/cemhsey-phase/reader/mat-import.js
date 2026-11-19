/* Browser-local CEMHSEY Level 5 MAT conversion for the frozen pinch protocol. */
(() => {
  'use strict';

  // This function is self-contained because its source also runs in the Blob worker.
  function createCodec() {
    const LIMIT = 250 * 1024 * 1024;
    const COMPRESSED_CHUNK = 16 * 1024;
    const FORCE_TICKS = 6000;
    const CHANNELS = 320;
    const SOURCE_COLUMNS = 61500;
    const WINDOWS = 594;
    const ELEMENT_WIDTH = 8;
    const FORMAT = 'cemhsey-array-trial-v1';
    const TIMING_MODE = 'nominal_release_index';
    const PROTOCOL_SHA256 = '1ddf690efdba4c91082999cae140f87ae6d567f3422afe68e4977cb4ca6a7781';
    const TYPE = { int8: 1, uint8: 2, int32: 5, uint32: 6, double: 9, matrix: 14, compressed: 15, utf8: 16 };
    const CLASS_DOUBLE = 6;
    const COMPLEX_OR_LOGICAL = 0x0a00;
    const LE_HOST = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
    const MESSAGES = {
      file: 'Choose a local .mat file between 128 bytes and 250 MiB.',
      level: 'Choose a MATLAB Level 5 trial file. MATLAB 7.3 and other formats are unsupported.',
      format: 'The MAT file is incomplete or has an unsupported Level 5 layout.',
      bounds: 'The decoded MAT data exceeds the 250 MiB limit.',
      compression: 'The MAT file contains a damaged or unsupported compressed variable.',
      browser: 'This browser cannot decompress MATLAB variables. Try a current browser.',
      variables: 'Use a CEMHSEY GRASP trial with data_sEMG, data_force and MVC.',
      shape: 'This trial needs a real double 320 × 61,500 data_sEMG array and a real double data_force row with at least 6,000 samples.',
      mvc: 'The trial needs a finite, positive MVC scalar. The release force values stay in fractions of MVC.',
      force: 'One of the first 6,000 force samples is nonfinite.',
      emg: 'Surface EMG gives a nonfinite RMS value inside the study windows.'
    };

    function fail(code) {
      throw Object.assign(new Error(MESSAGES[code]), {name: 'MatImportError', code});
    }

    function view(bytes) {
      return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    }

    function text(bytes) {
      return String.fromCharCode(...bytes);
    }

    function pad(length) {
      return (8 - length % 8) % 8;
    }

    function readTag(bytes, little) {
      const tag = view(bytes);
      const word = tag.getUint32(0, little);
      const shortLength = word >>> 16;
      return {
        type: word & 65535,
        length: shortLength || tag.getUint32(4, little),
        short: shortLength ? bytes.subarray(4, 4 + shortLength) : null,
        valid: shortLength <= 4
      };
    }

    async function slice(blob, start, count) {
      return new Uint8Array(await blob.slice(start, start + count).arrayBuffer());
    }

    function topTag(bytes, little, available) {
      if (bytes.length < 8) return null;
      const tag = readTag(bytes, little);
      if (!tag.valid || tag.short || tag.length > available - 8) return null;
      if (tag.type === TYPE.matrix && tag.length >= 40 && tag.length % 8 === 0) return tag;
      if (tag.type === TYPE.compressed && tag.length >= 8) return tag;
      return null;
    }

    async function scanTop(blob, little, progress) {
      let offset = 128;
      const entries = [];
      while (offset < blob.size) {
        if (entries.length === 3) fail('variables');
        const tag = topTag(await slice(blob, offset, 8), little, blob.size - offset);
        if (!tag) fail('format');
        const start = offset + 8;
        const end = start + tag.length;
        entries.push({start, end, compressed: tag.type === TYPE.compressed});
        offset = end;

        // SciPy writes no miCOMPRESSED alignment bytes. Accept a second convention
        // only when zero padding leads to an unambiguous valid next tag or EOF.
        const gap = tag.type === TYPE.compressed ? pad(tag.length) : 0;
        if (gap && end < blob.size) {
          const probe = await slice(blob, end, gap + 8);
          const raw = topTag(probe, little, blob.size - end);
          const zeroPad = probe.length >= gap && probe.subarray(0, gap).every(byte => byte === 0);
          const aligned = zeroPad && (end + gap === blob.size ||
            topTag(probe.subarray(gap), little, blob.size - end - gap));
          if (Boolean(raw) === Boolean(aligned)) fail('format');
          if (aligned) offset += gap;
        }
        progress({phase: 'reading', fraction: offset / blob.size});
      }
      if (entries.length !== 3) fail('variables');
      return entries;
    }

    class BlobCursor {
      constructor(blob) {
        this.blob = blob;
        this.position = 0;
      }

      async take(length, target) {
        if (length > this.blob.size - this.position) fail('format');
        const bytes = await slice(this.blob, this.position, length);
        this.position += length;
        if (bytes.length !== length) fail('format');
        if (!target) return bytes;
        target.set(bytes);
        return target.subarray(0, length);
      }

      async skip(length) {
        if (length > this.blob.size - this.position) fail('format');
        this.position += length;
      }

      async finish() {
        if (this.position !== this.blob.size) fail('format');
      }
    }

    class DeflateCursor {
      constructor(blob, budget) {
        if (typeof DecompressionStream !== 'function') fail('browser');
        let compressedOffset = 0;
        const input = new ReadableStream({
          async pull(controller) {
            if (compressedOffset === blob.size) {
              controller.close();
              return;
            }
            const length = Math.min(COMPRESSED_CHUNK, blob.size - compressedOffset);
            const bytes = await slice(blob, compressedOffset, length);
            compressedOffset += bytes.length;
            if (bytes.length !== length) fail('format');
            controller.enqueue(bytes);
          }
        });
        this.reader = input.pipeThrough(new DecompressionStream('deflate')).getReader();
        this.budget = budget;
        this.chunk = new Uint8Array();
        this.index = 0;
        this.position = 0;
      }

      async nextChunk() {
        let item;
        try {
          item = await this.reader.read();
        } catch {
          fail('compression');
        }
        if (item.done) return false;
        this.budget.remaining -= item.value.length;
        if (this.budget.remaining < 0) fail('bounds');
        this.chunk = item.value;
        this.index = 0;
        return true;
      }

      async consume(length, target) {
        let consumed = 0;
        while (consumed < length) {
          if (this.index === this.chunk.length && !await this.nextChunk()) fail('format');
          const count = Math.min(length - consumed, this.chunk.length - this.index);
          if (target) target.set(this.chunk.subarray(this.index, this.index + count), consumed);
          consumed += count;
          this.index += count;
        }
        this.position += length;
      }

      async take(length, target = new Uint8Array(length)) {
        await this.consume(length, target);
        return target.subarray(0, length);
      }

      async skip(length) {
        await this.consume(length, null);
      }

      async finish() {
        if (this.index !== this.chunk.length || await this.nextChunk()) fail('format');
      }

      async close() {
        try {
          await this.reader.cancel();
        } catch {
          // The conversion's own bounded error is sufficient.
        }
        this.reader.releaseLock();
      }
    }

    async function element(cursor, boundary, little) {
      if (boundary - cursor.position < 8) fail('format');
      const tag = readTag(await cursor.take(8), little);
      if (!tag.valid || !tag.type) fail('format');
      if (!tag.short && tag.length + pad(tag.length) > boundary - cursor.position) fail('format');
      return tag;
    }

    async function smallData(cursor, tag) {
      if (tag.short) return tag.short;
      const bytes = await cursor.take(tag.length);
      await cursor.skip(pad(tag.length));
      return bytes;
    }

    async function readForce(cursor, real, little) {
      const bytes = view(await cursor.take(FORCE_TICKS * ELEMENT_WIDTH));
      const force = new Float64Array(FORCE_TICKS);
      for (let tick = 0; tick < FORCE_TICKS; tick++) {
        const value = bytes.getFloat64(tick * ELEMENT_WIDTH, little);
        if (!Number.isFinite(value)) fail('force');
        force[tick] = value;
      }
      await cursor.skip(real.length - FORCE_TICKS * ELEMENT_WIDTH);
      return force;
    }

    // Keep the published ceil(2048 * tick / 200) convention exactly.
    function boundary(tick) {
      return Math.ceil(2048 * tick / 200);
    }

    async function readEmg(cursor, real, little, progress) {
      const rms = new Float64Array(WINDOWS * CHANNELS);
      const sums = [new Float64Array(CHANNELS), new Float64Array(CHANNELS)];
      const scratch = new Uint8Array(103 * CHANNELS * ELEMENT_WIDTH);
      const numbers = new Float64Array(scratch.buffer);
      const scalar = view(scratch);
      let first = 0;
      // At most two windows overlap. Square a sample once, then accumulate it
      // into both windows in time order. This also avoids subtracting large sums.
      for (let block = 0; block <= WINDOWS; block++) {
        const right = boundary((block + 1) * 10);
        const count = (right - first) * CHANNELS;
        const bytes = await cursor.take(count * ELEMENT_WIDTH, scratch);
        if (little !== LE_HOST) {
          for (let offset = 0; offset < bytes.length; offset += ELEMENT_WIDTH) {
            numbers[offset / ELEMENT_WIDTH] = scalar.getFloat64(offset, little);
          }
        }
        const newer = sums[block % 2];
        const older = sums[1 - block % 2];
        newer.fill(0);
        for (let offset = 0; offset < count; offset += CHANNELS) {
          for (let row = 0; row < CHANNELS; row++) {
            const value = numbers[offset + row];
            const square = value * value;
            newer[row] += square;
            older[row] += square;
          }
        }
        if (block > 0) {
          const window = block - 1;
          const width = right - boundary(window * 10);
          for (let row = 0; row < CHANNELS; row++) {
            // Match NumPy's mean as a division by the actual sample count.
            const value = Math.sqrt(older[row] / width);
            if (!Number.isFinite(value)) fail('emg');
            rms[window * CHANNELS + row] = value;
          }
          if (block % 24 === 0) progress({phase: 'converting', fraction: block / (WINDOWS + 1)});
        }
        first = right;
      }
      await cursor.skip(real.length - first * CHANNELS * ELEMENT_WIDTH);
      return rms;
    }

    async function readMvc(cursor, real, dimensions, flags, little) {
      // MATLAB may pack a saved scalar into a smaller real data element.
      // MVC is checked only as release metadata. Force is already normalized.
      const readers = {
        1: ['getInt8', 1], 2: ['getUint8', 1], 3: ['getInt16', 2], 4: ['getUint16', 2],
        5: ['getInt32', 4], 6: ['getUint32', 4], 7: ['getFloat32', 4], 9: ['getFloat64', 8],
        12: ['getBigInt64', 8], 13: ['getBigUint64', 8]
      };
      const reader = readers[real.type];
      const arrayClass = flags & 255;
      if (dimensions[0] !== 1 || dimensions[1] !== 1 || arrayClass < 6 || arrayClass > 15 ||
          flags & COMPLEX_OR_LOGICAL || !reader || real.length !== reader[1]) fail('mvc');
      const [get] = reader;
      const mvc = Number(view(await smallData(cursor, real))[get](0, little));
      if (!Number.isFinite(mvc) || mvc <= 0) fail('mvc');
    }

    async function readMatrix(cursor, end, little, result, seen, progress) {
      const flagsElement = await element(cursor, end, little);
      if (flagsElement.type !== TYPE.uint32 || flagsElement.length !== 8) fail('format');
      const flagBytes = view(await smallData(cursor, flagsElement));
      const flags = flagBytes.getUint32(0, little);
      const nzmax = flagBytes.getUint32(4, little);
      const dimensionsElement = await element(cursor, end, little);
      if (dimensionsElement.type !== TYPE.int32 || dimensionsElement.length !== 8) fail('shape');
      const dimensionsView = view(await smallData(cursor, dimensionsElement));
      const dims = [dimensionsView.getInt32(0, little), dimensionsView.getInt32(4, little)];
      const nameElement = await element(cursor, end, little);
      if (![TYPE.int8, TYPE.uint8, TYPE.utf8].includes(nameElement.type) ||
          !nameElement.length || nameElement.length > 63) fail('variables');
      const name = text(await smallData(cursor, nameElement));
      if (!['data_force', 'data_sEMG', 'MVC'].includes(name) || seen.has(name)) fail('variables');
      seen.add(name);
      const real = await element(cursor, end, little);
      if (name === 'MVC') {
        if (nzmax !== 0) fail('mvc');
        await readMvc(cursor, real, dims, flags, little);
      } else {
        const emg = name === 'data_sEMG';
        const correctShape = emg ? dims[0] === CHANNELS && dims[1] === SOURCE_COLUMNS :
          dims[0] === 1 && dims[1] >= FORCE_TICKS;
        if (!correctShape || (flags & 255) !== CLASS_DOUBLE || flags & COMPLEX_OR_LOGICAL || nzmax !== 0 ||
            real.type !== TYPE.double || real.length !== dims[0] * dims[1] * ELEMENT_WIDTH) fail('shape');
        if (emg) result.rms = await readEmg(cursor, real, little, progress);
        else result.force = await readForce(cursor, real, little);
      }
      if (cursor.position !== end) fail('format');
    }

    async function convert(blob, progress = () => {}) {
      if (!(blob instanceof Blob) || blob.size < 128 || blob.size > LIMIT ||
          (typeof blob.name === 'string' && !/\.mat$/i.test(blob.name))) fail('file');
      progress({phase: 'reading', fraction: 0});
      const header = await slice(blob, 0, 128);
      const marker = text(header.subarray(126, 128));
      const little = marker === 'IM';
      if ((!little && marker !== 'MI') || view(header).getUint16(124, little) !== 0x0100 ||
          !text(header.subarray(0, 116)).startsWith('MATLAB 5.0 MAT-file') ||
          !header.subarray(116, 124).every(byte => byte === 0 || byte === 32)) fail('level');
      const entries = await scanTop(blob, little, progress);
      progress({phase: 'converting', fraction: 0});
      const budget = {remaining: LIMIT - 128};
      const seen = new Set();
      const result = {};
      for (const entry of entries) {
        const payload = blob.slice(entry.start, entry.end);
        if (!entry.compressed) {
          budget.remaining -= 8 + payload.size;
          if (budget.remaining < 0) fail('bounds');
          const cursor = new BlobCursor(payload);
          await readMatrix(cursor, payload.size, little, result, seen, progress);
          await cursor.finish();
          continue;
        }
        const cursor = new DeflateCursor(payload, budget);
        try {
          const header = readTag(await cursor.take(8), little);
          if (header.length > LIMIT - 136) fail('bounds');
          if (!header.valid || header.type !== TYPE.matrix || header.short || header.length < 40 || header.length % 8) {
            fail('format');
          }
          await readMatrix(cursor, cursor.position + header.length, little, result, seen, progress);
          await cursor.finish();
        } finally {
          await cursor.close();
        }
      }
      if (!result.force || !result.rms || !seen.has('MVC')) fail('variables');
      progress({phase: 'converting', fraction: 1});
      return result;
    }

    function encode(array, count) {
      if (!(array instanceof Float64Array) || array.length !== count || !array.every(Number.isFinite)) {
        throw new TypeError('The converted trial is incomplete.');
      }
      const bytes = new Uint8Array(array.length * ELEMENT_WIDTH);
      if (LE_HOST) {
        bytes.set(new Uint8Array(array.buffer, array.byteOffset, array.byteLength));
      } else {
        const output = view(bytes);
        for (let i = 0; i < array.length; i++) output.setFloat64(i * ELEMENT_WIDTH, array[i], true);
      }
      let binary = '';
      for (let i = 0; i < bytes.length; i += 32768) binary += text(bytes.subarray(i, i + 32768));
      return btoa(binary);
    }

    function packet({force, rms}) {
      return {
        format: FORMAT,
        protocol_sha256: PROTOCOL_SHA256,
        timing_mode: TIMING_MODE,
        force_base64: encode(force, FORCE_TICKS),
        channel_rms_base64: encode(rms, WINDOWS * CHANNELS)
      };
    }

    return {convert, packet};
  }

  function serveWorker(factory) {
    const {convert} = factory();
    globalThis.onmessage = async event => {
      try {
        const result = await convert(event.data, progress => globalThis.postMessage({progress}));
        globalThis.postMessage({result}, [result.force.buffer, result.rms.buffer]);
      } catch (error) {
        const known = error?.name === 'MatImportError';
        globalThis.postMessage({error: known ? {code: error.code, message: error.message} : {
          code: 'read', message: 'The browser could not read this MAT file.'
        }});
      }
    };
  }

  function start(file, {onProgress = () => {}} = {}) {
    let worker;
    let url;
    let settle;
    const promise = new Promise((resolve, reject) => {
      settle = error => finish(reject, error);
      function finish(deliver, value) {
        if (!settle) return;
        settle = null;
        worker?.terminate();
        if (url) URL.revokeObjectURL(url);
        deliver(value);
      }
      try {
        // The Blob contains only shipped code, with no interpolation of file data.
        const source = `'use strict';\n(${serveWorker.toString()})(${createCodec.toString()});`;
        url = URL.createObjectURL(new Blob([source], {type: 'text/javascript'}));
        worker = new Worker(url);
        worker.onmessage = ({data}) => {
          if (data.progress) onProgress(data.progress);
          else if (data.result) finish(resolve, data.result);
          else if (data.error) finish(reject, Object.assign(new Error(data.error.message), {code: data.error.code}));
        };
        const workerFailure = () => finish(reject, Object.assign(
          new Error('This browser could not start the local MAT conversion worker.'), {code: 'worker'}));
        worker.onerror = workerFailure;
        worker.onmessageerror = workerFailure;
        worker.postMessage(file);
      } catch {
        finish(reject, Object.assign(
          new Error('This browser could not start the local MAT conversion worker.'), {code: 'worker'}));
      }
    });
    return {promise, cancel: () => settle?.(new DOMException('MAT conversion cancelled.', 'AbortError'))};
  }

  const {convert, packet} = createCodec();
  const api = Object.freeze({start, packet, convert});
  if (typeof module === 'object' && module.exports) module.exports = api;
  else globalThis.CemhseyMat = api;
})();
