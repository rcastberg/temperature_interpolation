import numpy as np
import plotly.graph_objects as go

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

thermometers = np.array([
    Temperature(7.1, 1, 23.7, 'Living Room Smoke'),
    Temperature(6.2, 0.3, 20, 'Airthings'),
    Temperature(10.6, 1, 23, 'Living Room Window'),
    Temperature(10.0, 0.10, 18.7, 'Living Room Door'),
    Temperature(6.6, 4.3, 23.9, 'Living Room Motion'),
    Temperature(10.6, 3.1, 24.9, 'Living room Heatpump'),
    Temperature(5, 5.2, 20, 'Kitchen Heat'),
    Temperature(4.5, 3.02, 21, 'Dinging room heat'),
    Temperature(0.1, 0.1, 20, 'Dinging room Motion'),
    Temperature(0.1, 3.2, 2.9, 'Front door contact'),
    Temperature(1.5, 3.2, 11.56, 'Bathroom Heat'),
    Temperature(1.8, 6.7, 10.6, 'Basement stairs'),
    ])

floor_def = [
    # Outer walls
    ((0, 0), (10.63, 0)),
    ((10.63, 0), (10.63, 7.04)),
    ((10.63, 7.04), (0, 7.04)),
    ((0, 0), (0, 7.04)),
    # Inner walls
    ((6.10, 0), (6.10, 3.09)),
    ((7.35, 7.04), (7.35, 4.43)),
    ((7.35, 4.43), (6.0, 4.43)),
    ((5., 4.43), (3.9, 4.43)),
    ((3.9, 4.43), (3.9, 7.04)),
    ((3.9, 4.43), (3.1, 4.43)),
    ((3.1, 4.43), (2.6, 4.43)),  # Bathroom door
    ((2.6, 4.43), (1.2, 4.43)),
    ((2.2, 4.43), (2.2, 7.04)),
    ((1.2, 4.43), (1.2, 7.04)),
    ((0, 3.02), (3.47, 3.02)),
    ((3.47, 3.02), (3.47, 4.43))
]

walls = [(Points(w[0][0], w[0][1]), Points(w[1][0], w[1][1])) for w in floor_def]


if __name__ == '__main__':
    fig = go.Figure()
    for w in walls:
        fig.add_trace(go.Scatter(x=[w[0].y, w[1].y], y=[w[0].x, w[1].x], mode='lines', name='wall', line=dict(color='black')))
    for t in thermometers:
        fig.add_trace(go.Scatter(x=[t.y], y=[t.x], mode='markers', name=t.name, marker=dict(color='red', size=10)))
    fig.update_layout(
        title='Heatmap',
        xaxis_title='Y',
        yaxis_title='X')
    fig['layout']['yaxis']['scaleanchor'] = 'x'
    fig.show()