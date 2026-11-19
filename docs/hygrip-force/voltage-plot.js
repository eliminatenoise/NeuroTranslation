"use strict";

(() => {
  const models = {
    force_history: "Force history",
    aligned: "Force history + EEG",
    timing: "Cue timing",
    persistence: "Last reading",
    backward_slope: "Recent slope",
  };
  const asVolts = (value) =>
    Math.abs(value) > 1e6 || (value !== 0 && Math.abs(value) < 1e-7)
      ? value.toExponential(5)
      : value.toFixed(7);

  function draw(canvas, data, model) {
    const width = canvas.clientWidth,
      height = canvas.clientHeight;
    if (!width || !height) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      canvas.hidden = true;
      return;
    }
    const scale = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    ctx.scale(canvas.width / width, canvas.height / height);
    ctx.font = "12px " + getComputedStyle(canvas).fontFamily;
    const prediction = data.predictions[model];
    const values = [...data.history, prediction];
    if (data.observed !== undefined) values.push(data.observed);
    // Normalize before subtracting so finite opposite-sign voltages cannot overflow the range.
    const peak = Math.max(...values.map(Math.abs)) || 1;
    let lo = Math.min(...values.map((v) => v / peak)),
      hi = Math.max(...values.map((v) => v / peak));
    if (hi === lo) {
      lo -= 0.01;
      hi += 0.01;
    }
    const ticks = [lo, (lo + hi) / 2, hi];
    const labels = ticks.map((v) => asVolts(v * peak));
    const left = Math.max(...labels.map((s) => ctx.measureText(s).width)) + 12;
    const right = width - 34,
      top = 29,
      bottom = height - 29;
    if (right <= left) return;
    const x = (ms) => left + ((ms + 380) / 500) * (right - left);
    const tickY = (n) =>
      bottom - 8 - ((n - lo) / (hi - lo)) * (bottom - top - 16);
    const y = (v) => tickY(v / peak);
    function line(x1, y1, x2, y2, color, dashes = []) {
      ctx.strokeStyle = color;
      ctx.setLineDash(dashes);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.fillStyle = "#e7edf7";
    ctx.fillRect(x(0), top, right - x(0) + 10, bottom - top);
    ctx.fillStyle = "#283d38";
    ctx.textBaseline = "middle";
    ctx.textAlign = "left";
    ctx.fillText("Sensor voltage (V)", 4, 13);
    for (const [i, v] of ticks.entries()) {
      line(left, tickY(v), right, tickY(v), "#c8d7d0");
      ctx.fillText(labels[i], 4, tickY(v));
    }
    line(x(0), top, x(0), bottom, "#5e706c", [3, 3]);
    ctx.textAlign = "center";
    const horizonLabel = "+120 ms";
    const wideLabelGap = (ctx.measureText("Cutoff").width + ctx.measureText(horizonLabel).width) / 2 + 6;
    const cutoffLabel = x(120) - x(0) >= wideLabelGap ? "Cutoff" : "0";
    const xTicks = right - left >= 125 ? [-380, -200, 0, 120] : [-380, 0, 120];
    for (const ms of xTicks) {
      const label = ms === 0 ? cutoffLabel : ms === 120 ? horizonLabel : "−" + Math.abs(ms);
      ctx.fillText(label, x(ms), bottom + 14);
    }
    ctx.beginPath();
    data.history.forEach((v, i) => {
      const px = x((i - 19) * 20),
        py = y(v);
      if (i) ctx.lineTo(px, py);
      else ctx.moveTo(px, py);
    });
    ctx.strokeStyle = "#15594e";
    ctx.lineWidth = 2.5;
    ctx.stroke();
    const fx = x(120),
      fy = y(prediction);
    ctx.beginPath();
    ctx.moveTo(fx, fy - 5);
    ctx.lineTo(fx + 5, fy);
    ctx.lineTo(fx, fy + 5);
    ctx.lineTo(fx - 5, fy);
    ctx.closePath();
    ctx.fillStyle = "#31549b";
    ctx.fill();
    if (data.observed !== undefined) {
      ctx.beginPath();
      ctx.arc(fx, y(data.observed), 7, 0, 2 * Math.PI);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = "#8d3919";
      ctx.stroke();
    }
  }

  function mount(host) {
    const template = document.getElementById("voltage-plot");
    if (!host || !template?.content) return null;
    host.append(template.content.cloneNode(true));
    const select = host.querySelector("select"),
      canvas = host.querySelector("canvas");
    const summary = host.querySelector(".plot-summary"),
      later = host.querySelector(".key-observed");
    const details = host.querySelector("details"),
      body = host.querySelector("tbody");
    let data = null,
      branches = "";
    function table() {
      body.replaceChildren();
      if (!data || !details.open) return;
      for (const [i, value] of data.history.entries()) {
        const row = body.insertRow();
        row.insertCell().textContent = String((i - 19) * 20);
        row.insertCell().textContent = asVolts(value);
      }
    }
    function redraw() {
      if (data) draw(canvas, data, select.value);
    }
    function describe() {
      const observed =
        data.observed === undefined
          ? ""
          : " Later reading " + asVolts(data.observed) + " V.";
      const text =
        models[select.value] +
        " predicts " +
        asVolts(data.predictions[select.value]) +
        " V at +120 ms." +
        observed;
      summary.textContent = text;
      canvas.setAttribute(
        "aria-label",
        data.source +
          ". Twenty sensor readings from 380 ms before cutoff through cutoff. " +
          text,
      );
      later.hidden = data.observed === undefined;
      redraw();
    }
    select.addEventListener("change", describe);
    details.addEventListener("toggle", table);
    if (typeof ResizeObserver === "function")
      new ResizeObserver(redraw).observe(canvas);
    else window.addEventListener("resize", redraw);
    return {
      show(history, predictions, source, observed) {
        data = { history, predictions, source, observed };
        const available = Object.keys(models).filter((id) => id in predictions);
        if (available.join() !== branches) {
          const previous = select.value;
          select.replaceChildren(
            ...available.map((id) => new Option(models[id], id)),
          );
          select.value = available.includes(previous)
            ? previous
            : "force_history";
          branches = available.join();
        }
        host.hidden = false;
        describe();
        table();
      },
      clear() {
        data = null;
        host.hidden = true;
        summary.textContent = "";
        canvas.removeAttribute("aria-label");
        canvas.width = canvas.width;
        body.replaceChildren();
        later.hidden = true;
      },
    };
  }
  globalThis.HygripVoltagePlot = { mount };
})();
