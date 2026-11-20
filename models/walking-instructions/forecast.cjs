#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const {predict} = require("./predict.js");
try {
  const [file, instruction, fit, ...extras] = process.argv.slice(2);
  if (extras.length || (fit && fit !== "permuted")) throw Error("Usage: node forecast.cjs [window.json] [4|5|null|exact instruction] [permuted]");
  const bundle = JSON.parse(fs.readFileSync(path.join(__dirname,"weights.json"),"utf8"));
  const payload = JSON.parse(fs.readFileSync(file || path.join(__dirname,"example.json"),"utf8"));
  const input = {...(payload.input || payload)};
  if (instruction !== undefined) input.instruction = (["4","5","null"].includes(instruction) ? JSON.parse(instruction) : instruction);
  const future_delta_mm = predict(bundle,input,fit);
  process.stdout.write(JSON.stringify({landmarks:["pelvis","right heel"], axes:["forward","left","up"],future_delta_mm},null,2)+"\n");
} catch (err) {
  process.stderr.write(err.message+"\n");
  process.exitCode = 1;
}
