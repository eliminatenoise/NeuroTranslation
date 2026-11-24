import { readFileSync } from "node:fs";
import { forecastBothFeet, forecastFoot } from "./pressure.mjs";

try {
  const weights = JSON.parse(readFileSync(new URL("pressure-model.json", import.meta.url), "utf8"));
  const source = process.argv[2] ?? new URL("example.json", import.meta.url);
  const input = JSON.parse(readFileSync(source, "utf8"));
  const values = input.side === "both"
    ? forecastBothFeet(input.history, weights)
    : forecastFoot(input.history, input.side, weights);
  if (!values.every(Number.isFinite)) throw new Error("Pressure history is outside the numeric range.");
  console.log(JSON.stringify({
    side: input.side,
    units: weights.units,
    forecastMs: weights.forecastMs,
    sensorOrderPerFoot: weights.sensorOrderPerFoot,
    pressure: values,
  }, null, 2));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
