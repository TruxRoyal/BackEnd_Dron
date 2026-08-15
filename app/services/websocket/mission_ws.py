import threading
import time

from flask_socketio import Namespace, emit

from app.services.mission.mission_state_service import MissionStateService
from app.services.mission.waypoint_mapper_service import WaypointMapperService
from app.services.mission.flight_path_service import FlightPathService
from app.services.mission.drone_navigation_service import DroneNavigationService
from app.services.mission.mission_planner_service import MissionPlannerService
from app.services.vgps_instance import vgps
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio

_state = MissionStateService()
_mapper = WaypointMapperService()
_flight_path = FlightPathService()
_navigation = DroneNavigationService(drone_service.flight, vgps)
_planner = MissionPlannerService(
    _state, _mapper, _flight_path, _navigation, vgps, drone_service.camera, socketio
)


def _full_state():
    return {
        "drone": vgps.get_state(),
        "path": _flight_path.get_path(),
        "mission": _state.get_state(),
    }


def _drone_ready() -> str | None:
    if not drone_service.base.connected:
        return "Dron no conectado"
    if not drone_service.base._is_flying:
        return "El dron debe estar volando para iniciar la misión"
    return None


class MissionNamespace(Namespace):
    namespace = "/mission"

    def on_connect(self):
        print("[Mission] Cliente conectado")
        emit("mission_update", _full_state())

    def on_disconnect(self):
        print("[Mission] Cliente desconectado")
        if _state.is_running():
            _planner.pause()

    def on_mission_set_origin(self, data):
        lat = data.get("lat")
        lng = data.get("lng")
        if lat is None or lng is None:
            return
        vgps.set_origin(lat, lng)
        vgps.reset()
        _mapper.set_origin(lat, lng)
        _flight_path.reset()
        emit("mission_update", _full_state(), broadcast=True)

    def on_mission_load_waypoints(self, data):
        waypoints = data.get("waypoints", [])
        try:
            local_wps = _mapper.load_waypoints(waypoints)
        except ValueError as e:
            emit("mission_error", {"message": f"Origen no configurado. Haz clic derecho en el mapa para establecerlo. ({e})"})
            return
        _state.total_waypoints = len(local_wps)
        emit("mission_update", _full_state(), broadcast=True)

    def on_mission_start(self, data=None):
        error = _drone_ready()
        if error:
            emit("mission_error", {"message": error})
            return
        if data and data.get("mission_name"):
            _planner.set_mission_name(data["mission_name"])
        success = _planner.start()
        if not success:
            emit("mission_error", {"message": "No se pudo iniciar: sin waypoints o misión ya en curso"})

    def on_mission_takeoff_start(self, data=None):
        if not drone_service.base.connected:
            emit("mission_error", {"message": "Dron no conectado"})
            return

        if data and data.get("mission_name"):
            _planner.set_mission_name(data["mission_name"])

        def _do():
            if not drone_service.base._is_flying:
                ok = drone_service.flight.takeoff()
                if not ok:
                    socketio.emit("mission_error", {"message": "Fallo el despegue"}, namespace="/mission")
                    return
                time.sleep(3)
            _planner.start()

        threading.Thread(target=_do, daemon=True).start()

    def on_mission_pause(self, data=None):
        _planner.pause()

    def on_mission_stop(self, data=None):
        _planner.stop()

    def on_mission_reset(self, data=None):
        _planner.reset()
