(() => {
  const geometry = ReachGeometry;
  const patterns = { ridge_residual: [], ar_ridge: [7, 3, 1, 3], diff_ridge: [1, 4] };
  const modelColor = { ridge_residual: '--residual', ar_ridge: '--ar', diff_ridge: '--diff' };

  function scene(canvas, onViewChange) {
    const ctx = canvas.getContext('2d');
    const forced = matchMedia('(forced-colors: active)');
    let model, state, frame, frameKey, queued = false;
    let [yaw, pitch] = geometry.presets.oblique;
    let gesture;
    let colors = {};
    function palette() {
      const style = getComputedStyle(document.documentElement);
      for (const name of ['--stage', '--stage-text', '--stage-soft', '--grid', '--ridge', '--residual', '--ar', '--diff', '--measured']) {
        colors[name] = style.getPropertyValue(name).trim();
      }
    }
    palette();
    function line(points, color, width, dash = [], alpha = 1) {
      if (points.length < 2) return;
      ctx.beginPath();
      ctx.moveTo(...points[0]);
      for (let i = 1; i < points.length; i++) ctx.lineTo(...points[i]);
      ctx.setLineDash(dash);
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha;
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.setLineDash([]);
    }
    function mark([x,y], site, r, color, filled) {
      ctx.beginPath();
      if (site === 0) ctx.arc(x, y, r, 0, 2 * Math.PI);
      else {
        ctx.moveTo(x, y-r);
        ctx.lineTo(x+r, y);
        ctx.lineTo(x, y+r);
        ctx.lineTo(x-r, y);
        ctx.closePath();
      }
      ctx.fillStyle = filled ? color : colors['--stage'];
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.65;
      ctx.stroke();
    }
    function text(value, x, y, color, size = 12, align = 'left') {
      ctx.font = '600 ' + size + 'px system-ui, sans-serif';
      ctx.textAlign = align;
      ctx.lineWidth = 3.6;
      ctx.strokeStyle = colors['--stage'];
      ctx.strokeText(value, x, y);
      ctx.fillStyle = color;
      ctx.fillText(value, x, y);
    }
    function guides(cam, w, h) {
      const { center, radius, low } = frame;
      const ground = low[2] - radius * 0.08;
      const step = geometry.nice(radius / 1.7);
      const extent = step * 4;
      for (let k = -4; k <= 4; k++) {
        const v = k * step;
        line([[center[0] + v, center[1] - extent, ground], [center[0] + v, center[1] + extent, ground]].map(cam.project), colors['--grid'], 0.8, [], forced.matches ? 0.5 : 0.72);
        line([[center[0] - extent, center[1] + v, ground], [center[0] + extent, center[1] + v, ground]].map(cam.project), colors['--grid'], 0.8, [], forced.matches ? 0.5 : 0.72);
      }
      const anchor = [31, h - 27];
      for (let i = 0; i < 3; i++) {
        if (Math.hypot(cam.x[i], cam.y[i]) < 0.16) continue;
        const tip = [anchor[0] + 18 * cam.x[i], anchor[1] - 18 * cam.y[i]];
        line([anchor, tip], colors['--stage-soft'], 1.1);
        text('XYZ'[i], anchor[0] + 24 * cam.x[i], anchor[1] - 24 * cam.y[i] + 3, colors['--stage-soft'], 10, 'center');
      }
      const mm = geometry.nice(68 / cam.pxPerMm), length = mm * cam.pxPerMm;
      const end = w - 10, left = end - length, y = h - 11;
      line([[left,y-3],[left,y],[end,y],[end,y-3]], colors['--stage-text'], 1.35);
      text(mm.toLocaleString('en-US', { maximumFractionDigits: 3 }) + ' mm', end, y - 7, colors['--stage-soft'], 11, 'right');
    }
    function render() {
      queued = false;
      if (!model || !state) return;
      const w = canvas.clientWidth, h = canvas.clientHeight;
      if (w < 1 || h < 1) return;
      const ratio = Math.min(devicePixelRatio || 1, 2);
      const bw = Math.max(1, Math.round(w * ratio)), bh = Math.max(1, Math.round(h * ratio));
      if (canvas.width !== bw || canvas.height !== bh) {
        canvas.width = bw;
        canvas.height = bh;
      }
      ctx.setTransform(bw / w, 0, 0, bh / h, 0, 0);
      ctx.fillStyle = colors['--stage'];
      ctx.fillRect(0, 0, w, h);
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      const markers = geometry.visibleMarkers(model, state.focus);
      const key = model.label + '/' + state.focus + '/' + state.reveal;
      if (key !== frameKey) {
        frame = geometry.framing(markers, state.reveal);
        frameKey = key;
      }
      const cam = geometry.camera(frame, yaw, pitch, w, h);
      const count = state.horizon + 1;
      const projected = path => path.slice(0, count).map(cam.project);
      guides(cam, w, h);
      for (const m of markers) {
        for (const key of state.families) {
          const color = colors[modelColor[key]];
          for (const path of m.paths[key]) {
            line(projected(path), color, forced.matches ? 1.05 : 1.15, forced.matches ? patterns[key] : [], forced.matches ? 0.4 : 0.22);
          }
        }
        line(m.past.map(cam.project), colors['--stage-text'], 2.1);
        if (state.ridge) line(projected(m.ridge), colors['--ridge'], 2.1, [7, 4]);
        for (const key of state.families) {
          const pts = projected(m.paths[key][state.draw]);
          const color = colors[modelColor[key]];
          line(pts, color, 2.8, patterns[key]);
          mark(pts.at(-1), m.site, 3, color, false);
        }
        if (state.reveal) {
          const pts = projected(m.recorded);
          line(pts, colors['--measured'], 2.8);
          for (const point of pts.slice(1)) mark(point, m.site, 2.85, colors['--measured'], true);
        }
      }
      for (const m of markers) {
        const [x,y] = cam.project(m.last);
        mark([x,y], m.site, 4.25, colors['--stage-text'], false);
        const labelX = Math.max(22, Math.min(w - 22, x));
        const labelY = Math.max(16, Math.min(h - 14, y + (m.site === 0 ? -16 : 25)));
        text(m.site === 0 ? 'Hand' : 'Elbow', labelX, labelY, colors['--stage-text'], 12, 'center');
      }
    }
    function schedule() {
      if (!queued) {
        queued = true;
        requestAnimationFrame(render);
      }
    }
    function preset(key) {
      [yaw, pitch] = geometry.presets[key];
      onViewChange(key);
      schedule();
    }
    function rotate(dx, dy) {
      yaw += dx;
      pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, pitch + dy));
      onViewChange('custom');
      schedule();
    }
    canvas.addEventListener('pointerdown', e => {
      if (!e.isPrimary || e.button !== 0) return;
      gesture = [e.pointerId, e.clientX, e.clientY];
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', e => {
      if (!gesture || gesture[0] !== e.pointerId) return;
      rotate((e.clientX - gesture[1]) * .013, (gesture[2] - e.clientY) * .013);
      gesture = [e.pointerId, e.clientX, e.clientY];
    });
    canvas.addEventListener('lostpointercapture', () => { gesture = null; });
    canvas.addEventListener('keydown', e => {
      const arrows = { ArrowLeft: [-.12,0], ArrowRight: [.12,0], ArrowUp: [0,.12], ArrowDown: [0,-.12] };
      if (Object.hasOwn(arrows, e.key)) {
        e.preventDefault();
        rotate(...arrows[e.key]);
      } else if (e.key === 'Home') {
        e.preventDefault();
        preset('oblique');
      }
    });
    new ResizeObserver(schedule).observe(canvas);
    forced.addEventListener('change', () => { palette(); schedule(); });
    return {
      preset,
      update(example, settings) { model = example; state = settings; schedule(); },
    };
  }
  globalThis.createReachScene = scene;
})();
