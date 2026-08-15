from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio

@socketio.on('battery')
def handle_battery():
    battery = drone_service.stats.get_battery()
    emit('drone_battery', {"battery": battery})
