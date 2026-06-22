'use strict';

class MinHeap {
  constructor() { this._h = []; }
  get size() { return this._h.length; }
  push(item) {
    this._h.push(item);
    let i = this._h.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this._h[p][0] <= this._h[i][0]) break;
      [this._h[p], this._h[i]] = [this._h[i], this._h[p]];
      i = p;
    }
  }
  pop() {
    const top = this._h[0];
    const last = this._h.pop();
    if (this._h.length > 0) {
      this._h[0] = last;
      let i = 0;
      while (true) {
        let m = i;
        const l = 2 * i + 1, r = 2 * i + 2;
        if (l < this._h.length && this._h[l][0] < this._h[m][0]) m = l;
        if (r < this._h.length && this._h[r][0] < this._h[m][0]) m = r;
        if (m === i) break;
        [this._h[m], this._h[i]] = [this._h[i], this._h[m]];
        i = m;
      }
    }
    return top;
  }
}

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
    this._therms = config.thermometers.map(t => ({
      x: t.x, y: t.y, name: t.name, entity: t.entity, temp: null,
    }));
    this._walls = config.walls.map(w => [
      { x: w[0][0], y: w[0][1] },
      { x: w[1][0], y: w[1][1] },
    ]);
    const xmax0 = Math.max(...this._walls.flatMap(w => [w[0].x, w[1].x]));
    const ymax0 = Math.max(...this._walls.flatMap(w => [w[0].y, w[1].y]));
    // Clamp step so total grid cells stay under 40 000, regardless of unit system
    const minStep = Math.sqrt((xmax0 * ymax0) / 40000);
    this._stepSize = Math.max(minStep, config.step_size ?? minStep * 2);
    this._xmax = xmax0 + this._stepSize;
    this._ymax = ymax0 + this._stepSize;

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

  // Dijkstra shortest-path distance from one sensor to every reachable grid cell.
  // Edges that cross a wall segment are impassable, so the path naturally routes
  // around walls. Cells inside a wall bounding box (inWall) are also skipped.
  _dijkstra(sensor, xs, ys, inWall) {
    const nx = xs.length, ny = ys.length;
    const dist = Array.from({ length: nx }, () => new Float32Array(ny).fill(Infinity));

    let si = Math.round((sensor.x - xs[0]) / this._stepSize);
    let sj = Math.round((sensor.y - ys[0]) / this._stepSize);
    si = Math.min(Math.max(si, 0), nx - 1);
    sj = Math.min(Math.max(sj, 0), ny - 1);
    dist[si][sj] = 0;

    const heap = new MinHeap();
    heap.push([0, si, sj]);

    const dirs = [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];

    while (heap.size > 0) {
      const [d, i, j] = heap.pop();
      if (d > dist[i][j]) continue; // stale heap entry

      for (const [di, dj] of dirs) {
        const ni = i + di, nj = j + dj;
        if (ni < 0 || ni >= nx || nj < 0 || nj >= ny) continue;
        if (inWall[ni][nj]) continue;

        // Reject edges whose midpoint crosses a wall segment
        const p = { x: xs[i],  y: ys[j]  };
        const q = { x: xs[ni], y: ys[nj] };
        let blocked = false;
        for (const w of this._walls) {
          if (this._intersects(p, q, w[0], w[1])) { blocked = true; break; }
        }
        if (blocked) continue;

        const nd = d + Math.hypot(xs[ni] - xs[i], ys[nj] - ys[j]);
        if (nd < dist[ni][nj]) {
          dist[ni][nj] = nd;
          heap.push([nd, ni, nj]);
        }
      }
    }

    return dist;
  }

  // Separable Gaussian blur applied in-place. NaN cells are excluded from
  // kernel sums, so the blur does not bleed across wall boundaries.
  _gaussianBlur(grid, nx, ny, sigma) {
    const radius = Math.ceil(sigma * 2);
    const kernel = [];
    let ksum = 0;
    for (let k = -radius; k <= radius; k++) {
      const v = Math.exp(-(k * k) / (2 * sigma * sigma));
      kernel.push(v);
      ksum += v;
    }
    for (let k = 0; k < kernel.length; k++) kernel[k] /= ksum;

    // Horizontal pass (along y axis)
    const tmp = Array.from({ length: nx }, () => new Float32Array(ny).fill(NaN));
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < ny; j++) {
        if (isNaN(grid[i][j])) continue;
        let num = 0, den = 0;
        for (let k = -radius; k <= radius; k++) {
          const nj = j + k;
          if (nj >= 0 && nj < ny && !isNaN(grid[i][nj])) {
            num += grid[i][nj] * kernel[k + radius];
            den += kernel[k + radius];
          }
        }
        if (den > 0) tmp[i][j] = num / den;
      }
    }

    // Vertical pass (along x axis)
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < ny; j++) {
        if (isNaN(tmp[i][j])) continue;
        let num = 0, den = 0;
        for (let k = -radius; k <= radius; k++) {
          const ni = i + k;
          if (ni >= 0 && ni < nx && !isNaN(tmp[ni][j])) {
            num += tmp[ni][j] * kernel[k + radius];
            den += kernel[k + radius];
          }
        }
        if (den > 0) grid[i][j] = num / den;
      }
    }
  }

  _computeGrid() {
    const { _stepSize: step, _therms: therms, _walls: walls, _xmax: xmax, _ymax: ymax } = this;
    const xs = [], ys = [];
    for (let v = 0; v < xmax; v += step) xs.push(v);
    for (let v = 0; v < ymax; v += step) ys.push(v);
    const nx = xs.length, ny = ys.length;

    // Precompute which cells fall inside a wall segment's bounding box
    const inWall = Array.from({ length: nx }, () => new Uint8Array(ny));
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < ny; j++) {
        for (const w of walls) {
          if (xs[i] >= Math.min(w[0].x, w[1].x) && xs[i] <= Math.max(w[0].x, w[1].x) &&
              ys[j] >= Math.min(w[0].y, w[1].y) && ys[j] <= Math.max(w[0].y, w[1].y)) {
            inWall[i][j] = 1; break;
          }
        }
      }
    }

    const valid = therms.filter(t => t.temp !== null);
    const grid = Array.from({ length: nx }, () => new Float32Array(ny).fill(NaN));

    if (valid.length > 0) {
      // Dijkstra from each sensor — gives true path distance routing around walls
      const pathDists = valid.map(t => this._dijkstra(t, xs, ys, inWall));

      // IDW over path distances (sensors behind sealed walls have Infinity distance
      // and are naturally excluded; sensors in adjacent rooms contribute via the
      // longer path, giving realistic heat permeability behaviour)
      for (let i = 0; i < nx; i++) {
        for (let j = 0; j < ny; j++) {
          if (inWall[i][j]) continue;
          let num = 0, den = 0;
          for (let k = 0; k < valid.length; k++) {
            const d = pathDists[k][i][j];
            if (!isFinite(d)) continue;
            const w = 1 / ((d + 1e-3) ** 2);
            num += valid[k].temp * w;
            den += w;
          }
          if (den > 0) grid[i][j] = num / den;
        }
      }

      // Gaussian blur smooths the grid-resolution staircase artifacts
      this._gaussianBlur(grid, nx, ny, 1.5);
    }

    this._grid = grid;
    this._xs = xs;
    this._ys = ys;

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

    // Canvas x-axis = floor y-axis, canvas y-axis = floor x-axis (inverted to match Plotly)
    const cssW = canvas.clientWidth || 400;
    const scale = cssW / this._ymax;
    canvas.width = cssW;
    canvas.height = Math.round(this._xmax * scale);
    this._scale = scale;

    // cy flips the y-axis so floor x=0 sits at the canvas bottom
    const cx = fy => fy * scale;
    const cy = fx => canvas.height - fx * scale;
    const cellW = step * scale + 1; // +1 closes sub-pixel gaps between cells
    const cellH = step * scale + 1;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Heatmap cells — fillRect origin is top-left, so use cy(xs[i] + step) after flipping
    for (let i = 0; i < xs.length; i++) {
      for (let j = 0; j < ys.length; j++) {
        const v = grid[i][j];
        if (isNaN(v)) continue;
        ctx.fillStyle = this._color(v);
        ctx.fillRect(cx(ys[j]), cy(xs[i] + step), cellW, cellH);
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
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * (this._canvas.height / rect.height);

    let nearest = null, bestD = Infinity;
    for (const t of this._therms) {
      const d = Math.hypot(t.y * this._scale - mx, (this._canvas.height - t.x * this._scale) - my);
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
