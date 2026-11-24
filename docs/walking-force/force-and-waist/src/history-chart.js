const historyChart = (() => {
  const GUTTER = {left: 52, right: 16, top: 14, bottom: 32};
  const tag = value => {
    if (Math.abs(value) >= 100000 || (value !== 0 && Math.abs(value) < 0.0001)) return value.toExponential(1);
    return Number(value.toPrecision(3)).toLocaleString('en-US', { maximumFractionDigits: 4 });
  };

  function draw(canvas, series) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (width <= GUTTER.left + GUTTER.right || height <= GUTTER.top + GUTTER.bottom) return;
    const ratio = window.devicePixelRatio || 1;
    const pixels = [Math.round(width * ratio), Math.round(height * ratio)];
    if (canvas.width !== pixels[0] || canvas.height !== pixels[1]) {
      [canvas.width, canvas.height] = pixels;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const horizontal = width - GUTTER.left - GUTTER.right;
    const vertical = height - GUTTER.top - GUTTER.bottom;
    const observed = series.filter(Number.isFinite);
    const min = Math.min(0, ...observed);
    const max = Math.max(0, ...observed);
    const span = max - min || 1;
    const y = value => GUTTER.top + vertical * (1 - (value - min) / span);
    const x = i => GUTTER.left + horizontal * (i + .5) / series.length;
    ctx.font = '11px system-ui, sans-serif';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'right';
    for (let step = 0; step <= 4; step++) {
      const value = min + span * step / 4;
      const yLine = y(value);
      ctx.fillStyle = '#52617a';
      ctx.fillText(tag(value), GUTTER.left - 7, yLine, GUTTER.left - 10);
      ctx.strokeStyle = value === 0 ? '#c5d2e9' : '#e0e8f6';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(GUTTER.left, yLine);
      ctx.lineTo(width - GUTTER.right, yLine);
      ctx.stroke();
    }
    ctx.fillStyle = '#52617a';
    for (const [position, label, alignment] of [[0, '−200 ms', 'left'], [.5, '−100 ms', 'center'], [1, '0 ms', 'right']]) {
      ctx.textAlign = alignment;
      ctx.fillText(label, GUTTER.left + horizontal * position, height - 13);
    }
    ctx.strokeStyle = '#315bc4';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    let continuing = false;
    series.forEach((value, i) => {
      if (!Number.isFinite(value)) {
        continuing = false;
        return;
      }
      if (continuing) ctx.lineTo(x(i), y(value));
      else ctx.moveTo(x(i), y(value));
      continuing = true;
    });
    ctx.stroke();
    ctx.fillStyle = '#315bc4';
    series.forEach((value, i) => {
      if (!Number.isFinite(value)) return;
      ctx.beginPath();
      ctx.arc(x(i), y(value), 3.4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function binAt(canvas, pointerX) {
    const extent = canvas.clientWidth - GUTTER.left - GUTTER.right;
    return Math.max(0, Math.min(9, Math.floor(10 * (pointerX - GUTTER.left) / extent)));
  }

  return { draw, binAt };
})();
