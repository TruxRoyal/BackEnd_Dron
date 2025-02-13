from flask import Blueprint, jsonify, request
from app.services.drone_service import DroneService

drone_bp = Blueprint('drone', __name__)
drone_service = DroneService()

@drone_bp.route('/takeoff', methods=['POST'])
def takeoff():
    drone_service.takeoff()
    return jsonify({"message": "Drone has taken off"})

@drone_bp.route('/land', methods=['POST'])
def land():
    drone_service.land()
    return jsonify({"message": "Drone has landed"})

@drone_bp.route('/move', methods=['POST'])
def move():
    data = request.json
    direction = data.get("direction")
    distance = data.get("distance")
    drone_service.move(direction, distance)
    return jsonify({"message": f"Drone moved {direction} {distance} cm"})