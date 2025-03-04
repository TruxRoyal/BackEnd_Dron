from flask import Blueprint, jsonify, request, send_file
from app.services.drone_service import drone_service

drone_bp = Blueprint('drone', __name__)

@drone_bp.route('/battery', methods=['GET'])
def get_battery():
    battery_level = drone_service.get_battery()
    if battery_level is not None:
        return jsonify({"battery": battery_level})
    return jsonify({"error": "No se pudo obtener la batería"}), 500

@drone_bp.route('/takeoff', methods=['POST'])
def takeoff():
    if drone_service.takeoff():
        return jsonify({"message": "Dron despegando"})
    return jsonify({"error": "No se pudo despegar el dron"}), 500

@drone_bp.route('/land', methods=['POST'])
def land():
    if drone_service.land():
        return jsonify({"message": "Dron aterrizando"})
    return jsonify({"error": "No se pudo aterrizar el dron"}), 500

@drone_bp.route('/move', methods=['POST'])
def move():
    data = request.json
    direction = data.get("direction")
    distance = data.get("distance")

    if not direction or not distance:
        return jsonify({"error": "Se requieren 'direction' y 'distance'"}), 400

    if drone_service.move(direction, distance):
        return jsonify({"message": f"Dron moviéndose {direction} {distance} cm"})
    return jsonify({"error": "No se pudo mover el dron"}), 500

@drone_bp.route('/rotate', methods=['POST'])
def rotate():
    data = request.json
    direction = data.get("direction")
    degrees = data.get("degrees")

    if not direction or not degrees:
        return jsonify({"error": "Se requieren 'direction' y 'degrees'"}), 400

    if drone_service.rotate(direction, degrees):
        return jsonify({"message": f"Dron rotando {direction} {degrees} grados"})
    return jsonify({"error": "No se pudo rotar el dron"}), 500

@drone_bp.route('/start_video_stream', methods=['POST'])
def start_video_stream():
    if drone_service.start_video_stream():
        return jsonify({"message": "Transmisión de video iniciada"})
    return jsonify({"error": "No se pudo iniciar la transmisión de video"}), 500

@drone_bp.route('/take_photo', methods=['POST'])
def take_photo():
    filename = "photo.jpg"
    if drone_service.take_photo(filename):
        return send_file(filename, mimetype='image/jpeg')
    return jsonify({"error": "No se pudo capturar la foto"}), 500