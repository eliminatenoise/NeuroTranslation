(function (root) {
  "use strict";
  const models = typeof module === "object" && module.exports
    ? {compact: require("./compact.json"), research: require("./research.json")}
    : root.WalkingBlendCoefficients;
  const names = ["heel_mm", "impulse_ns", "new_load_probability"];
  function requireKeys(value, keys, path) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== keys.length || keys.some(key => !Object.hasOwn(value, key))) {
      throw new TypeError(path + " must contain exactly " + keys.join(", ") + ".");
    }
  }
  function vector(value, length, path) {
    if (!Array.isArray(value) || value.length !== length) throw new TypeError(path + " must have " + length + " entries.");
    for (let i = 0; i < length; i++) if (!Object.hasOwn(value, i)) throw new TypeError(path + " contains an empty slot.");
  }
  function number(value, probability, path) {
    if (!Number.isFinite(value)) throw new TypeError(path + " must be a finite number.");
    if (probability && (value < 0 || value > 1)) throw new RangeError(path + " must be between 0 and 1.");
  }
  function forecast(value, path) {
    requireKeys(value, names, path);
    for (const name of names) {
      const side = value[name];
      vector(side, 2, path + "." + name);
      for (let i = 0; i < 2; i++) {
        const label = path + "." + name + "[" + i + "]";
        if (name === "heel_mm") {
          vector(side[i], 3, label);
          for (let axis = 0; axis < 3; axis++) number(side[i][axis], false, label + "[" + axis + "]");
        } else number(side[i], name === "new_load_probability", label);
      }
    }
  }
  function project(input) {
    requireKeys(input, ["learned_model", "physical", "learned"], "Input");
    if (typeof input.learned_model !== "string" || !Object.hasOwn(models, input.learned_model)) {
      throw new RangeError("learned_model must be compact or research.");
    }
    forecast(input.physical, "physical"); forecast(input.learned, "learned");
    const weights = models[input.learned_model].learned_fraction;
    function mix(a,b,w) {
      const v = a + w * (b - a);
      if (!Number.isFinite(v)) throw new RangeError("The projection exceeds the finite Float64 range.");
      return v;
    }
    const result = {};
    for (const name of names) {
      result[name] = input.physical[name].map((v,i) => name === "heel_mm"
        ? v.map((a,j) => mix(a,input.learned[name][i][j],weights[name]))
        : mix(v,input.learned[name][i],weights[name]));
    }
    return result;
  }
  if (typeof module === "object" && module.exports) module.exports = Object.freeze({project});
  else root.WalkingBlend = Object.freeze({project});
}(globalThis));
