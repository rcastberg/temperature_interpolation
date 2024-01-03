import numpy as np
import plotly.graph_objects as go
import yaml

with open('/home/recast/temperature_interpolation/floors.yaml', 'r') as f:
  floors = yaml.load(f , Loader=yaml.Loader)

class Points:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Temperature:
    def __init__(self, x, y, temp=None, name=None, ha_id=None):
        self.x = x
        self.y = y
        self.temp = temp
        self.name = name
        self.ha_id = ha_id

thermometers = [Temperature(t['x'], t['y'], name=t['name'], ha_id=t['ha_entity']) for t in floors['Basement']['thermometers']]
walls = [(Points(w[0][0], w[0][1]), Points(w[1][0], w[1][1])) for w in floors['Basement']['walls']]


if __name__ == '__main__':
    fig = go.Figure()
    for w in walls:
        fig.add_trace(go.Scatter(x=[w[0].y, w[1].y], y=[w[0].x, w[1].x], mode='lines', name='wall', line=dict(color='black')))
    for t in thermometers:
        fig.add_trace(go.Scatter(x=[t.y], y=[t.x], mode='markers', name=t.name, marker=dict(color='red', size=10)))
    fig.update_layout(
        title='Floorplan',
        xaxis_title='Y',
        yaxis_title='X')
    fig['layout']['yaxis']['scaleanchor'] = 'x'
    fig.show()
