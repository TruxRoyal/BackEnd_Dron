from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio

def emit_drone_status():
    status = drone_service.get_status()
    socketio.emit('drone_status', status)