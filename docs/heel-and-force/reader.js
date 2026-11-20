(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const offsets = Array.from($("offset").options, (o) => Number(o.value));
  const colors = { joint: "#006e58", specialist: "#aa4914", past: "#5e7069", grid: "#bbcec2" };
  const signed = (n) => (n > 0 ? "+" : "") + n.toFixed(2).replace("-", "−");
  const vector = (xyz) => xyz.map(signed).join(" / ");
  let current, dirty = false, custom = false, shown = null;
  function element(tag, attrs = {}, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, val] of Object.entries(attrs)) node.setAttribute(key, val);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function tickSize(raw) {
    const base = 10 ** Math.floor(Math.log10(raw));
    return ([1, 2, 5, 10].find((x) => x * base >= raw) ?? 10) * base;
  }
  function drawPlot() {
    const g = $("geometry"), svg = $("trajectory");
    g.replaceChildren();
    if (!shown) return;
    const view = $("view").value;
    const width = Math.max(250, Math.round(svg.clientWidth)),
      height = Math.max(170, Math.round(svg.clientHeight));
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    const axes = view === "xyz" ? [0, 1, 2] : ({ xz: [0, 2], xy: [0, 1], yz: [1, 2] })[view];
    function project([x, y, z]) {
      return view === "xyz"
        ? [.832 * x - .555 * y, .303 * x + .454 * y - .838 * z]
        : view === "xz"
        ? [x, -z]
        : view === "xy"
        ? [x, -y]
        : [y, -z];
    }
    const heel = current.lab_marker_mm.at(-1)[0];
    const path = current.lab_marker_mm.map(([p]) => p.map((v, a) => v - heel[a]));
    const forecasts = [shown.joint.heel_delta_mm, shown.heel];
    const visible = $("range").value === "all" ? [...path, ...forecasts] : forecasts;
    const maximum = Math.max(.05, ...visible.flatMap((v) => axes.map((i) => Math.abs(v[i]))));
    const step = tickSize(maximum / 3);
    const extent = Math.max(step, maximum * 1.1);
    const unit = (axis) => [0, 1, 2].map((i) => i === axis ? 1 : 0);
    const axisEnds = axes.flatMap((axis) =>
      [-1, 1].map((sign) => unit(axis).map((a) => a * extent * sign))
    );
    const points = [...visible, ...axisEnds].map(project);
    const x0 = Math.min(...points.map((p) => p[0])), x1 = Math.max(...points.map((p) => p[0]));
    const y0 = Math.min(...points.map((p) => p[1])), y1 = Math.max(...points.map((p) => p[1]));
    const zoom = Math.min(
      (width - 68) / Math.max(.01, x1 - x0),
      (height - 48) / Math.max(.01, y1 - y0),
    );
    const ox = width / 2 - (x0 + x1) * zoom / 2, oy = height / 2 - (y0 + y1) * zoom / 2;
    const pixel = (v) => {
      const [x, y] = project(v);
      return [ox + x * zoom, oy + y * zoom];
    };
    const line = (from, to, attrs) => {
      const [x1, y1] = pixel(from), [x2, y2] = pixel(to);
      g.append(element("line", { x1, y1, x2, y2, ...attrs }));
    };
    const zero = [0, 0, 0];
    const defs = element("defs"), clip = element("clipPath", { id: "trajectory-clip" });
    clip.append(element("rect", { x: 9, y: 8, width: width - 18, height: height - 16 }));
    defs.append(clip);
    g.append(defs);
    if (view === "xyz") {
      const floor = extent * .72;
      for (let j = -2; j <= 2; j++) {
        const t = j * floor / 2;
        line([-floor, t, 0], [floor, t, 0], { stroke: "#d9e5dd", "stroke-width": .8 });
        line([t, -floor, 0], [t, floor, 0], { stroke: "#d9e5dd", "stroke-width": .8 });
      }
    }
    for (const axis of axes) {
      const u = unit(axis), pos = u.map((v) => v * extent), neg = u.map((v) => -v * extent);
      line(neg, pos, { stroke: colors.grid, "stroke-width": "1.15" });
      const [ex, ey] = pixel(pos), anchor = ex < ox - 6 ? "end" : ex > ox + 6 ? "start" : "middle";
      g.append(
        element("text", {
          x: ex + (anchor === "end" ? -3 : anchor === "start" ? 3 : 0),
          y: ey + (ey < oy - 5 ? -4 : 12),
          fill: "#51635a",
          "text-anchor": anchor,
          "font-size": 12,
        }, "+" + "XYZ"[axis]),
      );
      for (let tick = step; tick <= extent + 1e-12; tick += step) {
        for (const sign of [-1, 1]) {
          const [tx, ty] = pixel(u.map((v) => v * tick * sign));
          g.append(element("circle", { cx: tx, cy: ty, r: 1.8, fill: "#a0b8a9" }));
        }
      }
    }
    g.append(
      element("polyline", {
        points: path.map((v) => pixel(v).join(",")).join(" "),
        "clip-path": "url(#trajectory-clip)",
        fill: "none",
        stroke: colors.past,
        "stroke-width": "2.5",
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
      }),
    );
    // Put the dashed line in front so both remain visible when their projections overlap.
    for (const [i, v] of forecasts.entries()) {
      const color = i ? colors.specialist : colors.joint;
      const [tx, ty] = pixel(v), dx = tx - ox, dy = ty - oy, length = Math.hypot(dx, dy);
      const attrs = { stroke: color, "stroke-width": i ? 2.5 : 4, "stroke-linecap": "round" };
      if (i) attrs["stroke-dasharray"] = "5 4";
      line(zero, v, attrs);
      if (length > 5) {
        const ux = dx / length,
          uy = dy / length,
          head = Math.min(10, length * .5),
          ex = tx - head * ux,
          ey = ty - head * uy;
        g.append(
          element("path", {
            d: "M " + (ex - head * .42 * uy) + " " + (ey + head * .42 * ux) + " L " + tx + " " +
              ty + " L " + (ex + head * .42 * uy) + " " + (ey - head * .42 * ux),
            stroke: color,
            "stroke-width": 2,
            fill: i ? "none" : color,
            "stroke-linejoin": "round",
          }),
        );
      }
    }
    g.append(
      element("circle", {
        cx: ox,
        cy: oy,
        r: 3.5,
        fill: "#fffef8",
        stroke: "#182a26",
        "stroke-width": 1.5,
      }),
    );
    $("scale").textContent = "Axis ticks " + Number(step.toPrecision(3)) + " mm apart";
    $("chartDesc").textContent =
      "The line follows the invented or edited right heel history up to the cutoff. Joint-model displacement XYZ in millimetres: " +
      vector(forecasts[0]) + ". Heel specialist: " + vector(forecasts[1]) + ".";
  }
  function plotForces(a, b) {
    const bound = tickSize(Math.max(1, Math.abs(a), Math.abs(b)) / 4);
    const low = Math.min(0, Math.floor(Math.min(a, b) / bound) * bound);
    const high = Math.max(0, Math.ceil(Math.max(a, b) / bound) * bound);
    const range = high - low || 1, px = (n) => 100 * (n - low) / range;
    for (const [id, v] of [["joint-bar", a], ["special-bar", b]]) {
      const bar = $(id);
      bar.style.left = Math.min(px(0), px(v)) + "%";
      bar.style.width = Math.abs(px(v) - px(0)) + "%";
    }
    $("force-scale").textContent = "Shared scale " + low + " to " + high + " N";
  }
  function assertInput(raw) {
    const exact = (a, n) => Array.isArray(a) && a.length === n;
    const finite = (v) => typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= 1e9;
    if (!raw || !offsets.includes(raw.offset_frames)) {
      throw Error("Choose an observed strike offset in frames: " + offsets.join(", ") + ".");
    }
    if (
      !exact(raw.lab_marker_mm, 24) ||
      !raw.lab_marker_mm.every((f) => exact(f, 2) && f.every((p) => exact(p, 3) && p.every(finite)))
    ) {
      throw Error(
        "Supply 24 marker frames with two XYZ positions each (finite values up to 10⁹ mm in magnitude).",
      );
    }
    if (
      !exact(raw.emg_rms_uV, 4) ||
      !raw.emg_rms_uV.every((b) => exact(b, 8) && b.every((v) => finite(v) && v >= 0))
    ) throw Error("Supply four bins of eight nonnegative muscle readings each (up to 10⁹ µV).");
    return {
      lab_marker_mm: raw.lab_marker_mm,
      emg_rms_uV: raw.emg_rms_uV,
      offset_frames: raw.offset_frames,
    };
  }
  function clear(message) {
    shown = null;
    for (const id of ["joint-xyz", "special-xyz", "joint-force", "special-force"]) {
      $(id).textContent = "—";
    }
    for (const id of ["joint-bar", "special-bar"]) $(id).style.width = "0";
    $("scale").textContent = "";
    $("force-scale").textContent = "";
    $("geometry").replaceChildren();
    $("chartDesc").textContent = "No current forecast.";
    $("status").textContent = message;
  }
  function predict() {
    if (dirty) {
      clear("Edits pending. Apply the edited history to calculate its forecast.");
      return;
    }
    const supported = $("offset").selectedOptions[0];
    $("support").textContent = "Development support here: " + supported.dataset.rows +
      " cutoffs from " + supported.dataset.people + " people.";
    const motionOnly = $("joint-mode").value === "marker";
    $("mode-note").textContent = motionOnly
      ? "The joint model uses markers and elapsed time. Both specialists still receive the muscle history."
      : "Both specialists receive the same markers, elapsed time and muscle history as the joint model.";
    try {
      const k = globalThis.HeelAndForceModels, run = globalThis.GaitPair.predict;
      const joint = run(motionOnly ? k.marker : k.joint, current),
        heel = run(k.heel, current).heel_delta_mm;
      const force = run(k.force, current).plate_up_N;
      if (![...joint.heel_delta_mm, ...heel, joint.plate_up_N, force].every(Number.isFinite)) {
        throw Error("This input gives a nonfinite forecast. Revise its readings.");
      }
      shown = { joint, heel, force };
      $("joint-xyz").textContent = vector(joint.heel_delta_mm);
      $("special-xyz").textContent = vector(heel);
      $("joint-force").textContent = joint.plate_up_N.toFixed(1) + " N";
      $("special-force").textContent = force.toFixed(1) + " N";
      plotForces(joint.plate_up_N, force);
      drawPlot();
      $("status").textContent = "";
    } catch (e) {
      clear("Forecast unavailable. " + e.message);
    }
  }
  function writeRaw() {
    $("raw").value = JSON.stringify(current, null, 1);
    $("raw").removeAttribute("aria-invalid");
    dirty = false;
  }
  function preset() {
    custom = false;
    dirty = false;
    const rise = Number($("rise").value), gain = Number($("gain").value);
    $("rise-label").textContent = rise.toFixed(2) + " mm";
    $("gain-label").textContent = gain.toFixed(2) + "×";
    current = HeelAndForceExamples.invented({
      rise,
      gain,
      offset: Number($("offset").value),
      alternate: $("pattern").value === "alternate",
    });
    writeRaw();
    predict();
  }
  function restore() {
    $("offset").value = String(offsets.includes(24) ? 24 : offsets[0]);
    $("joint-mode").value = "full";
    $("rise").value = "4";
    $("gain").value = "1";
    $("pattern").value = "original";
    preset();
  }
  $("restore").addEventListener("click", restore);
  $("raw").addEventListener("input", () => {
    dirty = true;
    $("raw").removeAttribute("aria-invalid");
    predict();
  });
  $("discard").addEventListener("click", () => {
    writeRaw();
    predict();
  });
  $("apply").addEventListener("click", () => {
    try {
      current = assertInput(JSON.parse($("raw").value));
      custom = true;
      $("offset").value = current.offset_frames;
      writeRaw();
      $("rise-label").textContent = "Custom";
      $("gain-label").textContent = "Custom";
      $("pattern").value = "custom";
      predict();
    } catch (e) {
      dirty = true;
      $("raw").setAttribute("aria-invalid", "true");
      clear("Cannot use these edits. " + e.message);
    }
  });
  for (const id of ["rise", "gain"]) {
    $(id).addEventListener("input", () => {
      if ($("pattern").value === "custom") $("pattern").value = "original";
      preset();
    });
  }
  $("pattern").addEventListener("change", preset);
  $("joint-mode").addEventListener("change", predict);
  $("offset").addEventListener("change", () => {
    if (custom || dirty) {
      if (dirty) {
        $("offset").value = String(current.offset_frames);
        predict();
        return;
      }
      current.offset_frames = Number($("offset").value);
      writeRaw();
      predict();
    } else preset();
  });
  $("view").addEventListener("change", drawPlot);
  $("range").addEventListener("change", drawPlot);
  new ResizeObserver(drawPlot).observe($("trajectory"));
  $("pattern").add(new Option("Edited history", "custom"));
  $("pattern").options[2].disabled = true;
  if (location.protocol === "file:") {
    for (const a of document.querySelectorAll(".online")) a.hidden = true;
  }
  $("order").textContent = "Muscle channels in order: " + HeelAndForceExamples.channels.join(", ") +
    ".";
  restore();
})();
