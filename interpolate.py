from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import cpu_count
from tqdm import tqdm
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import *


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
            total_d = sum(dists[intersect_not])

            temp = 0
            if sum(intersect_not) > 1:
                for t in range(len(thermometers)):
                    if intersect_not[t]:
                        temp += thermometers[t].temp * (dists[t]/total_d)
            else:
                temp = np.nan  # thermometers[intersect_not][0].temp
            grid[j] = temp
    return (i, grid)


if __name__ == '__main__':

    thermometers = np.array([
        Temperature(1, 1, 23.7, 'Living Room Smoke'),
        Temperature(4.40, 1, 23, 'Living Room Window'),
        Temperature(3.53, 0.50, 18.7, 'Living Room Door'),
        Temperature(0.5, 4.5, 23.9, 'Living Room Smoke'),
        Temperature(4.13, 3.09, 24.9, 'Living room Heatpump')
        ])

    walls = [(Points(0, 0), Points(4.53, 0)),
             (Points(4.53, 0), Points(4.53, 7.04)),
             (Points(4.53, 7.04), Points(1.25, 7.04)),
             (Points(1.25, 7.04), Points(1.25, 4.63)),
             (Points(1.25, 4.63), Points(0, 4.63)),
             (Points(0, 4.63), Points(0, 0))]

    # target grid to interpolate to
    x = np.arange(0, 4.6, 0.5)
    y = np.arange(0, 7.1, 0.5)

    grid = np.empty([len(x), len(y)])
    grid[:] = np.nan

    i = range(len(x))
    pool = ThreadPool(cpu_count())

    check_inwall(1)
    with ThreadPool(20) as pool:
        results = pool.map(check_inwall, i, chunksize=20)
    pool.close()
    pool.join()
    res = []
    res.append(results)
    for r in res[0]:
        grid[r[0]] = r[1]
    fig = go.Figure(data=go.Heatmap(x=x, y=y, z=grid, zmin=18, zmax=26))
    fig.update_layout(
        title='Heatmap',
        xaxis_title='Y',
        yaxis_title='X')
    fig['layout']['yaxis']['scaleanchor'] = 'x'
    fig.show()
