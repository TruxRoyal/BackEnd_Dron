from flask_socketio import SocketIO, emit
from flask import request
from app.services.drone_service import drone_service

socketio = SocketIO(cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    """Cuando un cliente se conecta, intentamos conectar el dron y enviamos el estado."""
    print(f"Cliente conectado: {request.sid}")
    drone_connected = drone_service.connect()
    battery = drone_service.get_battery() if drone_connected else "Desconocida"

    emit('drone_status', {
        "message": "Conexión establecida",
        "drone_connected": drone_connected,
        "battery": battery
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Cuando un cliente se desconecta."""
    print(f"Cliente desconectado: {request.sid}")

@socketio.on('takeoff')
def handle_takeoff(data=None):
    """Manejar despegue del dron."""
    success = drone_service.takeoff()
    emit('drone_response', {"action": "takeoff", "status": success}, broadcast=True)

@socketio.on('land')
def handle_land(data=None):
    """Manejar aterrizaje del dron."""
    success = drone_service.land()
    emit('drone_response', {"action": "land", "status": success}, broadcast=True)

@socketio.on('move')
def handle_move(data):
    """Manejar movimiento del dron."""
    direction = data.get("direction", "")
    distance = data.get("distance", 50)

    success = drone_service.move(direction, distance)
    emit('drone_response', {
        "action": "move",
        "direction": direction,
        "distance": distance,
        "status": success
    }, broadcast=True)

@socketio.on('rotate')
def handle_rotate(data):
    """Manejar rotación del dron."""
    direction = data.get("direction", "")
    degrees = data.get("degrees", 90)

    success = drone_service.rotate(direction, degrees)
    emit('drone_response', {
        "action": "rotate",
        "direction": direction,
        "degrees": degrees,
        "status": success
    }, broadcast=True)
    
@socketio.on('stop')
def handle_stop():
    """Detener el dron al soltar una tecla."""
    success = drone_service.stop()
    emit('drone_response', {"action": "stop", "status": success}, broadcast=True)


@socketio.on('battery')
def handle_battery():
    """Obtener el nivel de batería del dron."""
    battery = drone_service.get_battery()
    emit('drone_battery', {"battery": battery}, broadcast=True)

@socketio.on('start_video')
def handle_start_video():
    """Iniciar la transmisión de video."""
    success = drone_service.start_video_stream()
    emit('drone_response', {"action": "start_video", "status": success}, broadcast=True)

@socketio.on('capture_photo')
def handle_capture_photo(data):
    """Capturar una foto con el dron."""
    filename = data.get("filename", "photo.jpg")
    success = drone_service.take_photo(filename)
    emit('drone_response', {"action": "capture_photo", "filename": filename, "status": success}, broadcast=True)

@socketio.on("command")
def handle_command(data):
    """Maneja comandos del cliente para controlar el dron"""
    print(f"Comando recibido: {data}")
    emit('response', {'message': 'Comando {data} recibido'}, brodcast = True)