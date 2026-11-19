"use strict";

(() => {
  const protocol = "38c0551d464f5bbc3d2c4e8a712dfb47fe2f212f7527428c3ec829ad772eac71";
  const format = "cemhsey-pinch-carry-v1";
  const parents = globalThis.PinchTransfer.parents;
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
  const sha = value => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  const fields = (object, keys) => object && typeof object === "object" && !Array.isArray(object) &&
    Object.keys(object).length === keys.length && keys.every(key => Object.hasOwn(object, key));
  const order = ["format", "protocol_sha256", "parent_fit_sha256", "target", "practice_day",
    "practice_repeat", "issue_count", "source_kind", "participant_tag", "recording_tag", "coefficients"];
  const encoder = new TextEncoder();
  function keyText() { return hex(crypto.getRandomValues(new Uint8Array(16))); }

  async function signer(text) {
    if (!crypto.subtle) throw Error("Open this reader from its HTTPS page or extracted download to use a private fit.");
    const clean = text.trim().toLowerCase();
    if (!/^[a-f0-9]{32}$/.test(clean)) throw Error("Enter the 32-character private key saved with this fit.");
    const bytes = Uint8Array.from(clean.match(/../g), pair => parseInt(pair, 16));
    const key = await crypto.subtle.importKey("raw", bytes, {name: "HMAC", hash: "SHA-256"}, false, ["sign"]);
    return async (purpose, value) => hex(await crypto.subtle.sign("HMAC", key,
      encoder.encode(JSON.stringify([format, purpose, value]))));
  }

  function validate(profile) {
    if (!fields(profile, [...order, "seal"]) || profile.format !== format || profile.protocol_sha256 !== protocol ||
        !sha(profile.parent_fit_sha256) || ![.1, .3, .5].includes(profile.target) ||
        profile.practice_day !== 9 || profile.practice_repeat !== 1 || profile.issue_count !== 592 ||
        !["invented", "local_recording"].includes(profile.source_kind) || !sha(profile.participant_tag) ||
        !sha(profile.recording_tag) || !sha(profile.seal) || !fields(profile.coefficients, parents) ||
        !Object.values(profile.coefficients).every(Number.isFinite)) {
      throw Error("Choose a compatible day 9 first-repeat fit with two coefficients for this carry protocol.");
    }
    return profile;
  }

  function signedValues(profile) {
    return order.map(key => key === "coefficients" ? parents.map(p => profile.coefficients[p]) : profile[key]);
  }

  function read(bytes) {
    if (bytes.byteLength > 4096) throw Error("Choose a private practice-fit JSON under 4 KiB.");
    let profile;
    try { profile = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes)); }
    catch { throw Error("The practice fit must be a UTF-8 JSON file."); }
    return validate(profile);
  }

  async function create(context, first, coefficients, secret) {
    if (first.day !== 9 || !first.person || !sha(first.digest)) throw Error("Check the day 9 first-repeat source.");
    const tag = await signer(secret);
    const profile = {format, protocol_sha256: protocol, parent_fit_sha256: context.fitHash, target: context.q,
      practice_day: 9, practice_repeat: 1, issue_count: 592, source_kind: context.kind,
      participant_tag: await tag("participant", first.person), recording_tag: await tag("recording", first.digest),
      coefficients: Object.fromEntries(parents.map(parent => [parent, coefficients[parent]]))};
    profile.seal = await tag("profile", signedValues(profile));
    return validate(profile);
  }

  function compatible(profile, context) {
    validate(profile);
    if (profile.parent_fit_sha256 !== context.fitHash) throw Error("Open the exact parent model file used on day 9.");
    if (profile.target !== context.q) throw Error("The private fit uses a different prescribed target.");
    if (profile.source_kind !== context.kind) throw Error("Invented examples and local recordings need separate practice fits.");
  }

  async function match(profile, secret, context, first, second, training) {
    compatible(profile, context);
    const tag = await signer(secret);
    if (await tag("profile", signedValues(profile)) !== profile.seal) throw Error("The private key or file has changed. Check the original pair.");
    if (!first || !second || first.day !== 10 || second.day !== 10 || !first.person || first.person !== second.person)
      throw Error("Check both day 10 repeat roles and their common participant against the archive.");
    if (!sha(first.digest) || !sha(second.digest) || first.digest === second.digest)
      throw Error("The comparison needs two distinct decoded day 10 repeats.");
    if (await tag("participant", first.person) !== profile.participant_tag)
      throw Error("The day 9 fit belongs to a different participant.");
    for (const digest of [first.digest, second.digest, ...training]) {
      if (await tag("recording", digest) === profile.recording_tag)
        throw Error("The day 9 practice readings also occur in day 10 or parent training. Choose distinct recordings.");
    }
    if (training.includes(first.digest) || training.includes(second.digest))
      throw Error("A day 10 repeat also occurs in the parent training recordings.");
    return profile.coefficients;
  }

  globalThis.PinchCarry = Object.freeze({protocol, format, keyText, read, create, compatible, match});
})();
