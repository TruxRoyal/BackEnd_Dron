from flask import request
from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio

@socketio.on('connect')
def handle_connect(auth):
    print(f"Cliente conectado: {request.sid}")
    drone_connected = drone_service.base.connect()
    emit('drone_status', {
        "message": "Conexión establecida",
        "drone_connected": drone_connected,
        "battery": drone_service.stats.get_battery()
    })

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}")

@socketio.on("reset")
def handle_reset(data=None):
    print("♻️ Solicitud de reset recibida")
    drone_service.base.reset()
    connected = drone_service.base.connect()
    emit("drone_response", {
        "action": "reset",
        "status": connected
    })
