import math


class WaypointMapperService:
    def __init__(self):
        self.origin_lat = None
        self.origin_lng = None
        self._local_waypoints = []

    def set_origin(self, lat: float, lng: float):
        self.origin_lat = lat
        self.origin_lng = lng
        self._local_waypoints = []

    def _to_local(self, lat: float, lng: float):
        if self.origin_lat is None:
            raise ValueError("Origin not set before converting waypoints")
        dlat = lat - self.origin_lat
        dlng = lng - self.origin_lng
        y = dlat * 111320
        x = dlng * (40075000 * math.cos(math.radians(self.origin_lat)) / 360)
        return round(x, 3), round(y, 3)

    def load_waypoints(self, waypoints: list) -> list:
        self._local_waypoints = []
        for wp in waypoints:
            x, y = self._to_local(wp["lat"], wp["lng"])
            self._local_waypoints.append({
                "id": wp.get("id"),
                "lat": wp["lat"],
                "lng": wp["lng"],
                "x": x,
                "y": y,
                "altitude": wp.get("altitude", 30),
                "speed": wp.get("speed", 5),
            })
        return self._local_waypoints

    def get_waypoint(self, index: int):
        if 0 <= index < len(self._local_waypoints):
            return self._local_waypoints[index]
        return None

    def count(self) -> int:
        return len(self._local_waypoints)

    def reset(self):
        self._local_waypoints = []
