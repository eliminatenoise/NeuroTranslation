"use strict";
(() => {
  const {protocol, parents, directions} = PinchPhase;
  const format = "cemhsey-population-pinch-reader-v1";
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
  const sha = value => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  const fields = (obj, keys) => obj && typeof obj === "object" && !Array.isArray(obj) &&
    Object.keys(obj).length === keys.length && keys.every(k => Object.hasOwn(obj, k));
  const noRepeats = values => new Set(values).size === values.length;
  function archiveName(file) {
    const match = /^S([1-9]|1[0-3])_Day1_Session5_Task3_Trial([12])\.mat$/.exec(file.name);
    if (!match) throw Error("Use the exact archive filename for day 1, session 5, task 3, repeat 1 or 2. Check renamed files against the archive first.");
    if (file.size < 128 || file.size > 250 * 1024 * 1024) throw Error("A MATLAB recording must be between 128 bytes and 250 MiB.");
    return {person: match[1], repeat: Number(match[2]), file};
  }
  function roster(records, trainingPeople) {
    if (records.length !== 6 || new Set(records.map(r => r.person)).size !== 3 ||
        !noRepeats(records.map(r => r.person + "/" + r.repeat)) || records.some(r => ![1, 2].includes(r.repeat))) {
      throw Error("Choose six recordings, both repeats from each of three people.");
    }
    if (records.some(r => trainingPeople.includes(r.person))) throw Error("A calibration participant also supplied the parent model training set.");
    return records.slice().sort((a, b) => Number(a.person) - Number(b.person) || a.repeat - b.repeat);
  }
  function trainingPeople(input) {
    const ids = input.trim().split(/[\s,]+/);
    if (ids.length !== 3 || !noRepeats(ids) || !ids.every(id => /^([1-9]|1[0-3])$/.test(id))) {
      throw Error("Enter three different parent-training participant numbers from 1 to 13.");
    }
    return ids.sort((a, b) => Number(a) - Number(b));
  }
  function recordOK(digest, seen, training) {
    if (training.includes(digest)) throw Error("These decoded readings also occur in the model training files.");
    if (seen.includes(digest)) throw Error("Two recordings decode to the same force and EMG inputs.");
  }
  function keyText() { return hex(crypto.getRandomValues(new Uint8Array(16))); }
  async function signer(text) {
    if (!crypto.subtle) throw Error("Open the downloaded reader or its HTTPS page for private file checks.");
    const clean = text.trim().toLowerCase();
    if (!/^[a-f0-9]{32}$/.test(clean)) throw Error("Enter the 32-character key for this correction.");
    const raw = Uint8Array.from(clean.match(/../g), pair => parseInt(pair, 16));
    const key = await crypto.subtle.importKey("raw", raw, {name: "HMAC", hash: "SHA-256"}, false, ["sign"]);
    return async (kind, value) => hex(await crypto.subtle.sign("HMAC", key,
      new TextEncoder().encode(JSON.stringify([format, kind, value]))));
  }
  const ordered = ["format", "protocol_sha256", "parent_sha256", "source_kind", "day", "session", "task",
    "target", "fit_issues", "training_people", "fit_people", "fit_recordings", "gains"];
  function signed(p) {
    return ordered.map(key => key === "gains" ? parents.map(k => directions.map(d => p.gains[k][d])) : p[key]);
  }
  function validate(p) {
    const tags = (a, n) => Array.isArray(a) && a.length === n && noRepeats(a) && a.every(sha);
    if (!fields(p, [...ordered, "seal"]) || p.format !== format || p.protocol_sha256 !== protocol ||
        !sha(p.parent_sha256) || !["invented", "archive"].includes(p.source_kind) ||
        p.day !== 1 || p.session !== 5 || p.task !== 3 || p.target !== .5 || p.fit_issues !== 3552 ||
        !tags(p.training_people, p.source_kind === "archive" ? 3 : 0) || !tags(p.fit_people, 3) ||
        p.training_people.some(t => p.fit_people.includes(t)) || !tags(p.fit_recordings, 6) ||
        !fields(p.gains, parents) || !parents.every(k => fields(p.gains[k], directions) &&
          directions.every(d => Number.isFinite(p.gains[k][d]))) || !sha(p.seal)) {
      throw Error("This file needs the day-one 50% population protocol, three gains per parent and six distinct calibration records.");
    }
    return p;
  }
  async function make(context, records, gains, secret) {
    const fitRecords = roster(records, context.train);
    if (!fitRecords.every(r => sha(r.digest)) || !noRepeats(fitRecords.map(r => r.digest))) throw Error("Duplicate or missing decoded calibration fingerprint.");
    const tag = await signer(secret);
    const people = ids => Promise.all(ids.map(person => tag("person", person)));
    const p = {format, protocol_sha256: protocol, parent_sha256: context.hash, source_kind: context.kind,
      day: 1, session: 5, task: 3, target: .5, fit_issues: 3552,
      training_people: await people(context.train), fit_people: await people([...new Set(fitRecords.map(r => r.person))]),
      fit_recordings: await Promise.all(fitRecords.map(r => tag("record", r.digest))), gains};
    p.seal = await tag("profile", signed(p));
    return validate(p);
  }
  async function open(p, secret, context) {
    validate(p);
    if (p.parent_sha256 !== context.hash) throw Error("Choose the identical parent model JSON used for calibration.");
    if (p.source_kind !== context.kind) throw Error("The saved correction and current trial source must both be invented or both be local archive files.");
    const tag = await signer(secret);
    if (await tag("profile", signed(p)) !== p.seal) throw Error("The private key or saved file has changed.");
    const train = await Promise.all(context.train.map(person => tag("person", person)));
    if (train.length !== p.training_people.length || train.some(t => !p.training_people.includes(t))) throw Error("Check the original parent-training participant roster.");
    return tag;
  }
  async function separate(p, tag, record, training) {
    const person = await tag("person", record.person);
    if (p.fit_people.includes(person) || p.training_people.includes(person)) throw Error("This test participant supplied a calibration or parent-training recording. Choose a different participant.");
    if (p.fit_recordings.includes(await tag("record", record.digest)) || training.includes(record.digest)) throw Error("The test readings also occur in calibration or parent training.");
  }
  globalThis.PhaseProfile = Object.freeze({archiveName, roster, trainingPeople, recordOK, keyText, make, open, separate, validate});
})();
