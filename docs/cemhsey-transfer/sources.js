"use strict";

(() => {
  const protocolKeys = ["protocol_sha256", "population_sha256", "baseline_sha256", "baseline_protocol_sha256"];
  const hash = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
  const MAX_SIZE = 250 * 1024 * 1024;
  const targetForTask = [null, .1, .3, .5];

  function sourceName(file, target, role) {
    if (!file.name.toLowerCase().endsWith(".mat") || file.size < 128 || file.size > MAX_SIZE) {
      throw Error("Choose an original .mat file between 128 bytes and 250 MiB.");
    }
    const full = /^s([^_]*)_day([^_]*)_session([^_]*)_task([^_]*)_trial([^_]*)\.mat$/i.exec(file.name);
    if (!full) {
      // An incomplete name can disprove a role. It cannot establish a pair.
      const field = label => new RegExp("(?:^|[_-])" + label + "([0-9]+)(?=[_.-]|$)", "gi");
      const people = Array.from(file.name.matchAll(field("s")), match => match[1].replace(/^0+/, ""));
      const days = Array.from(file.name.matchAll(field("day")), match => Number(match[1]));
      const sessions = Array.from(file.name.matchAll(field("session")), match => Number(match[1]));
      const tasks = Array.from(file.name.matchAll(field("task")), match => Number(match[1]));
      const repeats = Array.from(file.name.matchAll(field("trial")), match => Number(match[1]));
      if (sessions.some(session => session !== 5) || tasks.some(task => targetForTask[task] !== target) ||
          repeats.some(repeat => repeat !== role) || days.some(day => day < 1 || day > 11) ||
          new Set(days).size > 1 || new Set(people).size > 1 || people.some(id => !id || Number(id) > 13)) {
        throw Error("The name conflicts with the selected Session 5 target, day range or repeat.");
      }
      return {person: people[0] ?? null, day: days[0] ?? null, originalName: false};
    }
    const fields = full.slice(1).map(field => field.replace(/^0+/, ""));
    if (fields.some(field => !/^[1-9]\d*$/.test(field))) {
      throw Error("The archive-style name needs positive whole numbers.");
    }
    const [person, dayText, sessionText, taskText, repeatText] = fields;
    const [day, session, task, repeat] = [dayText, sessionText, taskText, repeatText].map(Number);
    if (day > 11 || session !== 5 || targetForTask[task] !== target || repeat !== role) {
      throw Error("The name conflicts with the selected Session 5 target, day range or repeat.");
    }
    // Canonical archive names describe a source. Renaming any file can change what its name claims.
    const originalName = Number(person) <= 13 && fields.every((value, index) => value === full[index + 1]);
    return {person, day, originalName};
  }

  function pairState(first, second, confirmed) {
    if (!first || !second) return "missing";
    if (first.digest === second.digest) return "duplicate";
    const a = first.source, b = second.source;
    if ((a.person && b.person && a.person !== b.person) || (a.day && b.day && a.day !== b.day)) return "different";
    return (a.originalName && b.originalName) || confirmed ? "ready" : "confirm";
  }

  function readFit(bytes, bundled) {
    if (bytes.byteLength > 128 * 1024) throw Error("Choose a model under 128 KiB.");
    let fit;
    try {
      fit = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
    } catch {
      throw Error("Choose the original UTF-8 JSON fit from the array reader.");
    }
    globalThis.ArrayPinch.checkFit(fit, bundled.protocol_sha256);
    if (!protocolKeys.every(key => fit[key] === bundled[key])) {
      throw Error("This fit uses a different array-reader protocol.");
    }
    const training = fit.training?.packet_sha256;
    if (training !== undefined && (!Array.isArray(training) || !training.length ||
        !training.every(hash) || new Set(training).size !== training.length)) {
      throw Error("The fit's training fingerprints are invalid.");
    }
    return fit;
  }

  globalThis.TransferSources = Object.freeze({sourceName, pairState, readFit});
})();
