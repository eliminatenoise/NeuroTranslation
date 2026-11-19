"use strict";

(() => {
  // All four designs are nested prefixes. Standardize and form their shared
  // cross-products once, then solve each distinct penalized system.
  function fitRidge({ values, deltas, width }, arms) {
    const count = deltas.length;
    const center = new Float64Array(width);
    const scale = new Float64Array(width);
    const varies = new Uint8Array(width);
    let intercept = 0;

    for (let row = 0; row < count; row++) {
      intercept += deltas[row];
      const start = row * width;
      for (let col = 0; col < width; col++) {
        const value = values[start + col];
        center[col] += value;
        if (value !== values[col]) varies[col] = 1;
      }
    }
    intercept /= count;
    for (let col = 0; col < width; col++) center[col] /= count;

    for (let start = 0; start < values.length; start += width) {
      for (let col = 0; col < width; col++) {
        const distance = values[start + col] - center[col];
        scale[col] += distance * distance;
      }
    }
    for (let col = 0; col < width; col++) {
      scale[col] = varies[col] ? Math.sqrt(scale[col] / count) : 1;
    }

    const cross = new Float64Array(width * width);
    const outcome = new Float64Array(width);
    const standardized = new Float64Array(width);
    for (let row = 0; row < count; row++) {
      const response = deltas[row] - intercept;
      const start = row * width;
      for (let col = 0; col < width; col++) {
        const value = (values[start + col] - center[col]) / scale[col];
        standardized[col] = value;
        outcome[col] += value * response;
        const offset = col * width;
        for (let inner = 0; inner <= col; inner++) {
          cross[offset + inner] += value * standardized[inner];
        }
      }
    }

    function solve(size) {
      // Cholesky factorization. A positive ridge penalty makes the matrix
      // positive definite, including when the original columns are collinear.
      const factor = new Float64Array(size * size);
      for (let row = 0; row < size; row++) {
        for (let col = 0; col <= row; col++) {
          let sum = cross[row * width + col] / count;
          for (let t = 0; t < col; t++) sum -= factor[row * size + t] * factor[col * size + t];
          const value = row === col ? Math.sqrt(sum + 0.01) : sum / factor[col * size + col];
          if (!Number.isFinite(value)) throw Error("The training readings exceed the numerical range of this fit.");
          factor[row * size + col] = value;
        }
      }

      const coefficients = new Array(size);
      for (let row = 0; row < size; row++) {
        let rhs = outcome[row] / count;
        for (let col = 0; col < row; col++) rhs -= factor[row * size + col] * coefficients[col];
        coefficients[row] = rhs / factor[row * size + row];
      }
      for (let row = size - 1; row >= 0; row--) {
        let rhs = coefficients[row];
        for (let col = row + 1; col < size; col++) rhs -= factor[col * size + row] * coefficients[col];
        coefficients[row] = rhs / factor[row * size + row];
      }
      return coefficients;
    }

    return Object.fromEntries(arms.map(([name, keys]) => [name, {
      feature_names: keys,
      center: Array.from(center.subarray(0, keys.length)),
      scale: Array.from(scale.subarray(0, keys.length)),
      intercept,
      coef: solve(keys.length),
      add_force_now: true,
    }]));
  }

  function solveInWorker(design, arms, signal) {
    signal.throwIfAborted();
    // The exact same CPU kernel runs from HTTPS and file://, with no fetch or
    // cross-thread copy of the design. Only trusted application code is embedded.
    const source = new Blob([`const fitRidge = ${fitRidge.toString()};
      self.onmessage = ({data}) => {
        try {
          const start = performance.now();
          const models = fitRidge(data.design, data.arms);
          self.postMessage({models, computeMs: performance.now() - start});
        } catch (error) {
          self.postMessage({error: error.message});
        }
      };`], { type: "application/javascript" });
    const url = URL.createObjectURL(source);
    let worker;
    let abort;
    const start = performance.now();
    return new Promise((resolve, reject) => {
      worker = new Worker(url);
      abort = () => reject(signal.reason);
      signal.addEventListener("abort", abort, { once: true });
      worker.onmessage = ({ data }) => {
        if (data.error) reject(Error(data.error));
        else resolve({ models: data.models, computeMs: data.computeMs, totalMs: performance.now() - start });
      };
      worker.onerror = () => reject(Error("The fitting worker could not run in this browser."));
      worker.onmessageerror = () => reject(Error("The browser could not return the fitted weights."));
      worker.postMessage({ design, arms }, [design.values.buffer, design.deltas.buffer]);
    }).finally(() => {
      if (abort) signal.removeEventListener("abort", abort);
      worker?.terminate();
      URL.revokeObjectURL(url);
    });
  }

  globalThis.CemhseyRidge = { fitRidge, solveInWorker };
})();
