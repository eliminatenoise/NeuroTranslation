#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const {predict} = require('./src/knee-moment.js');
const example = require('./src/example.js');
const weights = require('./src/weights.json');

try {
  const args = process.argv.slice(2);
  if (args.length > 1) throw Error('Usage: node predict.cjs [record.json | - | --example-input]');
  if (args[0] === '--example-input') console.log(JSON.stringify(example()));
  else {
    const record = args.length ? JSON.parse(fs.readFileSync(args[0] === '-' ? 0 : args[0], 'utf8')) : example();
    console.log(JSON.stringify(predict(record, weights)));
  }
} catch (error) { console.error(error.message); process.exitCode = 1; }
