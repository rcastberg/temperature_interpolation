"""
This script creates a heatmap for a given location.
The script reads the location from the url and creates a heatmap for that location.
Data is provided in the floors.yaml file.

Exmaple of floors.yaml:
Token: "ABCDEF..XYZ"
Step_size: 0.2
ha_url: "http://ha.local:8123/api/states/"
Floors:
  Basement:
    thermometers:
      - name: Thermo1
        x: 1
        y: 2
        ha_entity: sensor.Thermo1
      - name: Thermo2
        x: 2
        y: 3
        ha_entity: sensor.Thermo2
    walls:
      - [[0,0], [4,0]]
      - [[4,0], [4,5]]
      - [[4,5], [0,5]]
      - [[0,5], [0,0]]
"""

import json
import logging
from io import BytesIO
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

import numpy as np
import plotly.graph_objects as go
import yaml
from flask import Flask, send_file, url_for
from flask_caching import Cache
from requests import get


logging.basicConfig(level=logging.DEBUG)

np.seterr(all='raise')

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


class Points:
    """
    Coordinates for points
    Takes x and y coordinates as input
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Temperature:
    """
    Temperature Class for thermometers
    Takes x and y coordinates as input
    Takes name and home assistant id as input
    Takes the temparture as input as well.
    """
    def __init__(self, x, y, temp=0, name=None, ha_id=None):
        self.x = x
        self.y = y
        self.temp = temp
        self.name = name
        self.ha_id = ha_id


def ccw(A, B, C):
    """ Check if 2 lines intersect
    Line defined by AB and CD
    Source: https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    """
    return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)


def intersect_check(A, B, C, D):
    """ Check if 2 lines intersect
    Lines defined by AB and CD
    Source: https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    """
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def check_intersect(cur_pos, target_pos, walls):
    """ Check if 2 points intersect with a wall
    Takes 2 points and a wall as input
    cur_pos = current position
    target_pos = target position
    walls = wall to check
    returns True if intersect, False if not"""
    s1_x = cur_pos.x-target_pos.x
    s1_y = cur_pos.y-target_pos.y
    s2_x = walls[0].x-walls[1].x
    s2_y = walls[0].y-walls[1].y
    outcome = False

    s = float(-s1_y * (target_pos.x - walls[1].x) + s1_x * (target_pos.y - walls[1].y)) / (-s2_x * s1_y + s1_x * s2_y)
    t = float(s2_x * (target_pos.y - walls[1].y) - s2_y * (target_pos.x - walls[1].x)) / (-s2_x * s1_y + s1_x * s2_y)

    if (s >= 0 and s <= 1 and t >= 0 and t <= 1):
        outcome = True

    return outcome


def calculate_distance(cur_pos, target_pos):
    """ Calculate distance between 2 points using x and y coordinates
    Takes 2 points as input
    cur_pos = current position
    target_pos = target position
    returns distance between the 2 points
    """
    d = np.sqrt(pow((cur_pos.x - target_pos.x), 2) + pow((cur_pos.y - target_pos.y), 2))
    return d


def inverse_distance_weighting(distances, values, power):
    """ Calculate the interpolated value using Inverse Distance Weighting (IDW) formula
    Takes distances, values and power as input
    distances = distances between known values and unknown value
    values = known values
    power = power to use in IDW formula
    returns interpolated value
    Source : https://pareekshithkatti.medium.com/inverse-distance-weighting-interpolation-in-python-68351fb612d2
    """
    # Calculate the weighted sum of known values based on distances
    distances = distances + 1e-3  # ensure no zero distance
    numerator = np.sum(values / (distances ** power))

    # Calculate the sum of weights (inverse of distances)
    weights = np.sum(1 / (distances ** power))

    # Calculate the interpolated value using Inverse Distance Weighting (IDW) formula
    interpolated_value = numerator / weights

    return interpolated_value


def check_inwall(i, x=None, y=None, thermometers=None, walls=None):
    """Claculate the interpolated value for a all y coordinates for a given x coordinate
    Takes x coordinate as input
    i = x coordinate
    returns a list of interpolated values for all y coordinates for a given x coordinate"
    """
    grid = np.empty(len(y))
    grid[:] = np.nan
    for j, yj in enumerate(y):
        in_wall = False
        for w in walls:
            #  Check if points are inside wall bounds.
            if (x[i] >= min(w[0].x, w[1].x)) and (yj >= min(w[0].y, w[1].y)) and \
               (x[i] <= max(w[0].x, w[1].x)) and (yj <= max(w[0].y, w[1].y)):
                grid[j] = np.nan
                in_wall = True
                break
        if not in_wall:
            dists = np.zeros(len(thermometers))
            intersect = [False]*len(thermometers)
            for t, thermometer in enumerate(thermometers):
                if (abs(x[i] - thermometer.x) < 0.0001) and (abs(yj - thermometer.y) < 0.0001):
                    # Is this point the thermometer
                    dists = np.zeros(len(thermometers))
                    intersect = [True]*len(thermometers)
                    intersect[t] = False
                    break
                else:
                    for w in walls:
                        if intersect_check(Points(x[i], yj), thermometer, w[0], w[1]):
                            intersect[t] = True
                dists[t] = calculate_distance(Points(x[i], yj), thermometer)
            intersect_not = [not i for i in intersect]

            temp = 0
            if sum(intersect_not) >= 1:
                temp = inverse_distance_weighting(dists[intersect_not],
                                                  np.array([t.temp for t in thermometers])[intersect_not], 2)
            else:
                temp = np.nan  # thermometers[intersect_not][0].temp
            grid[j] = temp
        else:
            grid[j] = np.nan
    return (i, grid)


def create_heatmap(step_size=0.1, thermometers=None, walls=None):
    """Create a heatmap
    Takes step_size as input
    step_size = step size to use in heatmap
    returns a heatmap figure
    """
    xmax = max(p.x for w in walls for p in w) + step_size
    ymax = max(p.y for w in walls for p in w) + step_size
    x = np.arange(0, xmax, step_size)
    y = np.arange(0, ymax, step_size)

    grid = np.empty([len(x), len(y)])
    grid[:] = np.nan

    i = range(len(x))

    logging.debug('Checking inwall')
    check_inwall_partial = partial(check_inwall, x=x, y=y, thermometers=thermometers, walls=walls)
    with ThreadPool(80) as pool:
        results = pool.map(check_inwall_partial, i, chunksize=1)
    pool.close()
    pool.join()
    logging.debug('Inwall checked')
    res = []
    res.append(results)
    for r in res[0]:
        grid[r[0]] = r[1]

    min_temp = min([t.temp for t in thermometers])
    max_temp = max([t.temp for t in thermometers])
    fig = go.Figure(data=go.Heatmap(x=x, y=y, z=grid, zmin=min_temp, zmax=max_temp))
    for w in walls:
        fig.add_trace(go.Scatter(x=[w[0].y+step_size, w[1].y+step_size], y=[w[0].x, w[1].x], mode='lines',
                                 line=dict(color='black')))
    for t in thermometers:
        fig.add_trace(go.Scatter(x=[t.y+step_size], y=[t.x], mode='markers+text', name=t.name,
                                 marker=dict(color='red', size=10), textposition='top right',
                                 textfont=dict(color='#000000'), textfont_size=16, text=t.temp))
    fig.update_layout(
        title='Heatmap',
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        xaxis_showticklabels=False,
        yaxis_showticklabels=False,
        xaxis_zeroline=False,
        yaxis_zeroline=False,
    )
    fig.update_layout(showlegend=False)
    fig['layout']['yaxis']['scaleanchor'] = 'x'
    fig.update_xaxes(range=[0, xmax])
    # fig.show()
    figdata = BytesIO()
    fig.write_image(figdata, format='jpg')
    return figdata


def read_temps(thermometers, token='', ha_url=None):
    """Read temperatures from Home Assistant
    Takes a list of thermometers as input
    thermometers = list of thermometers
    token = Home Assistant token
    base_url = Home Assistant url
    returns a list of thermometers with updated temperatures
    """
    headers = {
            "Authorization": "Bearer " + token,
            "content-type": "application/json",
        }
    for t in thermometers:
        url = ha_url + t.ha_id
        response = get(url, headers=headers, timeout=10)
        reading = json.loads(response.text)
        t.temp = float(reading["state"])
    return thermometers


@app.route("/<location>")
@cache.cached(timeout=300)
def make_temp_plot(location=None):
    """
    Flask server to create a heatmap for a given location
    Takes location as input
    location = location to create heatmap for
    returns a heatmap figure
    """
    location, extension = location.split('.')
    logging.info('Creating heatmap for location: %s', location)
    with open('/config/floors.yaml', 'r', encoding='utf8') as f:
        floors = yaml.load(f, Loader=yaml.Loader)
    thermometers = [Temperature(t['x'], t['y'], name=t['name'], ha_id=t['ha_entity'])
                    for t in floors['Floors'][location]['thermometers']]
    logging.debug('Reading temperatures')
    ha_url = floors['ha_url']
    thermometers = read_temps(thermometers, token=floors['Token'], ha_url=ha_url)
    logging.debug('Temperatures read')
    walls = [(Points(w[0][0], w[0][1]), Points(w[1][0], w[1][1])) for w in floors['Floors'][location]['walls']]
    step_size = floors['Step_size']
    logging.debug('Heatmap settings for location: %s', location)
    logging.debug('Step size: %s', str(step_size))
    image = create_heatmap(step_size=step_size, thermometers=thermometers, walls=walls)
    image.seek(0)
    logging.debug('Heatmap made')
    return send_file(image, download_name=location + '.' + extension, mimetype='image/' + extension)


# The code below lets the Flask server respond to browser requests for a favicon
@app.route("/favicon.ico")
def favicon():
    """
    Flask server to create a dummy favicon
    """
    return url_for('static', filename='data:,')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
