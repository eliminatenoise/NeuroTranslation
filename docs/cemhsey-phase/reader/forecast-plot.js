"use strict";

(() => {
  const C = globalThis.PinchIntervals;
  const colours = {
    ink: "#23423d", muted: "#4c625d", baseline: "#b2c7be", grid: "#e2ede6",
    plot: "#fff", band: "#c7e4d9", model: "#1b6258", reading: "#9d3e0e", cursor: "#566c65"
  };

  function draw(canvas, series, issueTick, phaseScheme) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;
    const ratio = Math.min(2, globalThis.devicePixelRatio || 1);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);
    ctx.fillStyle = colours.plot;
    ctx.fillRect(0, 0, width, height);
    if (!series.length) return;

    const margins = {left: width < 420 ? 55 : 70, right: 17, top: 27, bottom: 44};
    const right = width - margins.right;
    const bottom = height - margins.bottom;
    const horizontal = right - margins.left;
    const vertical = bottom - margins.top;
    const x = tick => margins.left + horizontal * tick / 6000;
    let min = Infinity;
    let max = -Infinity;
    let lowestReading = Infinity;
    for (const entry of series) {
      min = Math.min(min, entry.point, entry.range?.lower ?? Infinity, entry.observed ?? Infinity);
      max = Math.max(max, entry.point, entry.range?.upper ?? -Infinity, entry.observed ?? -Infinity);
      lowestReading = Math.min(lowestReading, entry.point, entry.observed ?? Infinity);
    }
    // Force is a share of the hardest pinch: start the axis at zero unless a forecast or reading is itself negative,
    // and use round tick steps. A band edge below zero is drawn at the axis floor.
    const floor = lowestReading >= 0 ? 0 : min;
    const pad = Math.max((max - floor) * .08, 1e-6);
    const rawStep = (max + pad - floor) / 4;
    const power = 10 ** Math.floor(Math.log10(rawStep));
    const mantissa = rawStep / power;
    const tickStep = (mantissa <= 1 ? 1 : mantissa <= 2 ? 2 : mantissa <= 2.5 ? 2.5 : mantissa <= 5 ? 5 : 10) * power;
    const axisLow = lowestReading >= 0 ? 0 : Math.floor((min - pad) / tickStep) * tickStep;
    const axisHigh = Math.ceil((max + pad) / tickStep) * tickStep;
    const y = value => bottom - (Math.min(axisHigh, Math.max(axisLow, value)) - axisLow) * vertical / (axisHigh - axisLow);

    function line(points, color, strokeWidth, dash = []) {
      ctx.beginPath();
      points.forEach(([xx, yy], i) => i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy));
      ctx.strokeStyle = color;
      ctx.lineWidth = strokeWidth;
      ctx.setLineDash(dash);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    function dot(xx, yy, color, radius, hollow = false) {
      ctx.beginPath();
      ctx.arc(xx, yy, radius, 0, 2 * Math.PI);
      ctx.fillStyle = hollow ? colours.plot : color;
      ctx.fill();
      if (hollow) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    ctx.font = "12px system-ui, sans-serif";
    ctx.fillStyle = colours.muted;
    ctx.textAlign = "left";
    ctx.fillText("Force (fraction of MVC)", margins.left, 15);
    ctx.textAlign = "right";
    const steps = Math.round((axisHigh - axisLow) / tickStep);
    for (let step = 0; step <= steps; step++) {
      const value = axisLow + tickStep * step;
      const yy = y(value);
      const printed = Number.isFinite(value) ? Number(value.toPrecision(3)).toString() : "";
      line([[margins.left, yy], [right, yy]], colours.grid, 1);
      ctx.fillText(printed, margins.left - 7, yy + 4, margins.left - 9);
    }
    line([[margins.left, margins.top], [margins.left, bottom], [right, bottom]], colours.baseline, 1);
    ctx.textAlign = "center";
    const stepTick = width < 420 ? 2000 : 1000;
    for (let tick = 0; tick <= 6000; tick += stepTick) {
      const xx = x(tick);
      line([[xx, bottom], [xx, bottom + 4]], colours.baseline, 1);
      ctx.fillText(String(tick / 200), xx, bottom + 17);
    }
    ctx.fillText("Target time (nominal seconds)", margins.left + horizontal / 2, height - 7);
    for (const tick of C.phaseEdges.slice(1, -1)) {
      const xx = x(tick + C.horizon);
      line([[xx, margins.top], [xx, bottom]], colours.baseline, .8, [2, 4]);
    }

    const selected = series.at(-1);
    if (selected.range) {
      let start = 0;
      for (let end = 1; end <= series.length; end++) {
        const withinPhase = !phaseScheme ||
          (end < series.length && C.phaseAt(series[end].tick) === C.phaseAt(series[start].tick));
        if (end < series.length && withinPhase) continue;
        const run = series.slice(start, end);
        ctx.beginPath();
        run.forEach(({tick, range}, i) => {
          const xx = x(tick + C.horizon);
          i ? ctx.lineTo(xx, y(range.upper)) : ctx.moveTo(xx, y(range.upper));
        });
        run.reverse().forEach(({tick, range}) => ctx.lineTo(x(tick + C.horizon), y(range.lower)));
        ctx.closePath();
        ctx.fillStyle = colours.band;
        ctx.fill();
        start = end;
      }
    }
    if (selected.observed !== undefined) {
      line(series.map(({tick, observed}) => [x(tick + C.horizon), y(observed)]), colours.reading, 1.5, [5, 3]);
    }
    const cursor = x(issueTick);
    line([[cursor, margins.top], [cursor, bottom]], colours.cursor, 1.2, [4, 4]);
    line(series.map(({tick, point}) => [x(tick + C.horizon), y(point)]), colours.model, 2);
    const selectedX = x(selected.tick + C.horizon);
    if (selected.range) {
      const lower = y(selected.range.lower);
      const upper = y(selected.range.upper);
      line([[selectedX - 4, lower], [selectedX + 4, lower]], colours.model, 1.5);
      line([[selectedX, lower], [selectedX, upper]], colours.model, 1.5);
      line([[selectedX - 4, upper], [selectedX + 4, upper]], colours.model, 1.5);
    }
    if (selected.observed !== undefined) dot(selectedX, y(selected.observed), colours.reading, 5, true);
    dot(selectedX, y(selected.point), colours.model, 3);
  }

  globalThis.PinchPlot = {draw};
})();
