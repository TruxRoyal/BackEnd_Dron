from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio
from app.services.vgps_instance import vgps
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
        x = int(data.get("x", 0))     # → derecha/izquierda
        y = int(data.get("y", 0))     # ↑ adelante/atrás
        z = int(data.get("z", 0))     # ↑ altura
        yaw = int(data.get("yaw", 0)) # ↻ rotación
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

    # 🔁 Actualizar VirtualGPS solo si el control fue exitoso
    if success:
        if yaw:
            vgps.rotate(yaw)

        vgps.update_position(forward_cm=y, right_cm=x, up_cm=z)
        emit("vgps_state", vgps.get_state(), broadcast=True)

@socketio.on('calibrate')
def handle_calibrate(data=None):
    def do_calibrate():
        result = drone_service.flight.calibrate()
        socketio.emit('drone_response', {"action": "calibrate", **result})
    threading.Thread(target=do_calibrate).start()

@socketio.on("vgps_set_origin")
def handle_set_origin(data):
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is not None and lon is not None:
        vgps.set_origin(lat, lon)
        emit("drone_response", {
            "action": "vgps_set_origin",
            "status": True,
            "lat": lat,
            "lon": lon
        })
        print(f"📍 Origen de VirtualGPS actualizado a lat={lat}, lon={lon}")
    else:
        emit("drone_response", {
            "action": "vgps_set_origin",
            "status": False,
            "error": "Faltan lat o lon"
        })
