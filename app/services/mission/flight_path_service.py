class FlightPathService:
    def __init__(self):
        self._path = []

    def append(self, lat: float, lng: float):
        self._path.append({"lat": lat, "lng": lng})

    def get_path(self) -> list:
        return list(self._path)

    def reset(self):
        self._path = []
