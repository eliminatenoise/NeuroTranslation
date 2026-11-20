"use strict";

// Runs in a dedicated worker. Each device retains its own observed time labels.
function parseWindow(buffer, kind) {
  const lines = new TextDecoder("utf-8", {fatal: true}).decode(buffer).trimEnd().split(/\r?\n/);
  const header = lines.shift().split(",");
  const muscle = kind === "muscle";
  const columns = muscle ? Array.from({length: 12}, (_, k) => k + 1) :
    ["Right Knee Flexion/Extension", "Left Knee Flexion/Extension"].map(name => header.indexOf(name));
  const clock = muscle ? header.indexOf("X [s]") : header.indexOf("Frame");
  if (clock < 0 || columns.includes(-1) ||
      (muscle && (header.length !== 13 || columns.some(k => !header[k].includes("MAV [Volts]"))))) {
    throw Error("The required source columns are missing.");
  }
  const times = [];
  const channels = columns.map(() => []);
  let first, previous, elapsed;
  for (const line of lines) {
    const cells = line.split(",");
    const stamp = cells[clock] !== "" ? Number(cells[clock]) : NaN;
    if (!Number.isFinite(stamp) || (previous !== undefined &&
        (muscle ? (stamp <= previous || stamp - previous > .110) : stamp - previous !== 1))) {
      throw Error("The source clock failed its continuity check.");
    }
    previous = stamp;
    const seconds = muscle ? stamp : stamp / 60;
    first ??= seconds;
    elapsed = seconds - first;
    const values = columns.map(k => cells[k] !== "" ? Number(cells[k]) : NaN);
    if (!values.every(Number.isFinite)) throw Error("A source channel contains a missing or invalid value.");
    if (elapsed >= 5 && elapsed < 45) {
      times.push(elapsed - 5);
      values.forEach((v, k) => channels[k].push(v));
    }
  }
  if (elapsed < 45 || times.length < (muscle ? 500 : 2000)) throw Error("Too little data in the fixed window.");
  return {times, channels};
}

function spectrum({times, channels}) {
  const n = times.length, m = channels.length, bins = 421;
  const weighted = new Float64Array(n * m);
  const means = channels.map(ch => ch.reduce((a, b) => a + b, 0) / n);
  for (let i = 0; i < n; i++) {
    const taper = .5 - .5 * Math.cos(2 * Math.PI * times[i] / 40);
    for (let k = 0; k < m; k++) weighted[i * m + k] = (channels[k][i] - means[k]) * taper;
  }
  const powers = new Float64Array(bins * m), totals = new Float64Array(m);
  const real = new Float64Array(m), imag = new Float64Array(m);
  for (let b = 0; b < bins; b++) {
    const omega = -2 * Math.PI * ((180 + b) / 400);
    real.fill(0);
    imag.fill(0);
    for (let i = 0; i < n; i++) {
      const phase = omega * times[i], cos = Math.cos(phase), sin = Math.sin(phase);
      for (let k = 0; k < m; k++) {
        const v = weighted[i * m + k];
        real[k] += v * cos;
        imag[k] += v * sin;
      }
    }
    for (let k = 0; k < m; k++) {
      const power = real[k] * real[k] + imag[k] * imag[k];
      powers[b * m + k] = power;
      totals[k] += power;
    }
  }
  if (!totals.every(v => Number.isFinite(v) && v > 0)) throw Error("A channel has no usable in-band power.");
  const share = new Float64Array(bins);
  let peak = 0;
  for (let b = 0; b < bins; b++) {
    for (let k = 0; k < m; k++) share[b] += powers[b * m + k] / totals[k] / m;
    if (share[b] > share[peak]) peak = b;
  }
  return {share, peak, rate: 60 * ((180 + peak) / 400), rows: n};
}

async function readVerified(file, digest) {
  if (!file || file.size > 12 * 1024 * 1024) throw Error("Choose the two original CSVs for this recording.");
  if (!self.crypto?.subtle) throw Error("File verification needs an up-to-date browser opened locally or over HTTPS.");
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", buffer));
  const hash = Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
  if (hash !== digest) throw Error("The files do not match the selected recording. Check both originals and their study ID.");
  return buffer;
}

self.onmessage = async event => {
  try {
    const {files, record} = event.data;
    const muscle = await readVerified(files[0], record.emg_sha256);
    const knee = await readVerified(files[1], record.angles_sha256);
    const emg = spectrum(parseWindow(muscle, "muscle"));
    const angles = spectrum(parseWindow(knee, "knee"));
    if (emg.rows !== record.emg_rows || angles.rows !== record.angle_rows ||
        Math.abs(emg.rate - record.emg_cycles_min) > 1e-8 || Math.abs(angles.rate - record.angle_cycles_min) > 1e-8) {
      throw Error("The recalculated peaks or sample counts differ from the published results.");
    }
    self.postMessage({emg, angles}, [emg.share.buffer, angles.share.buffer]);
  } catch (error) {
    self.postMessage({error: error.message});
  }
};
