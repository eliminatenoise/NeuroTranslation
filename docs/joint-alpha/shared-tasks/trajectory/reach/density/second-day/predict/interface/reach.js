// SPDX-License-Identifier: CC0-1.0
(() => {
  "use strict";

  const columns = ["hand_x", "hand_y", "hand_z", "elbow_x", "elbow_y", "elbow_z", "handle_x", "handle_y"];
  const columnNames = ["hand X", "hand Y", "hand Z", "elbow X", "elbow Y", "elbow Z", "handle X", "handle Y"];
  const ahead = [20, 50, 70, 100];
  const draws = 32;
  const samplingSeed = 1117;
  const markers = ["Hand marker", "Elbow marker"];
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
  let forecast = null;
  let revision = 0;

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

  function stopShowingResult(message) {
    revision++;
    forecast = null;
    if (saveLink.hasAttribute("href")) {
      URL.revokeObjectURL(saveLink.href);
      saveLink.removeAttribute("href");
    }
    run.disabled = false;
    result.hidden = true;
    placeholder.hidden = false;
    placeholder.textContent = message;
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

  function showTables(container, values, method) {
    container.replaceChildren(...markers.map((marker, i) => {
      const table = makeTable(marker + " (mm)", values, i * 3);
      table.setAttribute("aria-label", marker + " displacement in millimetres, " + method);
      return table;
    }));
  }

  function selectedPath() {
    return pathMenu.value === "mean" ? forecast.meanMm : forecast.pathsMm[Number(pathMenu.value)];
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

  function drawPlot(canvas, marker, model, velocity, maximum) {
    const selected = pathMenu.selectedOptions[0].text;
    const description = ahead.map((time, i) =>
      `${time} ms, ${formatted(model[i + 1])} mm model and ${formatted(velocity[i + 1])} mm constant velocity`
    ).join(". ");
    canvas.setAttribute("aria-label", `${marker} distance from its last recorded position. ${selected}. ${description}.`);

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

    function line(values, isModel) {
      ctx.strokeStyle = ctx.fillStyle = color(isModel ? "model" : "velocity");
      ctx.lineWidth = isModel ? 2.5 : 2;
      ctx.setLineDash(isModel ? [] : [6, 4]);
      ctx.beginPath();
      values.forEach((distance, i) => {
        if (i === 0) ctx.moveTo(x(times[i]), y(distance));
        else ctx.lineTo(x(times[i]), y(distance));
      });
      ctx.stroke();
      ctx.setLineDash([]);
      for (let i = 1; i < values.length; i++) {
        const px = x(times[i]), py = y(values[i]);
        if (isModel) {
          ctx.beginPath();
          ctx.arc(px, py, 2.7, 0, 2 * Math.PI);
          ctx.fill();
        } else {
          ctx.strokeRect(px - 2.6, py - 2.6, 5.2, 5.2);
        }
      }
    }
    line(velocity, false);
    line(model, true);
  }

  function updatePlots() {
    if (!forecast) return;
    const path = selectedPath();
    const series = markers.map((marker, i) => ({
      marker,
      model: distanceSeries(path, i * 3),
      velocity: distanceSeries(forecast.velocity20Mm, i * 3)
    }));
    const maximum = axisMaximum(Math.max(...series.flatMap(item => [...item.model, ...item.velocity])));
    series.forEach((item, i) => drawPlot(canvases[i], item.marker, item.model, item.velocity, maximum));
  }

  function updateSelection() {
    showTables(get("model-tables"), selectedPath(), pathMenu.selectedOptions[0].text);
    updatePlots();
  }

  function linkForecastDownload() {
    const model = globalThis.ReachForecastModel;
    const output = {
      format: "NeuroTranslation reach forecast",
      version: 1,
      quantity: "Forecast displacement from each marker's last input position",
      units: {displacement: "mm", time: "ms"},
      axes: columns.slice(0, 6),
      timeAfterLastReadingMs: forecast.timesMs,
      model: {
        id: model.schema,
        fitSeed: model.fitSeed,
        weightsSha256: model.weightsSha256,
        normalizersSha256: model.normalizersSha256,
        samplingSeed,
        drawCount: forecast.pathsMm.length,
        pathsMm: forecast.pathsMm,
        meanMm: forecast.meanMm
      },
      constantVelocity: {historyWindowMs: 20, displacementMm: forecast.velocity20Mm}
    };
    const file = new Blob([JSON.stringify(output, null, 2), "\n"], {type: "application/json"});
    saveLink.href = URL.createObjectURL(file);
  }

  function runForecast(focusInvalid = false) {
    stopShowingResult("Calculating the marker paths…");
    let readings;
    try {
      readings = readHistory(history.value);
    } catch (error) {
      reportError(error.message, true, focusInvalid);
      return;
    }
    if (typeof globalThis.ReachForecast?.predict !== "function") {
      reportError("The model files could not open. Extract the whole preview together and reopen it.", false, false);
      return;
    }
    const ticket = revision;
    run.disabled = true;
    status.textContent = "Calculating 32 model paths…";
    setTimeout(() => {
      if (ticket !== revision) return;
      try {
        const prediction = globalThis.ReachForecast.predict(readings, {seed: samplingSeed, draws});
        if (prediction.velocity20Mm.some(row => row.some(value => !Number.isFinite(value)))) {
          throw new RangeError("The final velocity exceeds the numeric range.");
        }
        forecast = prediction;
      } catch (error) {
        if (error instanceof RangeError) {
          reportError("These readings exceed the fitted model’s numeric range. Check that each position uses millimetres.", true, focusInvalid);
        } else {
          reportError("The model could not return a forecast. Reopen the complete preview and run it again.", false, false);
        }
        return;
      }
      placeholder.hidden = true;
      result.hidden = false;
      showTables(get("velocity-tables"), forecast.velocity20Mm, "constant velocity");
      updateSelection();
      run.disabled = false;
      status.textContent = "Forecast ready for these 20 readings.";
      linkForecastDownload();
    }, 0);
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
  pathMenu.addEventListener("change", () => {
    if (!forecast) return;
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
