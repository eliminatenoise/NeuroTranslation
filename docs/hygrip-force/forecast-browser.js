"use strict";

(() => {
  const windowSize = 400;
  const ieee = new DataView(new ArrayBuffer(8));
  const binaryScale = 1n << 1074n;
  const spectrum = [4, 5, 6, 7, 8, 9, 10, 11, 12].map(k =>
    Array.from({length: windowSize}, (_, n) => [
      Math.cos(2 * Math.PI * k * n / windowSize),
      Math.sin(2 * Math.PI * k * n / windowSize),
    ]),
  );
  const hann = Array.from(
    {length: windowSize}, (_, n) => 0.5 - 0.5 * Math.cos(2 * Math.PI * n / (windowSize - 1)),
  );
  const massFactor = 2 / (windowSize * hann.reduce((sum, w) => sum + w * w, 0));

  function insist(test, message) {
    if (!test) throw new Error(message);
  }

  function clock(value, name) {
    insist(Number.isFinite(value) && value >= 0 && value <= 86400,
      name + " must be a finite device-local time in seconds from 0 to 86400.");
    ieee.setFloat64(0, value);
    const bits = ieee.getBigUint64(0);
    const exponent = Number((bits >> 52n) & 2047n);
    const fraction = bits & ((1n << 52n) - 1n);
    return exponent === 0 ? fraction : ((1n << 52n) + fraction) << BigInt(exponent - 1);
  }

  function finiteArray(values, length) {
    return Array.isArray(values) && values.length === length && values.every(Number.isFinite);
  }

  function timing(go, index) {
    const clockGo = clock(go, "Force Go");
    insist(Number.isSafeInteger(index) && index >= 0, "Force issue index must be a nonnegative integer.");
    const anchor = (100n * clockGo + binaryScale) / (2n * binaryScale);
    const offset = BigInt(index) - anchor;
    insist(offset >= 20n && offset <= 1040n && (offset - 20n) % 5n === 0n,
      "Choose one of the scheduled force issues, from Go + 20 to Go + 1040 ticks in steps of 5.");
    const tickBase = 50n * binaryScale;
    const elapsed = BigInt(index) * binaryScale - 50n * clockGo;
    // Phase comparisons below are rational, including exact cue edges.
    const cycle = (20n * elapsed) / (42n * tickBase);
    const phaseUnits = 20n * elapsed - 42n * cycle * tickBase;
    const targetPhaseUnits = (20n * (elapsed + 6n * binaryScale)) % (42n * tickBase);
    const tau = index / 50 - go;
    return {
      elapsed, tickBase,
      features: [tau, Number(cycle), tau - 2.1 * Number(cycle),
        Number(phaseUnits < 31n * tickBase), Number(targetPhaseUnits < 31n * tickBase)],
    };
  }

  function eegEndpoint(forceGo, index, eegGo) {
    const planned = timing(forceGo, index);
    const eegClock = clock(eegGo, "EEG Go");
    const total = 1000n * (50n * eegClock + planned.elapsed - binaryScale);
    insist(total >= 0n, "The aligned window falls before the start of the EEG clock.");
    return Number(total / planned.tickBase);
  }

  function eegFeatures(channels) {
    const average = new Float64Array(windowSize);
    for (const channel of channels) {
      for (let i = 0; i < windowSize; ++i) average[i] += channel[i] / 24;
    }
    return channels.flatMap(channel => {
      const referenced = channel.map((value, i) => value - average[i]);
      const mean = referenced.reduce((sum, value) => sum + value, 0) / windowSize;
      const centered = referenced.map(value => value - mean);
      const rms = Math.sqrt(centered.reduce((sum, value) => sum + value * value, 0) / windowSize);
      const powers = spectrum.map(trig => {
        let real = 0;
        let imaginary = 0;
        for (let n = 0; n < windowSize; ++n) {
          const taper = centered[n] * hann[n];
          real += taper * trig[n][0];
          imaginary += taper * trig[n][1];
        }
        return (real * real + imaginary * imaginary) * massFactor;
      });
      const alpha = powers[0] + powers[1];
      const beta = powers.slice(2).reduce((sum, value) => sum + value, 0);
      return [mean, rms, alpha, beta];
    });
  }

  function ridgePrediction(features, model) {
    return model.intercept + features.reduce(
      (sum, value, i) => sum + ((value - model.mean[i]) / model.scale[i]) * model.coefficients[i], 0,
    );
  }

  function predict(input, weights) {
    insist(input && input.version === 1, "Use version 1 of the window input format.");
    const plan = timing(input.forceGoSeconds, input.issueForceIndex);
    insist(finiteArray(input.forceV, 20), "Supply 20 finite transducer readings in signed volts.");
    const last = input.forceV[19];
    const recent = last - input.forceV[15];
    const longer = last - input.forceV[9];
    const inputs = [...plan.features, ...input.forceV, recent / 0.08, longer / 0.2];
    const output = {
      timing: ridgePrediction(plan.features, weights.timing),
      force_history: ridgePrediction(inputs, weights.force_history),
      persistence: last,
      backward_slope: last + 1.5 * recent,
    };
    if (input.eeg !== undefined) {
      const eeg = input.eeg;
      insist(eeg && Array.isArray(eeg.channelNames) && eeg.channelNames.length === 24
        && eeg.channelNames.every((name, i) => name === weights.channelNames[i]),
      "Supply the 24 scalp channel names in the same order as the HYGRIP source.");
      const endpoint = eegEndpoint(input.forceGoSeconds, input.issueForceIndex, eeg.goSeconds);
      insist(eeg.endIndex === endpoint && endpoint >= 399,
        "The EEG window must end at exact device index " + endpoint + " and contain 400 samples.");
      insist(Array.isArray(eeg.mV) && eeg.mV.length === 24
        && eeg.mV.every(channel => finiteArray(channel, 400)),
      "Supply 400 finite readings in released millivolts for each scalp channel.");
      output.aligned = ridgePrediction([...inputs, ...eegFeatures(eeg.mV)], weights.aligned);
    }
    insist(Object.values(output).every(Number.isFinite), "The input produced a nonfinite forecast.");
    return output;
  }

  function invented(weights) {
    const forceGoSeconds = 12.125;
    const issueForceIndex = 626;
    const goSeconds = 12.25;
    return {
      version: 1,
      forceGoSeconds,
      issueForceIndex,
      forceV: Array.from({length: 20}, (_, n) => -0.0106 + n * 0.000025
        + Math.sin(0.3 * n) * 0.00004),
      eeg: {
        goSeconds,
        endIndex: eegEndpoint(forceGoSeconds, issueForceIndex, goSeconds),
        channelNames: weights.channelNames,
        mV: weights.channelNames.map((_, c) => Array.from({length: 400}, (_, n) =>
          0.0015 * Math.sin(c * 0.7)
          + 0.000005 * Math.sin((c * 0.4) + n * 0.077)
          + 0.000003 * Math.cos((c * 0.3) + n * (0.12 + 0.002 * c)),
        )),
      },
    };
  }

  const api = {eegEndpoint, eegFeatures, invented, predict, timing};
  globalThis.HygripForecast = api;
  if (typeof module !== "undefined") module.exports = api;
})();
