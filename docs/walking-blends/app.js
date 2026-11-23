"use strict";
const input = document.querySelector("#forecasts");
const output = document.querySelector("#result");
const notice = document.querySelector("#status");
const example = document.querySelector("#example");
function calculate() {
  output.textContent = "";
  try {
    const pair = JSON.parse(input.value);
    const result = WalkingBlend.project(pair);
    output.textContent = JSON.stringify(result, null, 2);
    notice.textContent = (pair.learned_model === "compact" ? "Compact" : "Research Edition") + " forecast calculated.";
  } catch (e) { notice.textContent = "Input error. " + e.message; }
}
function loadExample() {
  input.value = JSON.stringify(WalkingBlendExamples[example.value], null, 2);
  calculate();
}
document.querySelector("#restore").addEventListener("click", loadExample);
document.querySelector("#run").addEventListener("click", calculate);
input.addEventListener("input", () => {output.textContent = ""; notice.textContent = "Input changed. Calculate to see the result.";});
loadExample();
