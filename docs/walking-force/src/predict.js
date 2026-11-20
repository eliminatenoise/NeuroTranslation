/* Pure offline inference. Dense-layer matrices are stored as [output][input]. */
const WalkingForce = (() => {
  function dot(a, b) {
    let sum = 0;
    for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
    return sum;
  }
  function dense(x, weight, bias) { return weight.map((row, i) => dot(row, x) + bias[i]); }
  function add(a, b) { return a.map((n,i) => n + b[i]); }
  function norm(x, weight, bias) {
    const mean = x.reduce((total, n) => total + n, 0) / x.length;
    let variance = 0;
    for (const n of x) variance += (n - mean) ** 2;
    const scale = 1 / Math.sqrt(variance / x.length + 1e-5);
    return x.map((v,i) => (v - mean) * scale * weight[i] + bias[i]);
  }
  function attention(query, key, value, heads) {
    const width = query[0].length / heads;
    return query.map(q => {
      const joined = [];
      for (let h = 0; h < heads; h++) {
        const lo = h * width;
        const scores = key.map(k => {
          let sum = 0;
          for (let d = lo; d < lo + width; d++) sum += q[d] * k[d];
          return sum / Math.sqrt(width);
        });
        const max = Math.max(...scores);
        const exp = scores.map(s => Math.exp(s - max));
        const total = exp.reduce((a,b) => a+b);
        for (let d = lo; d < lo + width; d++) {
          let sum = 0;
          for (let t = 0; t < value.length; t++) sum += exp[t] / total * value[t][d];
          joined.push(sum);
        }
      }
      return joined;
    });
  }
  function normalized(rows, weights) {
    if (!Array.isArray(rows) || rows.length !== 8) throw Error('Expected eight time bins.');
    return rows.map(row => {
      if (!Array.isArray(row) || row.length !== 40) throw Error('Expected forty values per time bin.');
      const flags = [...row.slice(18, 24),...row.slice(32, 40)];
      if (flags.some(n => n !== 0 && n !== 1)) throw Error('Availability flags must be 0 or 1.');
      return row.map((n,c) => {
        if ((c >= 18 && c < 24) || c >= 32) return n;
        const flag = c < 18 ? 18 + Math.floor(c/3) : c + 8;
        if (!row[flag]) return 0;
        if (!Number.isFinite(n)) throw Error('An available signal must have a finite value.');
        return Math.max(-8, Math.min(8, (n-weights.center[c])/weights.scale[c]));
      });
    });
  }
  function transformer(tokens, w) {
    const affine = (x,name) => dense(x,w[name+'.weight'],w[name+'.bias']);
    const ln = (x,name) => norm(x,w[name+'.weight'],w[name+'.bias']);
    const input = tokens.map((row,t) => add(affine(row, 'embed'),w.pos[t]));
    const qkv = input.map(row => affine(ln(row, 'n1'), 'qkv'));
    const hidden = input[0].length;
    const context = attention([qkv[qkv.length-1].slice(0,hidden)],qkv.map(v => v.slice(hidden,2*hidden)),
      qkv.map(v => v.slice(2*hidden)),3);
    // Each feed-forward block acts on its own token. Only the final one reaches the readout.
    const t = input.length-1;
    const residual = add(input[t],affine(context[0], 'out'));
    const activated = affine(ln(residual, 'n2'), 'ff1').map(v => Math.max(v,0));
    const last = ln(add(residual,affine(activated, 'ff2')), 'n3');
    return affine(last, 'head')[0];
  }
  function predict(rows, weights, method, modality) {
    const xs = normalized(rows, weights);
    const selected = xs.map(row => modality === 'markers' ? row.slice(0,24)
      : modality === 'emg' ? row.slice(24) : row);
    if (!['combined','emg','markers'].includes(modality)) throw Error('Unknown input set.');
    let y;
    if (method === 'ridge') {
      const w = weights.ridge[modality];
      y = dot(selected.flat(),w.coef) + w.bias;
    } else if (method === 'transformer') {
      y = transformer(selected, weights.transformer[modality]);
    } else throw Error('Unknown model.');
    return Math.max(0, y * 500);
  }
  return {normalized, predict};
})();
if (typeof module === 'object') module.exports = WalkingForce;
