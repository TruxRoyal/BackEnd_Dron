from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio
from .utils_ws import emit_drone_status
import threading
@socketio.on('takeoff')
def handle_takeoff(data=None):
    def do_takeoff():
        success = drone_service.flight.takeoff()
        socketio.emit('drone_response', {"action": "takeoff", "status": success})
        emit_drone_status()

    threading.Thread(target=do_takeoff).start()

@socketio.on('land')
def handle_land(data=None):
    def do_land():
        success = drone_service.flight.land()
        socketio.emit('drone_response', {"action": "land", "status": success})
        emit_drone_status()

    threading.Thread(target=do_land).start()
    
@socketio.on('rotate')
def handle_rotate(data):
    direction = data.get("direction", "")
    degrees = data.get("degrees", 90)

    def do_rotate():
        success = drone_service.flight.rotate(direction, degrees)
        socketio.emit('drone_response', {"action": "rotate", "direction": direction, "degrees": degrees, "status": success})

    threading.Thread(target=do_rotate).start()

@socketio.on('stop')
def handle_stop():
    success = drone_service.flight.rc_control(0, 0, 0, 0)
    emit('drone_response', {"action": "stop", "status": success})
    emit_drone_status()

@socketio.on('rc_control')
def handle_rc(data):
    try:
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        z = int(data.get("z", 0))
        yaw = int(data.get("yaw", 0))
    except (TypeError, ValueError):
        emit("drone_response", {
            "action": "rc_control",
            "status": False,
            "error": "Valores no válidos en rc_control"
        })
        return

    success = drone_service.flight.rc_control(x, y, z, yaw)

    emit("drone_response", {
        "action": "rc_control",
        "status": success,
        "values": { "x": x, "y": y, "z": z, "yaw": yaw }
    })

    print(f"[RC_CONTROL] x={x}, y={y}, z={z}, yaw={yaw} | ✅ {success}")
