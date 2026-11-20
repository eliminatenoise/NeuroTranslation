function customInput(obj) {
  if (typeof obj !== "object" || obj === null || Array.isArray(obj)) throw Error("Choose a history JSON object.");
  for (const [key, expected] of [["feature_order", channels], ["frames_before_cutoff", lags]]) {
    if (key in obj && JSON.stringify(obj[key]) !== JSON.stringify(expected)) throw Error("The " + key + " declaration differs from this model.");
  }
  if (Object.keys(obj).some(key => !["history_degrees", "origin", "feature_order", "frames_before_cutoff"].includes(key))) {
    throw Error("Keep only history_degrees, feature_order, frames_before_cutoff and an optional origin. A JSON history has no verified endpoint.");
  }
  return {history: historyRows(obj.history_degrees), cutoff: 0, mode: "custom"};
}

function parseMember(text, sources, member) {
  // Official member bytes are identified by SHA-256 before decoding. These
  // exports have one plain header line and unquoted numeric records.
  const lines = text.trimEnd().split(/\r?\n/);
  const fields = lines.shift().replace(/^\uFEFF/, "").split(",");
  const indexes = [sources.frame_column, ...sources.columns].map(name => {
    const i = fields.indexOf(name);
    if (i < 0 || fields.lastIndexOf(name) !== i) throw Error("The joint-angle header differs from this release.");
    return i;
  });
  const values = [];
  const frames = [];
  const cuts = [];
  let run = 0;
  for (let i = 0; i < lines.length; i++) {
    const parts = lines[i].split(",");
    const selected = indexes.map(k => {
      const s = parts[k]?.trim();
      return s ? Number(s) : NaN;
    });
    const [frame, ...row] = selected;
    const valid = Number.isSafeInteger(frame) && row.every(Number.isFinite);
    run = valid ? (i && frame === frames[i - 1] + 1 ? run + 1 : 1) : 0;
    frames.push(frame); values.push(row);
    if (run >= 40) cuts.push(i - 15);
  }
  if (!cuts.length || values.length !== member.rows || cuts.length !== member.eligible_windows) throw Error("The stored rows or eligible windows differ from the study.");
  return {values, frames, cuts, member};
}

function recordedInput(trial, index) {
  const cut = trial.cuts[index];
  return {mode: "recorded", history: lags.map(lag => trial.values[cut - lag]),
    cutoff: trial.frames[cut], target: trial.values[cut + 15].slice(2, 4), trial, index};
}

async function openInput(file, study) {
  if (!file || file.size === 0 || file.size > 32 * 1024 * 1024) throw Error("Choose a nonempty input smaller than 32 MiB.");
  if (/\.json$/i.test(file.name)) {
    if (file.size > 16384) throw Error("The five-row JSON file must be under 16 KiB.");
    let obj;
    try { obj = JSON.parse(await file.text()); } catch { throw Error("This file could not be read as JSON."); }
    return customInput(obj);
  }
  if (!/\.csv$/i.test(file.name)) throw Error("Choose an original held-out joint-angle CSV or a five-row JSON history.");
  if (!globalThis.crypto?.subtle) throw Error("Open the saved page directly or use HTTPS so your browser can verify this file.");
  const bytes = await file.arrayBuffer();
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), x => x.toString(16).padStart(2, "0")).join("");
  const member = study.members.find(row => row.sha256 === digest);
  if (!member) throw Error("This file does not match a held-out joint-angle file in release 1.0.0. Choose the original, unedited CSV.");
  const trial = parseMember(new TextDecoder().decode(bytes), study, member);
  return recordedInput(trial, 0);
}
