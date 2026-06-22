# temperature-heatmap-card

A Home Assistant Lovelace custom card that renders a temperature heatmap for a floor plan. Uses Dijkstra shortest-path routing around walls and inverse distance weighting (IDW) to produce physically realistic heat gradients across rooms. Runs entirely in the browser — no Docker, no server, no extra dependencies.

![Example heatmap](example.png)

## Installation

### Via HACS (recommended)

1. In HA go to **HACS → Frontend → Explore & download repositories**
2. Search for **Temperature Heatmap Card** and download it
3. Hard-refresh your browser (Ctrl+Shift+R / Cmd+Shift+R)

### Manual

1. Copy `temperature-heatmap-card.js` to `/config/www/temperature-heatmap-card.js`
2. Go to **Settings → Dashboards → Resources** and add:
   - URL: `/local/temperature-heatmap-card.js`
   - Type: **JavaScript module**
3. Hard-refresh your browser

## Card configuration

Each card renders one floor. Add one card per floor on any dashboard.

```yaml
type: custom:temperature-heatmap-card
title: Basement
step_size: 0.2
thermometers:
  - name: Basement stairs
    x: 1.5
    y: 6.45
    entity: sensor.cellarstairs_smoke_homely_temperature
  - name: Airthings
    x: 6.3
    y: 3.0
    entity: sensor.airthings_wave_170641_temperature
walls:
  - [[0,0],     [10.77,0]]
  - [[10.77,0], [10.77,7.05]]
  - [[10.77,7.05], [0,7.05]]
  - [[0,7.05],  [0,0]]
  - [[2.75,0],  [2.75,3.03]]
```

### Options

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `thermometers` | yes | — | List of sensors with floor coordinates and HA entity IDs |
| `walls` | yes | — | Wall segments as `[[x1,y1],[x2,y2]]` pairs |
| `title` | no | *(none)* | Card title shown above the map |
| `step_size` | no | auto | Grid resolution. Smaller = sharper, slower. Clamped automatically so the grid never exceeds ~40 000 cells. |

### Thermometer fields

| Key | Description |
|-----|-------------|
| `name` | Label shown in the hover tooltip and next to the sensor dot |
| `x` | Floor x coordinate |
| `y` | Floor y coordinate |
| `entity` | Home Assistant entity ID for the temperature sensor |

Coordinates can be in any consistent unit (metres, feet, etc.) — the card adapts automatically.

## How it works

**Coordinate system** — `(0,0)` is the top-left corner of the floor plan. `x` increases downward, `y` increases to the right.

**Dijkstra path distance** — for each sensor the card runs Dijkstra's algorithm on the grid to find the true shortest walkable path to every cell. Paths cannot cross wall segments, so sensors in an adjacent room contribute heat via the longer route around the wall rather than being cut off entirely. Cells with no reachable sensor (a sealed room with no sensor) are left blank.

**IDW interpolation** — each grid cell's temperature is a weighted average of all reachable sensors, with weight = 1 / distance². Sensors far away (long path) have low weight; the nearest sensor dominates.

**Gaussian blur** — a separable Gaussian blur (σ = 1.5 grid cells) is applied after IDW to smooth the staircase artefacts that come from finite grid resolution. NaN wall cells are excluded from the kernel, so colours do not bleed across walls.

**Live updates** — the card re-renders automatically whenever any sensor state changes in HA.

## Migrating from the Docker version

The old `floors.yaml` format maps directly to card config. The only field change is `ha_entity` → `entity`. The fields `Token`, `ha_url`, and `cpu_cores` are no longer needed and can be removed.

The original Flask/Docker implementation is preserved on the [`docker_version`](../../tree/docker_version) branch.
