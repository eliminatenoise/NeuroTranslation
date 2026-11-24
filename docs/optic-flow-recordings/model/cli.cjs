/* Run the same local inference core as the browser. */
"use strict";

const fs = require("node:fs");
const engine = require("./runtime.js");

try {
  const source = process.argv[2];
  if (!source || process.argv.length !== 3) throw new Error("Use node cli.cjs example-input.json, or use - to read JSON from stdin.");
  const input = JSON.parse(fs.readFileSync(source === "-" ? 0 : source, "utf8"));
  const result = Array.isArray(input) ? engine.predictCases(input) : engine.predict(input);
  process.stdout.write(JSON.stringify(result, null, 2) + "\n");
} catch (error) {
  process.stderr.write(error.message + "\n");
  process.exitCode = 1;
}
