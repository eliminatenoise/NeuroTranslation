// SPDX-License-Identifier: CC0-1.0
"use strict";
const data = JSON.parse(document.getElementById("study").textContent);
const fingers = ["Thumb", "Index", "Middle", "Ring", "Little"];
const times = [-120, -80, -40, 0];

function inventedGlove(pattern) {
  if (pattern === "mixed") return data.glove;
  const starts = data.glove[0];
  const slopes = pattern === "steady" ? [0, 0, 0, 0, 0] : [7, 14, 21, 16, 8];
  return times.map((_, t) => starts.map((base, f) => base + slopes[f] * t));
}

function cueAt(finger, time) {
  // The screen shows this finger, 920 ms into the active phase at cutoff.
  const seconds = (data.age + time) / 1000;
  const features = new Array(60).fill(0);
  const offset = finger * 6;
  features[offset] = 1;
  features[offset + 1] = seconds;
  [0.4, 0.8, 1.2, 1.6].forEach((k, i) => {
    features[offset + 2 + i] = Math.max(0, seconds - k);
  });
  return features;
}

function ridge(tokens, weights, last) {
  const forecast = weights.intercept.map((v, f) => v + last[f]);
  let p = 0;
  for (const token of tokens) {
    for (const value of token) {
      const standardized = (value - weights.mean[p]) / weights.sd[p];
      for (let f = 0; f < forecast.length; f++) {
        forecast[f] += standardized * weights.weights[p][f];
      }
      p++;
    }
  }
  return forecast;
}

function predict(finger, pattern, power) {
  const glove = inventedGlove(pattern);
  const common = glove.map((row, t) => [...row, ...cueAt(finger, times[t])]);
  // The stored powers come exclusively from the invented waveform fixture.
  const full = common.map((row, t) => [
    ...row, ...data.powers[t].map(v => Math.log1p(power * v))
  ]);
  const hold = glove[3];
  return {
    glove, hold,
    cue: ridge(common, data.motion_cue, hold),
    brain: ridge(full, data.aligned, hold)
  };
}
