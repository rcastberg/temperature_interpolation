from flask import Flask, jsonify

app = Flask(__name__)

# Mock temperature sensor data
sensor_data = {
    "sensor.Thermo1": {"state": "21.5", "attributes": {"unit_of_measurement": "°C"}},
    "sensor.Thermo2": {"state": "22.3", "attributes": {"unit_of_measurement": "°C"}},
    # Add more sensors as needed
}

@app.route("/api/states/<entity_id>", methods=["GET"])
def get_entity_state(entity_id):
    if entity_id in sensor_data:
        return jsonify(sensor_data[entity_id])
    return jsonify({"state": "unknown", "attributes": {}}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8123)