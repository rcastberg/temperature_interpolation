'use strict';

class TemperatureHeatmapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._grid = null;
    this._renderPending = false;
  }

  setConfig(config) {
    if (!config.thermometers?.length || !config.walls?.length) {
      throw new Error('temperature-heatmap-card requires thermometers and walls');
    }
    this._config = config;
    this._stepSize = config.step_size ?? 0.2;
    this._therms = config.thermometers.map(t => ({
      x: t.x, y: t.y, name: t.name, entity: t.entity, temp: null,
    }));
    this._walls = config.walls.map(w => [
      { x: w[0][0], y: w[0][1] },
      { x: w[1][0], y: w[1][1] },
    ]);
    this._xmax = Math.max(...this._walls.flatMap(w => [w[0].x, w[1].x])) + this._stepSize;
    this._ymax = Math.max(...this._walls.flatMap(w => [w[0].y, w[1].y])) + this._stepSize;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          background: var(--card-background-color);
          border-radius: var(--ha-card-border-radius, 4px);
          box-shadow: var(--ha-card-box-shadow, none);
        }
        .header {
          padding: 16px 16px 4px;
          font-size: 1.1em;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .wrap { position: relative; padding: 8px; }
        canvas { display: block; width: 100%; }
        .tip {
          position: absolute;
          background: rgba(0,0,0,0.75);
          color: #fff;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 12px;
          white-space: nowrap;
          pointer-events: none;
          display: none;
        }
      </style>
      ${config.title ? `<div class="header">${config.title}</div>` : ''}
      <div class="wrap">
        <canvas></canvas>
        <div class="tip"></div>
      </div>
    `;

    this._canvas = this.shadowRoot.querySelector('canvas');
    this._ctx = this._canvas.getContext('2d');
    this._tip = this.shadowRoot.querySelector('.tip');

    const ro = new ResizeObserver(() => this._scheduleRender());
    ro.observe(this._canvas);

    this._canvas.addEventListener('mousemove', e => this._onHover(e));
    this._canvas.addEventListener('mouseleave', () => { this._tip.style.display = 'none'; });
  }

  set hass(hass) {
    let changed = !this._grid;
    for (const t of this._therms) {
      const s = hass.states[t.entity];
      const raw = s ? parseFloat(s.state) : null;
      const val = (raw === null || isNaN(raw)) ? null : raw;
      if (val !== t.temp) { t.temp = val; changed = true; }
    }
    if (changed) {
      this._computeGrid();
      this._scheduleRender();
    }
  }

  _scheduleRender() {
    if (this._renderPending) return;
    this._renderPending = true;
    requestAnimationFrame(() => { this._renderPending = false; this._draw(); });
  }

  // Segment intersection — port of check_intersect() from interpolate.py
  _intersects(p, q, r, s) {
    const s1x = p.x - q.x, s1y = p.y - q.y;
    const s2x = r.x - s.x, s2y = r.y - s.y;
    const d = -s2x * s1y + s1x * s2y;
    if (Math.abs(d) < 1e-10) return false;
    const si = (-s1y * (q.x - s.x) + s1x * (q.y - s.y)) / d;
    const ti = (s2x * (q.y - s.y) - s2y * (q.x - s.x)) / d;
    return si >= 0 && si <= 1 && ti >= 0 && ti <= 1;
  }

  // IDW grid computation — port of check_inwall() + inverse_distance_weighting() from interpolate.py
  _computeGrid() {
    const { _stepSize: step, _therms: therms, _walls: walls, _xmax: xmax, _ymax: ymax } = this;
    const xs = [], ys = [];
    for (let v = 0; v < xmax; v += step) xs.push(v);
    for (let v = 0; v < ymax; v += step) ys.push(v);

    const valid = therms.filter(t => t.temp !== null);
    const grid = Array.from({ length: xs.length }, () => new Float32Array(ys.length).fill(NaN));

    for (let i = 0; i < xs.length; i++) {
      const xi = xs[i];
      for (let j = 0; j < ys.length; j++) {
        const yj = ys[j];

        // Skip grid points inside a wall segment's bounding box
        let inWall = false;
        for (const w of walls) {
          if (xi >= Math.min(w[0].x, w[1].x) && xi <= Math.max(w[0].x, w[1].x) &&
              yj >= Math.min(w[0].y, w[1].y) && yj <= Math.max(w[0].y, w[1].y)) {
            inWall = true; break;
          }
        }
        if (inWall || valid.length === 0) continue;

        const pt = { x: xi, y: yj };
        let placed = false;
        const dists = [], vals = [], blocked = [];

        for (const t of valid) {
          // Grid point is exactly at this sensor — use its temp directly
          if (Math.abs(xi - t.x) < 0.0001 && Math.abs(yj - t.y) < 0.0001) {
            grid[i][j] = t.temp; placed = true; break;
          }
          let wallBlocked = false;
          for (const w of walls) {
            if (this._intersects(pt, t, w[0], w[1])) { wallBlocked = true; break; }
          }
          dists.push(Math.hypot(xi - t.x, yj - t.y));
          vals.push(t.temp);
          blocked.push(wallBlocked);
        }
        if (placed) continue;

        // IDW over unblocked sensors
        let num = 0, den = 0, count = 0;
        for (let k = 0; k < dists.length; k++) {
          if (blocked[k]) continue;
          const w = 1 / ((dists[k] + 1e-3) ** 2);
          num += vals[k] * w;
          den += w;
          count++;
        }
        if (count > 0) grid[i][j] = num / den;
      }
    }

    this._grid = grid;
    this._xs = xs;
    this._ys = ys;

    // Temperature range for colorscale
    const flat = [];
    for (const row of grid) for (const v of row) if (!isNaN(v)) flat.push(v);
    this._minT = flat.length ? Math.min(...flat) : 0;
    this._maxT = flat.length ? Math.max(...flat) : 1;
  }

  // Plasma colorscale
  _color(temp) {
    const t = Math.max(0, Math.min(1, (temp - this._minT) / ((this._maxT - this._minT) || 1)));
    const stops = [
      [0.00, [13,   8, 135]],
      [0.25, [126,  3, 168]],
      [0.50, [204, 71, 120]],
      [0.75, [248, 149,  64]],
      [1.00, [240, 249,  33]],
    ];
    let i = 0;
    while (i < stops.length - 2 && stops[i + 1][0] <= t) i++;
    const [t0, c0] = stops[i], [t1, c1] = stops[i + 1];
    const f = (t - t0) / (t1 - t0);
    return `rgb(${Math.round(c0[0] + f * (c1[0] - c0[0]))},` +
                `${Math.round(c0[1] + f * (c1[1] - c0[1]))},` +
                `${Math.round(c0[2] + f * (c1[2] - c0[2]))})`;
  }

  _draw() {
    const { _grid: grid, _xs: xs, _ys: ys, _walls: walls, _therms: therms, _stepSize: step } = this;
    if (!grid) return;

    const canvas = this._canvas;
    const ctx = this._ctx;

    // Canvas x-axis = floor y-axis, canvas y-axis = floor x-axis (preserves original orientation)
    const cssW = canvas.clientWidth || 400;
    const scale = cssW / this._ymax;
    canvas.width = cssW;
    canvas.height = Math.round(this._xmax * scale);
    this._scale = scale;

    // Floor coords → canvas pixels
    const cx = fy => fy * scale;  // floor y → canvas x
    const cy = fx => fx * scale;  // floor x → canvas y
    const cellW = step * scale + 1; // +1 closes sub-pixel gaps between cells
    const cellH = step * scale + 1;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Heatmap cells
    for (let i = 0; i < xs.length; i++) {
      for (let j = 0; j < ys.length; j++) {
        const v = grid[i][j];
        if (isNaN(v)) continue;
        ctx.fillStyle = this._color(v);
        ctx.fillRect(cx(ys[j]), cy(xs[i]), cellW, cellH);
      }
    }

    // Walls
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1.5, scale * 0.07);
    ctx.lineJoin = 'round';
    for (const w of walls) {
      ctx.beginPath();
      ctx.moveTo(cx(w[0].y), cy(w[0].x));
      ctx.lineTo(cx(w[1].y), cy(w[1].x));
      ctx.stroke();
    }

    // Sensor dots + temperature labels
    const fontSize = Math.max(11, scale * 0.28);
    ctx.font = `bold ${fontSize}px sans-serif`;
    for (const t of therms) {
      const px = cx(t.y), py = cy(t.x);
      ctx.beginPath();
      ctx.arc(px, py, 5, 0, 2 * Math.PI);
      ctx.fillStyle = 'red';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      if (t.temp !== null) {
        ctx.fillStyle = '#000';
        ctx.fillText(t.temp.toFixed(1), px + 8, py - 4);
      }
    }
  }

  _onHover(e) {
    if (!this._scale) return;
    const rect = this._canvas.getBoundingClientRect();
    const scaleX = this._canvas.width / rect.width;
    const scaleY = this._canvas.height / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * scaleY;

    let nearest = null, bestD = Infinity;
    for (const t of this._therms) {
      const d = Math.hypot(t.y * this._scale - mx, t.x * this._scale - my);
      if (d < bestD) { bestD = d; nearest = t; }
    }

    if (nearest && bestD < 20 * scaleX) {
      this._tip.style.display = 'block';
      this._tip.style.left = (e.offsetX + 14) + 'px';
      this._tip.style.top = (e.offsetY - 10) + 'px';
      this._tip.textContent = `${nearest.name}: ${nearest.temp?.toFixed(1) ?? 'N/A'} °C`;
    } else {
      this._tip.style.display = 'none';
    }
  }

  getCardSize() {
    if (!this._xmax || !this._ymax) return 4;
    return Math.ceil((this._xmax / this._ymax) * 4);
  }
}

customElements.define('temperature-heatmap-card', TemperatureHeatmapCard);
