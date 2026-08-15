from flask_socketio import Namespace, emit
from app.services.vgps_instance import vgps  # ✅ Usar instancia global

flight_path = []  # 🧭 Historial virtual del vuelo

class VirtualGPSNamespace(Namespace):
    namespace = '/'

    def on_connect(self):
        print("[vGPS] Cliente conectado")
        emit("vgps_state", {
            "position": vgps.get_state(),
            "path": flight_path
        })

    def on_disconnect(self):
        print("[vGPS] Cliente desconectado")

    def on_vgps_command(self, data):
        forward = data.get("forward", 0)
        right = data.get("right", 0)
        up = data.get("up", 0)
        rotate = data.get("rotate", 0)

        if rotate:
            vgps.rotate(rotate)

        vgps.update_position(forward_cm=forward, right_cm=right, up_cm=up)

        # 🧭 Agrega la nueva posición al historial
        lat, lon = vgps.get_latlon()
        flight_path.append({ "lat": lat, "lng": lon })

        emit("vgps_state", {
            "position": vgps.get_state(),
            "path": flight_path
        }, broadcast=True)

    def on_vgps_reset(self):
        vgps.reset()
        flight_path.clear()
        emit("vgps_state", {
            "position": vgps.get_state(),
            "path": flight_path
        }, broadcast=True)
