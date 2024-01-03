from multiprocessing import cpu_count
from multiprocessing.dummy import Pool as ThreadPool

import numpy as np
import plotly.graph_objects as go
np.seterr(all='raise')

class Points:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Temperature:
    def __init__(self, x, y, temp, name=None):
        self.x = x
        self.y = y
        self.temp = temp
        self.name = name

from first_floor import thermometers, walls

def ccw(A, B, C):
    return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)


def intersect_check(A, B, C, D):
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def check_intersect(cur_pos, target_pos, walls):
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
    d = np.sqrt(pow((cur_pos.x - target_pos.x), 2) + pow((cur_pos.y - target_pos.y), 2))
    return d

def inverse_distance_weighting(distances, values, power):
    # Calculate the weighted sum of known values based on distances
    distances = distances + 1e-3 # ensure no zero distance
    numerator = np.sum(values / (distances ** power))

    # Calculate the sum of weights (inverse of distances)
    weights = np.sum(1 / (distances ** power))
    
    # Calculate the interpolated value using Inverse Distance Weighting (IDW) formula
    interpolated_value = numerator / weights
    
    return interpolated_value


def check_inwall(i):
    global thermometers
    global walls
    global x
    global y
    grid = np.empty(len(y))
    grid[:] = np.nan
    for j in range(len(y)):
        in_Wall = False
        for w in walls:
            #  Check if points are inside wall bounds.
            if (x[i] >= min(w[0].x, w[1].x)) and (y[j] >= min(w[0].y, w[1].y)) and \
               (x[i] <= max(w[0].x, w[1].x)) and (y[j] <= max(w[0].y, w[1].y)):
                grid[j] = np.nan
                in_Wall = True
                break
        if not in_Wall:
            dists = np.zeros(len(thermometers))
            intersect = [False]*len(thermometers)
            for t in range(len(thermometers)):
                if (abs(x[i] - thermometers[t].x) < 0.0001) and (abs(y[j] - thermometers[t].y) < 0.0001):
                    # Is this point the thermometer
                    dists = np.zeros(len(thermometers))
                    intersect = [True]*len(thermometers)
                    intersect[t] = False
                    break
                else:
                    for w in walls:
                        if intersect_check(Points(x[i], y[j]), thermometers[t], w[0], w[1]):
                            intersect[t] = True
                dists[t] = calculate_distance(Points(x[i], y[j]), thermometers[t])
            intersect_not = [not i for i in intersect]

            temp = 0
            if sum(intersect_not) >= 1:
                temp = inverse_distance_weighting(dists[intersect_not], np.array([t.temp for t in thermometers])[intersect_not], 2)
            else:
                temp = np.nan  # thermometers[intersect_not][0].temp
            grid[j] = temp
        else:
            grid[j] = np.nan
    return (i, grid)


if __name__ == '__main__':

    step_size = 0.1
    xmax = max([p.x  for w in walls for p in w]) + step_size
    ymax = max([p.y  for w in walls for p in w]) + step_size
    x = np.arange(0, xmax, step_size)
    y = np.arange(0, ymax, step_size)

    grid = np.empty([len(x), len(y)])
    grid[:] = np.nan

    i = range(len(x))

    #for i in range(len(x)):
    #    grid[i] = check_inwall(i)[1]

    with ThreadPool(80) as pool:
        results = pool.map(check_inwall, i, chunksize=1)
    pool.close()
    pool.join()
    res = []
    res.append(results)
    for r in res[0]:
        grid[r[0]] = r[1]

    fig = go.Figure(data=go.Heatmap(x=x, y=y, z=grid, zmin=15, zmax=30))
    for w in walls:
        fig.add_trace(go.Scatter(x=[w[0].y, w[1].y], y=[w[0].x, w[1].x], mode='lines', line=dict(color='black')))
    for t in thermometers:
        fig.add_trace(go.Scatter(x=[t.y], y=[t.x], mode='markers', name=t.name, marker=dict(color='red', size=10)))
    fig.update_layout(
        title='Heatmap',
        xaxis_title='Y',
        yaxis_title='X'
    )
    fig.update_layout(showlegend=False)
    fig['layout']['yaxis']['scaleanchor'] = 'x'
    fig.show()
