// SPDX-License-Identifier: CC0-1.0
(() => {
  "use strict";

  // Orthographic basis and plane views from the CC0 reach/explore reader.
  const angles = {oblique: [0.82, 0.23], xy: [0, Math.PI / 2], xz: [0, 0], yz: [Math.PI / 2, 0]};
  const seriesNames = {
    input: "Input positions", absolute: "Recorded-position model",
    relative: "Relative-position model", velocity: "Constant velocity"
  };
  const arrows = {ArrowLeft: [-.12, 0], ArrowRight: [.12, 0], ArrowUp: [0, .12], ArrowDown: [0, -.12]};

  function svg(tag, attributes = {}, text = "") {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    if (text) element.textContent = text;
    return element;
  }

  function markerTracks(readings, displacements, offset) {
    const input = readings.map(row => row.slice(offset, offset + 3));
    const last = input.at(-1);
    const tracks = {input};
    for (const [key, path] of Object.entries(displacements)) {
      tracks[key] = [last, ...path.map(row => last.map((origin, axis) => origin + row[offset + axis]))];
    }
    return {name: offset === 0 ? "Hand" : "Elbow", tracks, last};
  }

  function frameFor(markers) {
    const points = markers.flatMap(marker => Object.values(marker.tracks).flat());
    const bounds = [0, 1, 2].map(axis => {
      const values = points.map(point => point[axis]);
      return [Math.min(...values), Math.max(...values)];
    });
    const center = bounds.map(([min, max]) => (min + max) / 2);
    const centered = points.map(p => p.map((value, i) => value - center[i]));
    const radius = Math.max(0.5, ...centered.map(p => Math.hypot(...p)));
    return {center, centered, radius, minZ: bounds[2][0]};
  }

  function camera(frame, yaw, pitch, width, height) {
    const x = [Math.cos(yaw), Math.sin(yaw), 0];
    const y = [-Math.sin(yaw) * Math.sin(pitch), Math.cos(yaw) * Math.sin(pitch), Math.cos(pitch)];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const extent = basis => Math.max(frame.radius * .16, ...frame.centered.map(p => Math.abs(dot(p, basis))));
    const padX = Math.min(width * .16, width < 400 ? 23 : 44);
    const padY = Math.min(height * .22, 49);
    const pixelsPerMm = Math.min(
      (width - 2 * padX) / (2 * extent(x)), (height - 2 * padY) / (2 * extent(y)),
      2 * (height - 2 * padY) / frame.radius
    );
    function project(point) {
      const p = point.map((value, i) => value - frame.center[i]);
      return [width / 2 + dot(p, x) * pixelsPerMm, height / 2 - dot(p, y) * pixelsPerMm];
    }
    return {x, y, pixelsPerMm, project};
  }

  function rulerStep(value) {
    const power = 10 ** Math.floor(Math.log10(value));
    const units = value / power;
    return power * (units >= 5 ? 5 : units >= 2 ? 2 : 1);
  }

  function number(value) {
    const absolute = Math.abs(value);
    if (absolute >= 100000 || (absolute > 0 && absolute < .001)) return Number(value.toPrecision(4)).toExponential();
    return String(Number(value.toFixed(3)));
  }

  function guides(frame, view, width, height) {
    const layer = svg("g", {"aria-hidden": "true"});
    const [cx, cy] = frame.center;
    const z = frame.minZ - frame.radius * .08;
    const step = rulerStep(frame.radius / 1.7);
    const extent = 4 * step;
    let grid = "";
    for (let k = -4; k <= 4; k++) {
      const d = k * step;
      grid += "M" + view.project([cx + d, cy - extent, z]) + "L" + view.project([cx + d, cy + extent, z]);
      grid += "M" + view.project([cx - extent, cy + d, z]) + "L" + view.project([cx + extent, cy + d, z]);
    }
    layer.append(svg("path", {class: "space-grid", d: grid}));
    const ax = 41, ay = height - 40;
    const axisLabels = [];
    for (let i = 0; i < 3; i++) {
      if (Math.hypot(view.x[i], view.y[i]) < .16) continue;
      const tipX = ax + 16 * view.x[i], tipY = ay - 16 * view.y[i];
      layer.append(svg("path", {class: "space-ruler", d: `M ${ax} ${ay} L ${tipX} ${tipY}`}));
      const candidates = [25, 39, 17].map(r => [ax + r * view.x[i], ay - r * view.y[i] + 4]);
      const position = candidates.find(([x, y]) => axisLabels.every(([px, py]) => Math.hypot(x - px, y - py) >= 14)) || candidates[0];
      axisLabels.push(position);
      layer.append(svg("text", {
        class: "space-guide-text", x: position[0], y: position[1], "text-anchor": "middle"
      }, "XYZ"[i]));
    }
    const mm = rulerStep(Math.min(66, width * .22) / view.pixelsPerMm);
    const end = width - 13, left = end - mm * view.pixelsPerMm, bottom = height - 11;
    layer.append(svg("path", {class: "space-ruler", d: `M ${left} ${bottom - 4} V ${bottom} H ${end} v -4`}));
    layer.append(svg("text", {class: "space-guide-text", x: end, y: bottom - 7, "text-anchor": "end"}, number(mm) + " mm"));
    return layer;
  }

  function symbolFor(key) {
    if (key === "relative") return svg("polygon");
    if (key === "velocity") return svg("rect", {width: 5.5, height: 5.5});
    return svg("circle", {r: key === "input" ? 2 : 3.3});
  }

  function placeSymbol(symbol, key, [x, y]) {
    if (key === "relative") {
      symbol.setAttribute("points", `${x},${y - 4} ${x + 3.8},${y + 2.9} ${x - 3.8},${y + 2.9}`);
    } else if (key === "velocity") {
      symbol.setAttribute("x", x - 2.75);
      symbol.setAttribute("y", y - 2.75);
    } else {
      symbol.setAttribute("cx", x);
      symbol.setAttribute("cy", y);
    }
  }

  function createReachSpace() {
    const get = id => document.getElementById(id);
    const card = get("space-view");
    if (!card) return;
    const plot = get("space-plot"), focus = get("space-markers"), angle = get("space-angle");
    const series = get("space-series"), details = get("space-readout"), tables = get("space-tables");
    const summary = get("space-summary");
    let [yaw, pitch] = angles.oblique;
    let sites = [], visible = [], lines = [], labels = [], times = {}, frame, guideLayer, gesture;
    let selection = "", preferredSeries = "input", drawRequest = 0;

    function draw() {
      drawRequest = 0;
      const w = plot.clientWidth, h = plot.clientHeight;
      if (!frame || !w || !h) return;
      plot.setAttribute("viewBox", `0 0 ${w} ${h}`);
      const view = camera(frame, yaw, pitch, w, h);
      const nextGuides = guides(frame, view, w, h);
      guideLayer.replaceWith(nextGuides);
      guideLayer = nextGuides;
      for (const {key, path, line, symbols} of lines) {
        const points = path.map(view.project);
        line.setAttribute("points", points.map(point => point.join(",")).join(" "));
        const first = key === "input" ? 0 : 1;
        symbols.forEach((symbol, i) => placeSymbol(symbol, key, points[i + first]));
      }
      for (const {site, mark, text} of labels) {
        const [x, y] = view.project(site.last);
        mark.setAttribute("cx", x);
        mark.setAttribute("cy", y);
        text.setAttribute("x", Math.max(32, Math.min(w - 32, x)));
        text.setAttribute("y", Math.max(16, Math.min(h - 12, y + (site.name === "Hand" ? -14 : 21))));
      }
    }

    function schedule() {
      if (frame && !drawRequest) drawRequest = requestAnimationFrame(draw);
    }

    function readout() {
      tables.replaceChildren();
      if (!details.open || !visible.length) return;
      const key = series.value;
      for (const site of visible) {
        const table = document.createElement("table");
        table.createCaption().textContent = site.name + " · " + seriesNames[key] + " (mm)";
        const header = table.createTHead().insertRow();
        for (const heading of ["Time (ms)", "X", "Y", "Z"]) {
          const cell = document.createElement("th");
          cell.scope = "col";
          cell.textContent = heading;
          header.append(cell);
        }
        const body = table.createTBody();
        site.tracks[key].forEach((point, i) => {
          const row = body.insertRow();
          const time = document.createElement("th");
          time.scope = "row";
          time.textContent = String(times[key][i]);
          row.append(time);
          for (const value of point) row.insertCell().textContent = number(value);
        });
        tables.append(table);
      }
    }

    function setMarkers() {
      if (!sites.length) return;
      visible = sites.filter(site => focus.value === "both" || site.name.toLowerCase() === focus.value);
      frame = frameFor(visible);
      guideLayer = svg("g");
      const drawing = document.createDocumentFragment();
      drawing.append(guideLayer);
      lines = [];
      labels = [];
      for (const site of visible) {
        for (const [key, path] of Object.entries(site.tracks)) {
          const group = svg("g", {class: "space-track " + key, "data-marker": site.name.toLowerCase()});
          const line = svg("polyline");
          const symbols = (key === "input" ? path : path.slice(1)).map(() => symbolFor(key));
          group.append(line, ...symbols);
          drawing.append(group);
          lines.push({key, path, line, symbols});
        }
        const mark = svg("circle", {class: "space-origin", r: 4.5});
        const text = svg("text", {class: "space-label", "text-anchor": "middle"}, site.name);
        labels.push({site, mark, text});
      }
      for (const {mark, text} of labels) drawing.append(mark, text);
      plot.replaceChildren(drawing);
      summary.textContent = visible.map(site => site.name).join(" and ") + ". " + selection + ". " +
        Object.keys(times).map(key => seriesNames[key]).join(", ") + ". Each forecast begins at the marker’s last input position.";
      readout();
      schedule();
    }

    function setAngle(key) {
      [yaw, pitch] = angles[key];
      angle.value = key;
      schedule();
    }

    function rotate(dx, dy) {
      yaw += dx;
      pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, pitch + dy));
      angle.value = "custom";
      schedule();
    }

    plot.addEventListener("keydown", event => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (Object.hasOwn(arrows, event.key)) {
        event.preventDefault();
        rotate(...arrows[event.key]);
      } else if (event.key === "Home") {
        event.preventDefault();
        setAngle("oblique");
      }
    });
    plot.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      gesture = [event.pointerId, event.clientX, event.clientY];
      plot.setPointerCapture(event.pointerId);
    });
    plot.addEventListener("pointermove", event => {
      if (gesture?.[0] !== event.pointerId) return;
      rotate((event.clientX - gesture[1]) * .013, (gesture[2] - event.clientY) * .013);
      gesture = [event.pointerId, event.clientX, event.clientY];
    });
    plot.addEventListener("lostpointercapture", () => { gesture = null; });
    focus.addEventListener("change", setMarkers);
    angle.addEventListener("change", () => { if (Object.hasOwn(angles, angle.value)) setAngle(angle.value); });
    details.addEventListener("toggle", readout);
    series.addEventListener("change", () => { preferredSeries = series.value; readout(); });
    if (typeof ResizeObserver === "function") new ResizeObserver(schedule).observe(plot);
    else window.addEventListener("resize", schedule);

    return {
      show(readings, paths, futureTimes, selectedPath) {
        sites = [0, 3].map(offset => markerTracks(readings, paths, offset));
        times = {input: readings.map((_, i) => (i + 1 - readings.length) * 10)};
        for (const key of Object.keys(paths)) times[key] = [0, ...futureTimes];
        selection = selectedPath;
        series.replaceChildren(...Object.keys(times).map(key => new Option(seriesNames[key], key)));
        series.value = Object.hasOwn(times, preferredSeries) ? preferredSeries : "input";
        for (const key of ["absolute", "relative"]) get("space-" + key + "-key").hidden = !Object.hasOwn(paths, key);
        card.hidden = false;
        setMarkers();
      },
      clear() {
        if (drawRequest) cancelAnimationFrame(drawRequest);
        drawRequest = 0;
        sites = []; visible = []; lines = []; labels = []; times = {}; frame = null; gesture = null;
        card.hidden = true;
        plot.replaceChildren();
        series.replaceChildren();
        tables.replaceChildren();
        summary.textContent = "";
      }
    };
  }

  globalThis.createReachSpace = createReachSpace;
})();
