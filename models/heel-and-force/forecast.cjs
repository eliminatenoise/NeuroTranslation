const fs = require('node:fs');
const path = require('node:path');
const {predict} = require('./predict.js');

try {
  const [name = 'joint', file] = process.argv.slice(2);
  if (!['joint', 'heel', 'force', 'marker'].includes(name) || process.argv.length > 4) {
    throw new Error('Usage: node forecast.cjs [joint|heel|force|marker] [input.json]');
  }
  const model = JSON.parse(fs.readFileSync(path.join(__dirname, name + '-model.json'), 'utf8'));
  const input = JSON.parse(fs.readFileSync(file || path.join(__dirname, 'example.json'), 'utf8'));
  console.log(JSON.stringify(predict(model, input.input || input), null, 2));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
