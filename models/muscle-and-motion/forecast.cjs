#!/usr/bin/env node
/* Offline command-line forecast. All arguments after the input are optional. */
const path = require("node:path");
const fs = require("node:fs");
const {predict} = require("./model.js");
const file = process.argv[2] || path.join(__dirname,"synthetic-event.json");
const mode = process.argv[3] || "joint";
try {
  const weights = JSON.parse(fs.readFileSync(path.join(__dirname,"weights.json")));
  const input = JSON.parse(fs.readFileSync(file));
  process.stdout.write(JSON.stringify(predict(weights,input,mode),null,2)+"\n");
} catch (error) {
  process.stderr.write(error.message+"\n");
  process.exitCode=1;
}
