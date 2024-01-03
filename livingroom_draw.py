import numpy as np
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
    Temperature(1, 1, 23.7, 'Living Room Smoke'),
    Temperature(4.40, 1, 23, 'Living Room Window'),
    Temperature(3.5, 0.10, 18.7, 'Living Room Door'),
    Temperature(0.5, 4.5, 23.9, 'Living Room Smoke'),
    Temperature(4.4, 3.1, 24.9, 'Living room Heatpump')
    ])

walls = [(Points(0, 0), Points(4.53, 0)),
            (Points(4.53, 0), Points(4.53, 7.04)),
            (Points(4.53, 7.04), Points(1.25, 7.04)),
            (Points(1.25, 7.04), Points(1.25, 4.63)),
            (Points(1.25, 4.63), Points(0, 4.63)),
            (Points(0, 4.63), Points(0, 0))]
