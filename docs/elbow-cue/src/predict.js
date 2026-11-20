/* Signed change in the stored elbow-sensor units. No display or network dependency. */
const ElbowPredict = (() => {
  const modes = ["persistence", "cue_median", "cue_mechanics", "cue_mechanics_c3", "cue_mechanics_eog", "temporal_attention"];
  const names = {
    persistence: "No change", cue_median: "Cue alone", cue_mechanics: "Cue + elbow history",
    cue_mechanics_c3: "Cue + elbow + scalp", cue_mechanics_eog: "Cue + elbow + eyes",
    temporal_attention: "Cue + elbow + scalp attention", shifted_c3: "Scalp from another trial"
  };
  function attention(signal, scale) {
    const tokens = signal.map(value => Math.min(4, Math.max(-4, (value - signal[0]) / scale)));
    const logits = tokens.map((value, i) => value * tokens[3] + (i - 3) / 4);
    const peak = Math.max(...logits);
    const weights = logits.map(value => Math.exp(value - peak));
    return tokens.reduce((sum, token, i) => sum + token * weights[i], 0) / weights.reduce((a,b) => a+b, 0);
  }
  function forecast(models, mode, input) {
    if (!modes.includes(mode) || !["flexion", "extension"].includes(input.cue)) throw Error("Unknown model or cue");
    const model = models[mode];
    if (mode === "persistence") return model.value;
    if (mode === "cue_median") return model.by_cue[input.cue];
    const m = input.elbow_medians;
    const x = [Number(input.cue === "extension"), m[3], m[3]-m[2], m[2]-m[1], m[1]-m[0]];
    if (mode === "temporal_attention") x.push(attention(input.c3_means, model.token_scale));
    if (mode === "cue_mechanics_c3" || mode === "cue_mechanics_eog") {
      const signal = mode === "cue_mechanics_eog" ? input.eog_means : input.c3_means;
      x.push(signal[1]-signal[0], signal[2]-signal[0], signal[3]-signal[0]);
    }
    if (model.weights.length !== x.length) throw Error("Model feature count mismatch");
    return x.reduce((sum,value,i) => sum + (value - model.means[i]) / model.scales[i] * model.weights[i], model.intercept);
  }
  return { forecast, names, modes };
})();
if (typeof module !== "undefined" && module.exports) module.exports = ElbowPredict;
