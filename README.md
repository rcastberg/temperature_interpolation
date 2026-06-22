# temperature-heatmap-card

A Home Assistant Lovelace custom card that renders a temperature heatmap for a floor plan using inverse distance weighting (IDW) interpolation. Walls block heat propagation between rooms. Runs entirely in the browser — no Docker, no server, no extra dependencies.

![Example heatmap](example.png)

## Installation

1. Copy `temperature-heatmap-card.js` to your HA config directory:
   ```
   /config/www/temperature-heatmap-card.js
   ```

2. In Home Assistant go to **Settings → Dashboards → Resources** and add:
   - URL: `/local/temperature-heatmap-card.js`
   - Type: **JavaScript module**

3. Add the card to any dashboard (see configuration below).

## Card configuration

Each card renders one floor. Add multiple cards for multiple floors.

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
  - [[0,0],    [10.77,0]]
  - [[10.77,0], [10.77,7.05]]
  - [[10.77,7.05], [0,7.05]]
  - [[0,7.05], [0,0]]
```

### Options

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `thermometers` | yes | — | List of sensors with their floor coordinates |
| `walls` | yes | — | List of wall segments as `[[x1,y1],[x2,y2]]` pairs (metres) |
| `title` | no | *(none)* | Card title shown above the map |
| `step_size` | no | `0.2` | Grid resolution in metres. Smaller = sharper but slower. |

### Thermometer fields

| Key | Description |
|-----|-------------|
| `name` | Label shown on hover and next to the dot on the map |
| `x` | Floor x coordinate in metres |
| `y` | Floor y coordinate in metres |
| `entity` | HA entity ID for the temperature sensor |

## How it works

- Coordinates use metres, with `(0,0)` at the top-left corner of the floor plan.
- The canvas x-axis maps to the floor y-axis; canvas y-axis maps to floor x-axis (i.e. the plan is drawn with x going downward).
- Walls are line segments. The card checks line-of-sight from each grid cell to each sensor; sensors behind a wall do not influence the other side.
- IDW with power 2 is used to blend temperatures from all visible sensors.
- The card re-renders automatically whenever any sensor state changes in HA.

## Previous Docker version

The original Flask/Docker implementation is preserved on the [`docker_version`](../../tree/docker_version) branch.
