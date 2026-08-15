import threading
import time

from app.utils.media_utils import get_mission_directory, init_manifest, close_manifest

WAYPOINT_TOLERANCE_M = 0.3   # indoor: 30 cm (era 1.0 m para exterior)
LOOP_INTERVAL_S = 0.5


class MissionPlannerService:
    def __init__(self, state, mapper, flight_path, navigation, vgps, camera, socketio):
        self.state = state
        self.mapper = mapper
        self.flight_path = flight_path
        self.navigation = navigation
        self.vgps = vgps
        self.camera = camera
        self.socketio = socketio
        self._thread = None
        self._stop_event = threading.Event()
        self._mission_dir = None
        self._mission_name = "Misión"

    def set_mission_name(self, name: str) -> None:
        self._mission_name = name or "Misión"

    def start(self) -> bool:
        if self.state.status.value not in ("IDLE", "PAUSED"):
            return False
        if self.mapper.count() == 0:
            return False
        if self.state.status.value == "IDLE":
            self._mission_dir = get_mission_directory(self._mission_name)
            init_manifest(self._mission_dir, self._mission_name)
        self.state.start()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def pause(self):
        self.state.pause()
        self._stop_event.set()
        self._broadcast()

    def stop(self):
        self._stop_event.set()
        self.state.stop()
        if self._mission_dir:
            close_manifest(self._mission_dir, status="stopped")
        self._broadcast()

    def reset(self):
        self._stop_event.set()
        self.state.reset()
        self.mapper.reset()
        self.flight_path.reset()
        self._mission_dir = None
        self._broadcast()

    def _run(self):
        while not self._stop_event.is_set():
            if not self.state.is_running():
                break

            idx = self.state.current_waypoint_index

            if idx >= self.mapper.count():
                self.state.complete()
                if self._mission_dir:
                    close_manifest(self._mission_dir, status="completed")
                self._broadcast()
                break

            target = self.mapper.get_waypoint(idx)
            dist = self.navigation.distance_to(target["x"], target["y"])

            if dist <= WAYPOINT_TOLERANCE_M:
                print(f"[Mission] ✅ Waypoint #{idx + 1} alcanzado — ajustando altitud y tomando foto")

                self.navigation.adjust_altitude(target["altitude"])

                lat, lng = self.vgps.get_latlon()
                ok, photo_path = self.camera.take_photo(
                    mission_dir=self._mission_dir,
                    waypoint=idx + 1,
                    lat=lat,
                    lng=lng,
                    altitude=target.get("altitude", 0),
                    battery=0,
                )
                if ok:
                    self.state.add_photo()
                    print(f"[Mission] 📸 Foto #{self.state.photos_taken} guardada: {photo_path}")

                self.state.advance_waypoint()
                self._broadcast()
                continue

            bearing = self.navigation.bearing_to(target["x"], target["y"])
            rotated = self.navigation.rotate_to_bearing(bearing)

            if not rotated:
                print(f"[Mission] ⚠️  Fallo al rotar hacia waypoint #{idx + 1}")
                self._stop_event.set()
                self.state.stop()
                self._broadcast()
                break

            moved = self.navigation.move_step_towards(target["x"], target["y"])

            if not moved:
                print(f"[Mission] ⚠️  Fallo al mover hacia waypoint #{idx + 1}")
                self._stop_event.set()
                self.state.stop()
                self._broadcast()
                break

            lat, lon = self.vgps.get_latlon()
            self.flight_path.append(lat, lon)
            self._broadcast()
            time.sleep(LOOP_INTERVAL_S)

    def _broadcast(self):
        self.socketio.emit(
            "mission_update",
            {
                "drone": self.vgps.get_state(),
                "path": self.flight_path.get_path(),
                "mission": self.state.get_state(),
            },
            namespace="/mission",
            broadcast=True,
        )
