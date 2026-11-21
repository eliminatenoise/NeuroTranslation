/* The orthographic camera follows Interoceptomics' CC0 reach-feedback viewer. */
(() => {
  const families = ['ridge_residual', 'ar_ridge', 'diff_ridge'];
  const presets = { oblique: [-0.68, 0.38], xy: [0, Math.PI / 2], xz: [0, 0], yz: [Math.PI / 2, 0] };

  function sitePath(rows, origin, site) {
    const start = site * 3;
    return rows.map(row => [
      row[start] + origin[start],
      row[start + 1] + origin[start + 1],
      row[start + 2] + origin[start + 2],
    ]);
  }

  function prepare(example) {
    if (example.origins_mm.length !== 6 || !example.origins_mm.every(Number.isFinite)) {
      throw Error('Both marker origins in millimetres are required.');
    }
    const markers = [0, 1].map(site => {
      const convert = rows => sitePath(rows, example.origins_mm, site);
      const past = convert(example.past);
      const last = past.at(-1);
      const future = rows => [last, ...convert(rows)];
      const ridge = future(example.ridge_point);
      const recorded = future(example.recorded);
      const paths = Object.fromEntries(families.map(key => [key, example.paths[key].map(future)]));
      const framePoints = [...past, ...ridge, ...families.flatMap(key => paths[key].flat())];
      return { site, past, last, ridge, recorded, paths, framePoints };
    });
    return { label: example.label, markers };
  }

  function visibleMarkers(example, focus) {
    if (focus === 'both') return example.markers;
    return [example.markers[focus === 'hand' ? 0 : 1]];
  }

  function framing(markers, reveal) {
    const points = markers.flatMap(marker =>
      reveal ? marker.framePoints.concat(marker.recorded) : marker.framePoints
    );
    const low = [Infinity, Infinity, Infinity], high = [-Infinity, -Infinity, -Infinity];
    for (const p of points) {
      for (let i = 0; i < 3; i++) {
        low[i] = Math.min(low[i], p[i]);
        high[i] = Math.max(high[i], p[i]);
      }
    }
    const center = low.map((v, i) => (v + high[i]) / 2);
    const centered = points.map(p => p.map((v, i) => v - center[i]));
    const radius = Math.max(0.5, ...centered.map(p => Math.hypot(...p)));
    return { center, centered, radius, low };
  }

  function camera(frame, yaw, pitch, width, height) {
    const x = [Math.cos(yaw), Math.sin(yaw), 0];
    const y = [-Math.sin(yaw) * Math.sin(pitch), Math.cos(yaw) * Math.sin(pitch), Math.cos(pitch)];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    let halfX = frame.radius * 0.16, halfY = frame.radius * 0.16;
    for (const p of frame.centered) {
      halfX = Math.max(halfX, Math.abs(dot(p, x)));
      halfY = Math.max(halfY, Math.abs(dot(p, y)));
    }
    const padX = width < 400 ? 25 : 48, padY = height < 280 ? 42 : 60;
    const pxPerMm = Math.max(0.001, Math.min(
      (width - 2 * padX) / (2 * halfX),
      (height - 2 * padY) / (2 * halfY),
      2 * (height - 2 * padY) / frame.radius
    ));
    function project(p) {
      const d = [p[0] - frame.center[0], p[1] - frame.center[1], p[2] - frame.center[2]];
      return [width / 2 + dot(d, x) * pxPerMm, height / 2 - dot(d, y) * pxPerMm];
    }
    return { x, y, pxPerMm, project };
  }

  function nice(value) {
    const n = 10 ** Math.floor(Math.log10(Math.max(value, 1e-9)));
    return n * (value / n >= 5 ? 5 : value / n >= 2 ? 2 : 1);
  }

  globalThis.ReachGeometry = { families, presets, prepare, visibleMarkers, framing, camera, nice };
})();
