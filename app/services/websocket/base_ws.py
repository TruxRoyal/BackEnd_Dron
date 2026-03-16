from flask import request
from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio


@socketio.on('connect')
def handle_connect(auth):
    print(f"🌐 Cliente conectado: {request.sid}")

    # Si el dron ya estaba conectado de una sesión anterior,
    # verificar que sigue vivo antes de reportarlo como conectado.
    # Evita el caso donde self.connected=True pero el dron se reinició.
    if drone_service.base.connected:
        alive = drone_service.base.is_alive()
        if not alive:
            print("⚠️  Dron marcado como conectado pero no responde — reconectando…")
            drone_service.reset()  # para stream + limpia base

    drone_connected = drone_service.base.connect()

    emit('drone_status', {
        "message": "Conexión establecida",
        "drone_connected": drone_connected,
        "battery": drone_service.stats.get_battery() if drone_connected else None
    })


@socketio.on('disconnect')
def handle_disconnect():
    print(f"🔌 Cliente desconectado: {request.sid}")


@socketio.on('reset')
def handle_reset(data=None):
    print("♻️ Reset solicitado")
    drone_service.reset()  # para stream + limpia base
    connected = drone_service.base.connect()
    emit('drone_response', {
        "action": "reset",
        "status": connected
    })