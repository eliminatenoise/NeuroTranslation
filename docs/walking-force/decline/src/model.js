/* Browser inference for the published relative-muscle checkpoints.
   The dense and attention calculations follow the project's Walking Force runtime.
   Each compact checkpoint has an input projection, one reused pre-normalized block and a readout. */
const DeclineForce = (() => {
  const CHANNELS = ['LBF', 'LTA', 'LRF', 'RBF', 'RTA', 'RRF'];
  const DEPTHS = [1, 3, 5, 7, 9];
  const SEEDS = [20261125, 20261126];
  const WIDTH = 32;
  const HEAD_WIDTH = 8;
  const BINS = 10;
  const ROWS_PER_BIN = 40;
  const f32 = Math.fround;
  const ERF_FACTORS = [1.061405429, -1.453152027, 1.421413741, -0.284496736, 0.254829592];

  function unpack(record) {
    if (!record) throw Error('The saved checkpoint is missing an array.');
    const bytes = Uint8Array.from(atob(record.data), ch => ch.charCodeAt(0));
    const step = record.dtype === 'f32' ? 4 : 8;
    const size = record.shape.reduce((count, width) => count * width, 1);
    if (!['f32', 'f64'].includes(record.dtype) || bytes.length !== size * step) {
      throw Error('The saved checkpoint contains an invalid array.');
    }
    const binary = new DataView(bytes.buffer);
    return record.dtype === 'f32'
      ? Float32Array.from({length: size}, (_, i) => binary.getFloat32(i * step, true))
      : Float64Array.from({length: size}, (_, i) => binary.getFloat64(i * step, true));
  }

  function csvRows(csv) {
    const lines = csv.trim().split(/\r?\n/);
    const fields = line => line.split(',').map(value => {
      const text = value.trim();
      return text[0] === '"' && text.at(-1) === '"' ? text.slice(1, -1).trim() : text;
    });
    if (fields(lines.shift()).join(',') !== CHANNELS.join(',')) {
      throw Error('Use the CSV header LBF,LTA,LRF,RBF,RTA,RRF in that order.');
    }
    if (lines.length !== BINS * ROWS_PER_BIN) {
      throw Error('Use exactly 400 rows of voltages after the header.');
    }
    const numeric = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i;
    return lines.map(line => {
      const values = fields(line);
      if (values.length !== CHANNELS.length || values.some(value => !numeric.test(value))) {
        throw Error('Enter a number for each of the six voltages on every row.');
      }
      return values.map(Number);
    });
  }

  function relativeHistory(volts) {
    if (volts.length !== BINS * ROWS_PER_BIN || volts.some(row =>
      row.length !== CHANNELS.length || row.some(value => !Number.isFinite(value)))) {
      throw Error('Use 400 rows of six finite voltages.');
    }
    const energies = Array.from({length: BINS}, (_, bin) => {
      const start = bin * ROWS_PER_BIN;
      const rows = volts.slice(start, start + ROWS_PER_BIN);
      return CHANNELS.map((_, channel) => {
        const origin = rows[0][channel];
        const shifted = rows.map(row => row[channel] - origin);
        const mean = shifted.reduce((total, value) => total + value, 0) / ROWS_PER_BIN;
        return shifted.reduce((total, value) => total + (value - mean) ** 2, 0) / ROWS_PER_BIN;
      });
    });
    return energies.slice(3).map((energy, offset) =>
      energy.map((value, channel) => {
        const count = offset + 3;
        const previous = energies.slice(0, count).reduce((sum, row) => sum + row[channel], 0);
        if (!(previous > 0) || !Number.isFinite(previous)) {
          throw Error('Each channel needs variation in its first three groups of voltages.');
        }
        const relative = f32(Math.log1p(Math.sqrt(value * count / previous)));
        if (!Number.isFinite(relative)) throw Error('The voltage is outside the supported numerical range.');
        return relative;
      }));
  }

  function gravityImpulse(mass, slope) {
    if (!Number.isFinite(mass) || mass <= 0) throw Error('Enter a positive body mass in kilograms.');
    if (!Number.isFinite(slope) || Math.abs(slope) >= 90) throw Error('Enter a slope between −90° and 90°.');
    return mass * 9.80665 * Math.cos(slope * Math.PI / 180) * .1;
  }

  function dense(input, weights, bias) {
    return bias.map((offset, output) => {
      const row = output * input.length;
      let sum = 0;
      for (let i = 0; i < input.length; i++) sum += input[i] * weights[row + i];
      return sum + offset;
    });
  }

  function normalize(input, weights, bias) {
    const mean = input.reduce((sum, value) => sum + value, 0) / input.length;
    const variance = input.reduce((sum, value) => sum + (value - mean) ** 2, 0) / input.length;
    const scale = 1 / Math.sqrt(variance + 1e-5);
    return input.map((value, i) => (value - mean) * scale * weights[i] + bias[i]);
  }

  function add(a, b) {
    return a.map((value, i) => value + b[i]);
  }

  function attend(query, memory) {
    const result = new Float32Array(WIDTH);
    for (let first = 0; first < WIDTH; first += HEAD_WIDTH) {
      const last = first + HEAD_WIDTH;
      const scores = memory.map(qkv => {
        let score = 0;
        for (let i = first; i < last; i++) score += query[i] * qkv[WIDTH + i];
        return score / Math.sqrt(HEAD_WIDTH);
      });
      const top = Math.max(...scores);
      const weights = scores.map(score => Math.exp(score - top));
      const weightSum = weights.reduce((sum, weight) => sum + weight, 0);
      for (let channel = first; channel < last; channel++) {
        let sum = 0;
        memory.forEach((qkv, bin) => { sum += (weights[bin] / weightSum) * qkv[2 * WIDTH + channel]; });
        result[channel] = sum;
      }
    }
    return result;
  }

  function gelu(value) {
    // Abramowitz and Stegun 7.1.26, max absolute error 1.5e-7 for erf.
    const x = Math.abs(value) / Math.SQRT2;
    const inverse = 1 / (1 + 0.3275911 * x);
    const polynomial = ERF_FACTORS.reduce((sum, factor) => sum * inverse + factor, 0) * inverse;
    const erf = Math.sign(value) * (1 - polynomial * Math.exp(-x * x));
    return .5 * value * (1 + erf);
  }

  function compact(rows, depth, read) {
    const affine = (x, key) => dense(x, read(key + '.weight'), read(key + '.bias'));
    const norm = (x, key) => normalize(x, read(key + '.weight'), read(key + '.bias'));
    const center = read('center');
    const scale = read('scale');
    const positions = read('positions');
    const qkvWeight = read('block.self_attn.in_proj_weight');
    const qkvBias = read('block.self_attn.in_proj_bias');
    const tokens = Array.from({length: BINS}, (_, bin) => {
      const input = new Float32Array(12);
      if (bin >= 3) {
        rows[bin - 3].forEach((value, c) => { input[c] = (value - center[c]) / scale[c]; });
        input.fill(1, CHANNELS.length);
      }
      return add(affine(input, 'project'), positions.subarray(bin * WIDTH, (bin + 1) * WIDTH));
    });
    let state = tokens;
    for (let pass = 0; pass < depth; pass++) {
      const qkv = state.map(row => dense(norm(row, 'block.norm1'), qkvWeight, qkvBias));
      state = state.map((row, time) => {
        const first = add(row, affine(attend(qkv[time], qkv), 'block.self_attn.out_proj'));
        const widened = affine(norm(first, 'block.norm2'), 'block.linear1').map(gelu);
        return add(first, affine(widened, 'block.linear2'));
      });
    }
    const output = affine(norm(state.at(-1), 'readout.0'), 'readout.1');
    const unit = read('unit')[0];
    const location = read('location');
    return Array.from(output, (value, i) => value * unit + location[i]);
  }

  function linear(rows, read, slopeKey) {
    const coefficients = read(slopeKey);
    const center = read('center');
    const scale = read('scale');
    const result = [0, 0];
    rows.flat().forEach((value, index) => {
      const standardized = (value - center[index]) / scale[index];
      result[0] += coefficients[2 * index] * standardized;
      result[1] += coefficients[2 * index + 1] * standardized;
    });
    const intercept = read('intercept');
    return add(result, intercept);
  }

  function create(payload) {
    const decoded = new Map();
    function weights(prefix) {
      return name => {
        const key = prefix + name;
        if (!decoded.has(key)) decoded.set(key, unpack(payload.tensors[key]));
        return decoded.get(key);
      };
    }
    function predict(relative, depth, context = null) {
      if (!DEPTHS.includes(depth)) throw Error('Choose 1, 3, 5, 7 or 9 passes.');
      if (relative.length !== 7 || relative.some(row => row.length !== CHANNELS.length ||
        row.some(value => !Number.isFinite(f32(value))))) throw Error('The muscle history must contain seven groups of six readings.');
      const rows = relative.map(row => row.map(f32));
      const known = context !== null;
      const condition = known ? 'known_mass' : 'muscle';
      const scale = known ? gravityImpulse(context.mass, context.slope) : 1;
      const reference = known ? scale : weights('linear.muscle.')('fixed_total')[0];
      const seeds = SEEDS.map(seed =>
        compact(rows, depth, weights(`compact.${condition}.p${depth}.${seed}.`)));
      const attention = seeds[0].map((value, plate) => (value + seeds[1][plate]) * .5 * scale);
      const straight = linear(rows, weights(`linear.${condition}.`), 'slope').map(value => value * scale);
      const headCondition = known ? 'given_body_mass_and_slope' : 'muscle_only';
      const head = weights(`research.${headCondition}.`);
      if (head('blend_research_share')[0] !== 0) throw Error('This blend needs a separate Research Edition model state.');
      const muscle = linear(rows, weights(`research.${headCondition}.relative_muscle.`), 'coefficient').map(value => value * scale);
      if (![reference, ...attention, ...straight, ...muscle].every(Number.isFinite)) {
        throw Error('The readings produced a value outside the model’s numerical range.');
      }
      return {reference, attention, linear: straight, relativeMuscle: muscle, lateBlend: muscle};
    }
    return {predict};
  }

  return {create, csvRows, relativeHistory, channels: CHANNELS, depths: DEPTHS};
})();
if (typeof module === 'object') module.exports = DeclineForce;
