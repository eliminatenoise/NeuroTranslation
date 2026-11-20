#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
require('./weights.js');
require('./model.js');
require('./experiment.js');
const methods = ['joint','specialists','repeat','stationary','velocity16','velocity32'];
try {
  const [file,method='joint'] = process.argv.slice(2);
  if (!file || !methods.includes(method)) throw Error('Usage: node predict.cjs input.json [' + methods.join('|') + ']');
  const input = MuscleMotionExperiment.validate(JSON.parse(fs.readFileSync(file,'utf8')));
  const result = ['joint','specialists'].includes(method) ? MuscleMotion.predict(MuscleMotionWeights,input,method) : MuscleMotionExperiment.reference(input,method);
  if (!MuscleMotionExperiment.validOutput(result)) throw Error('The input produced a nonfinite forecast.');
  process.stdout.write(JSON.stringify(result) + '\n');
} catch(e) {
  process.stderr.write(e.message + '\n');
  process.exitCode=1;
}
