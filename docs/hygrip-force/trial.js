"use strict";

(() => {
  const model = globalThis.HygripForecast;
  const format = "hygrip-right-trial-v1";

  function valid(condition, message) {
    if (!condition) throw new Error(message);
  }

  function trace(values, maximum) {
    return Array.isArray(values) && values.length > 0 && values.length <= maximum
      && values.every(Number.isFinite);
  }

  function prepare(trial, weights) {
    valid(trial && trial.format === format, "Choose a HYGRIP right-hand trial JSON.");
    const first = model.firstIssue(trial.forceGoSeconds);
    valid(Number.isSafeInteger(trial.forceStartIndex) && trial.forceStartIndex >= 0
      && Array.isArray(trial.forceV) && trial.forceV.length > 0 && trial.forceV.length <= 1050
      && trial.forceV.every(value => value === null || Number.isFinite(value)),
      "Supply up to 1,050 voltage samples. Use null for omitted ticks.");
    const eeg = trial.eeg;
    if (eeg !== undefined) {
      valid(eeg && Array.isArray(eeg.channelNames) && eeg.channelNames.length === 24
        && eeg.channelNames.every((s,i) => s === weights.channelNames[i]),
      "Use the source order for all 24 scalp channels.");
      valid(Array.isArray(eeg.mV) && eeg.mV.length === 24
        && Number.isSafeInteger(eeg.startIndex) && eeg.startIndex >= 0
        && eeg.mV.every(ch => trace(ch, 21000) && ch.length === eeg.mV[0].length),
      "Supply consecutive 1 kHz scalp readings of equal length in released millivolts.");
    }
    const issues = [];
    for (let n = 0; n < 205; n++) {
      const issue = first + 5*n;
      const last = issue - trial.forceStartIndex;
      if (last < 19 || last + 6 >= trial.forceV.length || trial.forceV[last + 6] === null
          || trial.forceV.slice(last - 19, last + 1).includes(null)) continue;
      if (eeg) {
        const end = model.eegEndpoint(trial.forceGoSeconds, issue, eeg.goSeconds) - eeg.startIndex;
        if (end < 399 || end >= eeg.mV[0].length) continue;
      }
      issues.push(issue);
    }
    valid(issues.length > 0, "No scheduled cutoff has complete history and a later sensor reading.");
    return {trial, issues};
  }

  function replay(prepared, position, weights) {
    const {trial, issues} = prepared;
    const issue = issues[position];
    valid(Number.isSafeInteger(issue), "Select a cutoff within this trial.");
    const last = issue - trial.forceStartIndex;
    const input = {version: 1, forceGoSeconds: trial.forceGoSeconds, issueForceIndex: issue,
      forceV: trial.forceV.slice(last - 19, last + 1)};
    if (trial.eeg) {
      const eeg = trial.eeg;
      const endIndex = model.eegEndpoint(trial.forceGoSeconds, issue, eeg.goSeconds);
      const end = endIndex - eeg.startIndex;
      input.eeg = {goSeconds: eeg.goSeconds, endIndex, channelNames: eeg.channelNames,
        mV: eeg.mV.map(channel => channel.slice(end - 399, end + 1))};
    }
    const predictions = model.predict(input, weights);
    return {issue, seconds: issue / 50 - trial.forceGoSeconds, predictions,
      observed: trial.forceV[last + 6]};
  }

  function invented() {
    return {format, forceGoSeconds: 12, forceStartIndex: 600,
      forceV: Array.from({length: 1050}, (_, n) => {
        const phase = (n % 105) / 105;
        return -0.01 + 0.0012 * Math.cos(phase * 2 * Math.PI) + 0.00015 * Math.sin(n * 0.57);
      })};
  }

  globalThis.HygripTrial = {prepare, replay, invented};
})();
