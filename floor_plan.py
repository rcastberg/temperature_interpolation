import plotly.graph_objects as go
import yaml
from interpolate import Points, Temperature


if __name__ == '__main__':
    floors = None
    for file in ['floors.yaml', '/config/floors.yaml']:
        print(f'Trying to read Config file: {file}')
        try:
            with open(file, 'r', encoding='utf8') as f:
                floors = yaml.load(f, Loader=yaml.Loader)
            break
        except OSError:
            print('Config File not found: {file}')
            continue
    if floors is None:
        print('Error reading floors.yaml')
        raise Exception('Error reading floors.yaml')
    for floor, floor_data in floors['Floors'].items():
        thermometers = [Temperature(t['x'], t['y'], name=t['name'], ha_id=t['ha_entity']) for t in floor_data['thermometers']]
        walls = [(Points(w[0][0], w[0][1]), Points(w[1][0], w[1][1])) for w in floor_data['walls']]

        fig = go.Figure()
        for w in walls:
            fig.add_trace(go.Scatter(x=[w[0].y, w[1].y], y=[w[0].x, w[1].x], mode='lines', name='wall', line=dict(color='black')))
        for t in thermometers:
            fig.add_trace(go.Scatter(x=[t.y], y=[t.x], mode='markers', name=t.name, marker=dict(color='red', size=10)))
        fig.update_layout(
            title=floor,
            xaxis_title='Y',
            yaxis_title='X')
        fig['layout']['yaxis']['scaleanchor'] = 'x'
        fig.show()
