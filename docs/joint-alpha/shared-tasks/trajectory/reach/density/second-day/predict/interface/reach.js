// SPDX-License-Identifier: CC0-1.0
(() => {
  "use strict";

  const columns = ["hand_x", "hand_y", "hand_z", "elbow_x", "elbow_y", "elbow_z", "handle_x", "handle_y"];
  const columnNames = ["hand X", "hand Y", "hand Z", "elbow X", "elbow Y", "elbow Z", "handle X", "handle Y"];
  const ahead = [20, 50, 70, 100];
  const draws = 32;
  const samplingSeed = 1117;
  const markers = ["Hand marker", "Elbow marker"];
  const labels = {absolute: "Recorded positions", relative: "Relative positions", velocity: "Constant velocity"};
  const colors = {absolute: "model", relative: "relative", velocity: "velocity"};
  const dashes = {absolute: [], relative: [2, 4], velocity: [7, 4]};
  const modes = document.querySelectorAll('input[name="model-mode"]');
  const get = id => document.getElementById(id);
  const history = get("history");
  const fileInput = get("file");
  const pathMenu = get("path");
  const run = get("run");
  const sourceName = get("source-name");
  const status = get("status");
  const inputError = get("input-error");
  const result = get("result");
  const saveLink = get("save-forecast");
  const placeholder = get("empty-result");
  const canvases = [get("hand-plot"), get("elbow-plot")];
  const space = globalThis.createReachSpace?.();
  let current = null;
  let revision = 0;

  function mode() {
    return document.querySelector('input[name="model-mode"]:checked').value;
  }

  function modelKeys(view = mode()) {
    return view === "comparison" ? ["absolute", "relative"] : [view];
  }

  function fields(line) {
    return line.split(",").map(cell => {
      const text = cell.trim();
      return text.startsWith('"') && text.endsWith('"') ? text.slice(1, -1).trim() : text;
    });
  }

  function readHistory(text) {
    const clean = text.trim();
    if (!clean) throw new Error("Enter 20 rows of readings or restore the recorded example.");
    const lines = clean.split(/\r\n|[\r\n]/);
    const first = fields(lines[0]).map(item => item.toLowerCase());
    if (first.length === columns.length && first.every((value, i) => value === columns[i])) {
      lines.shift();
    } else if (first.some(value => /^(?:hand|elbow|handle)[ _]/.test(value))) {
      throw new Error("The header must put hand X, Y, Z first, then elbow X, Y, Z and handle X, Y. See Column order and units.");
    }
    if (lines.length !== 20) {
      throw new Error(`Expected 20 rows of readings. Found ${lines.length}. Each row should hold one reading.`);
    }
    return lines.map((line, rowIndex) => {
      const row = fields(line);
      if (row.length !== columns.length) {
        const unit = row.length === 1 ? "field" : "fields";
        throw new Error(`Row ${rowIndex + 1} has ${row.length} ${unit}. Enter eight comma-separated positions.`);
      }
      return row.map((value, columnIndex) => {
        const number = Number(value);
        if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value) || !Number.isFinite(number)) {
          throw new Error(`In row ${rowIndex + 1}, ${columnNames[columnIndex]} needs a finite decimal number in millimetres.`);
        }
        if (!Number.isFinite(Math.fround(number))) {
          throw new Error(`In row ${rowIndex + 1}, ${columnNames[columnIndex]} exceeds the model’s numeric range. Check the units.`);
        }
        return number;
      });
    });
  }

  function hideResult(message) {
    space?.clear();
    if (saveLink.hasAttribute("href")) {
      URL.revokeObjectURL(saveLink.href);
      saveLink.removeAttribute("href");
    }
    get("model-tables").replaceChildren();
    get("velocity-tables").replaceChildren();
    get("comparison-gap").textContent = "";
    get("comparison-gap").hidden = true;
    canvases.forEach((canvas, i) => {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.save();
        ctx.resetTransform();
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.restore();
      }
      canvas.setAttribute("aria-label", markers[i] + " distance forecast");
    });
    result.hidden = true;
    placeholder.hidden = false;
    placeholder.textContent = message;
  }

  function stopShowingResult(message) {
    revision++;
    current = null;
    hideResult(message);
    run.disabled = false;
    inputError.textContent = "";
    history.removeAttribute("aria-invalid");
    status.textContent = "";
  }

  function reportError(message, invalidInput, focusInput) {
    inputError.textContent = message;
    status.textContent = "";
    run.disabled = false;
    if (invalidInput) {
      history.setAttribute("aria-invalid", "true");
      if (focusInput) history.focus();
    }
    placeholder.textContent = "A forecast will appear here once the readings can be processed.";
  }

  function formatted(value) {
    if (Math.abs(value) < .005) return "0.00";
    return Math.abs(value) >= 100000 ? value.toExponential(2) : value.toFixed(2);
  }

  function makeTable(label, values, offset) {
    const table = document.createElement("table");
    table.createCaption().textContent = label;
    const head = table.createTHead().insertRow();
    for (const name of ["Ahead (ms)", "X", "Y", "Z"]) {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = name;
      head.append(cell);
    }
    const body = table.createTBody();
    ahead.forEach((time, i) => {
      const row = body.insertRow();
      const heading = document.createElement("th");
      heading.scope = "row";
      heading.textContent = String(time);
      row.append(heading);
      for (let j = offset; j < offset + 3; j++) {
        row.insertCell().textContent = formatted(values[i][j]);
      }
    });
    return table;
  }

  function markerTables(values, method, modelLabel = "") {
    return markers.map((marker, i) => {
      const title = modelLabel ? marker + " · " + modelLabel : marker;
      const table = makeTable(title + " (mm)", values, i * 3);
      table.setAttribute("aria-label", marker + " displacement in millimetres, " + method);
      return table;
    });
  }

  function selectedPath(key) {
    const prediction = current.predictions[key];
    return pathMenu.value === "mean" ? prediction.meanMm : prediction.pathsMm[Number(pathMenu.value)];
  }

  function distanceSeries(path, offset) {
    return [0, ...path.map(row => Math.hypot(row[offset], row[offset + 1], row[offset + 2]))];
  }

  function axisMaximum(maximum) {
    if (maximum === 0) return 1;
    const power = 10 ** Math.floor(Math.log10(maximum));
    const multiple = [1, 2, 3, 5, 10].find(step => step * power >= maximum);
    return multiple ? multiple * power : maximum;
  }

  function tickLabel(value) {
    if (value === 0) return "0";
    if (value >= 10000 || value < .001) return value.toExponential(0);
    return String(Number(value.toPrecision(3)));
  }

  function drawPlot(canvas, marker, lines, maximum) {
    const selected = pathMenu.selectedOptions[0].text;
    const description = ahead.map((time, i) => {
      const distances = Object.entries(lines).map(([key, values]) =>
        labels[key] + " " + formatted(values[i + 1]) + " mm"
      );
      return time + " ms, " + distances.join(", ");
    }).join(". ");
    canvas.setAttribute("aria-label", marker + " distance from its last input position. " + selected + ". " + description + ".");

    const ctx = canvas.getContext("2d");
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!ctx || !width || !height) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    ctx.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);

    const style = getComputedStyle(canvas);
    const color = name => style.getPropertyValue("--chart-" + name).trim();
    ctx.font = "12px system-ui, sans-serif";
    const left = Math.max(25, ctx.measureText(tickLabel(maximum)).width + 9);
    const right = width - 15;
    const top = 13;
    const bottom = height - 23;
    const times = [0, ...ahead];
    const x = t => left + (right - left) * t / 100;
    const y = d => bottom - (bottom - top) * (d / maximum);
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (const value of [0, maximum / 2, maximum]) {
      ctx.strokeStyle = color("grid");
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, y(value));
      ctx.lineTo(right, y(value));
      ctx.stroke();
      ctx.fillStyle = color("label");
      ctx.fillText(tickLabel(value), left - 5, y(value));
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const time of times) ctx.fillText(String(time), x(time), bottom + 5);

    function line(key, values) {
      ctx.strokeStyle = ctx.fillStyle = color(colors[key]);
      ctx.lineWidth = key === "velocity" ? 2 : 2.5;
      ctx.setLineDash(dashes[key]);
      ctx.beginPath();
      values.forEach((distance, i) => {
        if (i === 0) ctx.moveTo(x(times[i]), y(distance));
        else ctx.lineTo(x(times[i]), y(distance));
      });
      ctx.stroke();
      ctx.setLineDash([]);
      for (let i = 1; i < values.length; i++) {
        const px = x(times[i]), py = y(values[i]);
        if (key === "velocity") {
          ctx.strokeRect(px - 2.7, py - 2.7, 5.4, 5.4);
        } else if (key === "relative") {
          ctx.beginPath();
          ctx.moveTo(px, py - 3.5);
          ctx.lineTo(px - 3.5, py + 2.8);
          ctx.lineTo(px + 3.5, py + 2.8);
          ctx.closePath();
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.arc(px, py, 2.7, 0, 2 * Math.PI);
          ctx.fill();
        }
      }
    }
    for (const [key, values] of Object.entries(lines)) line(key, values);
  }

  function updatePlots() {
    if (!current || result.hidden) return;
    const keys = modelKeys();
    const velocity = current.predictions[keys[0]].velocity20Mm;
    const series = markers.map((_, i) => {
      const lines = {velocity: distanceSeries(velocity, i * 3)};
      for (const key of keys) lines[key] = distanceSeries(selectedPath(key), i * 3);
      return lines;
    });
    const maximum = axisMaximum(Math.max(...series.flatMap(lines => Object.values(lines).flat())));
    series.forEach((lines, i) => drawPlot(canvases[i], markers[i], lines, maximum));
  }

  function updateSelection() {
    const keys = modelKeys();
    const paired = keys.length === 2;
    const pathName = pathMenu.selectedOptions[0].text;
    if (space) {
      const paths = Object.fromEntries(keys.map(key => [key, selectedPath(key)]));
      paths.velocity = current.predictions[keys[0]].velocity20Mm;
      space.show(current.readings, paths, ahead, pathName);
    }
    const tables = keys.flatMap(key =>
      markerTables(selectedPath(key), labels[key] + ", " + pathName, paired ? labels[key] : "")
    );
    get("model-tables").replaceChildren(...tables);
    const gap = get("comparison-gap");
    if (paired) {
      const absolute = selectedPath("absolute").at(-1);
      const relative = selectedPath("relative").at(-1);
      const difference = absolute.map((value, i) => value - relative[i]);
      const hand = formatted(Math.hypot(...difference.slice(0, 3)));
      const elbow = formatted(Math.hypot(...difference.slice(3, 6)));
      gap.textContent = "At 100 ms, the two predicted hand positions are " + hand +
        " mm apart in 3D. The predicted elbow positions are " + elbow + " mm apart.";
    }
    gap.hidden = !paired;
    updatePlots();
  }

  function modelRecord(key) {
    const model = key === "absolute" ? globalThis.ReachForecastModel : globalThis.ReachForecastRelativeModel;
    const prediction = current.predictions[key];
    return {
      id: model.schema,
      fitSeed: model.fitSeed,
      weightsSha256: model.weightsSha256,
      normalizersSha256: model.normalizersSha256,
      samplingSeed,
      drawCount: prediction.pathsMm.length,
      pathsMm: prediction.pathsMm,
      meanMm: prediction.meanMm
    };
  }

  function linkForecastDownload(view, keys) {
    const prediction = current.predictions[keys[0]];
    const common = {
      format: "NeuroTranslation reach forecast",
      version: view === "absolute" ? 1 : 2,
      quantity: "Forecast displacement from each marker's last input position",
      units: {displacement: "mm", time: "ms"},
      axes: columns.slice(0, 6),
      timeAfterLastReadingMs: prediction.timesMs
    };
    const constantVelocity = {historyWindowMs: 20, displacementMm: prediction.velocity20Mm};
    let output;
    if (view === "absolute") {
      // Keep the published v1 record and filename byte-compatible.
      output = {...common, model: modelRecord("absolute"), constantVelocity};
      saveLink.download = "reach-forecast-v1.json";
      saveLink.textContent = "Save forecast";
      get("save-help").textContent = "The JSON file contains all 32 model paths, their mean and the constant-velocity forecast.";
    } else {
      const descriptions = {
        absolute: "The model reads the original recorded positions.",
        relative: "The model subtracts each coordinate's last reading from its 20 readings."
      };
      const models = Object.fromEntries(keys.map(key => [key, {
        historyRepresentation: key,
        historyTransform: descriptions[key],
        ...modelRecord(key)
      }]));
      output = {
        ...common,
        mode: view,
        expectedInputFrame: {
          markers: "Hand and elbow XYZ relative to the shoulder on the recording's axes.",
          handle: "Handle XY in the recording robot's coordinates.",
          positionUnits: "mm",
          readings: 20,
          intervalMs: 10,
          timeFromLastReadingMs: [-190, 0]
        },
        outputFrame: "Displacement along the recorded X, Y and Z axes from each marker's own last input position.",
        provenance: {
          engineContractVersion: 2,
          engineSha256: "48a4b2aea1896fdd6fb227190f76b9de42bbff7697a6052dbf28e1cbe375ef86",
          trainingDatasetDoi: "10.5061/dryad.nk98sf7q7",
          methodsDoi: "10.7554/eLife.48198",
          fittingRecording: "Macaque C, 7 September 2017"
        },
        models,
        constantVelocity
      };
      saveLink.download = "reach-forecast-" + view + "-v2.json";
      saveLink.textContent = view === "comparison" ? "Save both forecasts" : "Save relative forecast";
      get("save-help").textContent = view === "comparison"
        ? "The JSON file contains 32 paths and their mean for each model, plus the shared constant-velocity forecast."
        : "The JSON file contains all 32 relative-model paths, their mean and the constant-velocity forecast.";
    }
    const file = new Blob([JSON.stringify(output, null, 2), "\n"], {type: "application/json"});
    saveLink.href = URL.createObjectURL(file);
  }

  function showMode(focusInvalid = false) {
    if (!current) return;
    const ticket = ++revision;
    const view = mode();
    const keys = modelKeys(view);
    hideResult("Calculating the marker paths…");
    inputError.textContent = "";
    status.textContent = "";
    history.removeAttribute("aria-invalid");
    const engines = {
      absolute: globalThis.ReachForecasts?.absolute ?? globalThis.ReachForecast,
      relative: globalThis.ReachForecasts?.relative
    };
    if (keys.some(key => typeof engines[key]?.predict !== "function")) {
      reportError("The files for this model choice could not open. Extract the whole preview together and reopen it.", false, false);
      return;
    }
    run.disabled = true;
    status.textContent = view === "comparison" ? "Calculating 32 paths for each model…" : "Calculating 32 model paths…";
    function finish() {
      if (ticket !== revision) return;
      try {
        for (const key of keys) {
          if (current.predictions[key]) continue;
          const prediction = engines[key].predict(current.readings, {seed: samplingSeed, draws});
          if (prediction.velocity20Mm.some(row => row.some(value => !Number.isFinite(value)))) {
            throw new RangeError("The final velocity exceeds the numeric range.");
          }
          current.predictions[key] = prediction;
        }
        get("absolute-key").hidden = !keys.includes("absolute");
        get("relative-key").hidden = !keys.includes("relative");
        const velocity = current.predictions[keys[0]].velocity20Mm;
        get("velocity-tables").replaceChildren(...markerTables(velocity, "constant velocity"));
        linkForecastDownload(view, keys);
        placeholder.hidden = true;
        result.hidden = false;
        updateSelection();
        run.disabled = false;
        const messages = {
          absolute: "Forecast ready for these 20 readings.",
          relative: "Relative-position forecast ready for these 20 readings.",
          comparison: "Both forecasts are ready for the same 20 readings."
        };
        status.textContent = messages[view];
      } catch (error) {
        stopShowingResult("The model could not finish the forecast.");
        if (error instanceof RangeError) {
          reportError("These readings exceed the fitted model’s numeric range. Check that each position uses millimetres.", true, focusInvalid);
        } else {
          reportError("The model could not return a forecast. Reopen the complete preview and run it again.", false, false);
        }
      }
    }
    if (keys.every(key => current.predictions[key])) finish();
    else setTimeout(finish, 0);
  }

  function runForecast(focusInvalid = false) {
    try {
      current = {readings: readHistory(history.value), predictions: {}};
    } catch (error) {
      stopShowingResult("Check the movement readings.");
      reportError(error.message, true, focusInvalid);
      return;
    }
    showMode(focusInvalid);
  }

  function restoreExample() {
    const example = globalThis.ReachExample;
    fileInput.value = "";
    if (!Array.isArray(example?.rows)) {
      stopShowingResult("Enter readings to see a forecast.");
      reportError("The example could not open. Paste 20 rows or open a local CSV to run the model.", false, false);
      return;
    }
    history.value = [columns.join(","), ...example.rows.map(row => row.join(","))].join("\n");
    sourceName.textContent = example.label;
    pathMenu.value = "mean";
    runForecast();
  }

  pathMenu.add(new Option("Mean of 32 paths", "mean"));
  const samples = document.createElement("optgroup");
  samples.label = "Individual model paths";
  for (let i = 0; i < draws; i++) samples.append(new Option(`Path ${i + 1} of ${draws}`, String(i)));
  pathMenu.append(samples);

  get("input-form").addEventListener("submit", event => {
    event.preventDefault();
    runForecast(true);
  });
  get("restore").addEventListener("click", restoreExample);
  history.addEventListener("input", () => {
    stopShowingResult("The readings have changed. Run the forecast to update the plots and values.");
    sourceName.textContent = "Edited readings";
    fileInput.value = "";
  });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    stopShowingResult("Opening the local CSV…");
    const ticket = revision;
    run.disabled = true;
    status.textContent = "Opening the local CSV…";
    try {
      const text = await file.text();
      if (ticket !== revision) return;
      history.value = text;
      sourceName.textContent = "Local CSV · " + file.name;
      runForecast();
    } catch {
      if (ticket === revision) {
        fileInput.value = "";
        reportError("This file could not be read. Choose it again or paste its contents.", false, false);
      }
    }
  });
  modes.forEach(radio => radio.addEventListener("change", () => showMode()));
  pathMenu.addEventListener("change", () => {
    if (!current || result.hidden) return;
    updateSelection();
    status.textContent = "Showing " + pathMenu.selectedOptions[0].text.toLowerCase() + ".";
  });
  if (typeof ResizeObserver === "function") {
    const observer = new ResizeObserver(updatePlots);
    for (const canvas of canvases) observer.observe(canvas);
  } else {
    window.addEventListener("resize", updatePlots);
  }
  window.matchMedia("(forced-colors: active)").addEventListener("change", updatePlots);
  restoreExample();
})();
