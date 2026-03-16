import math

class VirtualGPS:
    def __init__(self, lat_origin: float, lon_origin: float):
        self.lat_origin = lat_origin
        self.lon_origin = lon_origin
        self.x = 0.0  # metros en eje X (derecha/izquierda)
        self.y = 0.0  # metros en eje Y (adelante/atrás)
        self.z = 0.0  # altura
        self.yaw = 0.0  # orientación en grados (0° = norte)

    def reset(self):
        self.x = self.y = self.z = self.yaw = 0.0

    def update_position(self, forward_cm=0, right_cm=0, up_cm=0):
        dx = right_cm / 100
        dy = forward_cm / 100
        dz = up_cm / 100

        rad = math.radians(self.yaw)
        delta_x = dx * math.cos(rad) - dy * math.sin(rad)
        delta_y = dx * math.sin(rad) + dy * math.cos(rad)

        self.x += delta_x
        self.y += delta_y
        self.z += dz

    def rotate(self, delta_yaw):
        self.yaw = (self.yaw + delta_yaw) % 360

    def get_position(self):
        return round(self.x, 2), round(self.y, 2), round(self.z, 2)

    def get_latlon(self):
        delta_lat = self.y / 111320
        delta_lon = self.x / (40075000 * math.cos(math.radians(self.lat_origin)) / 360)
        lat = self.lat_origin + delta_lat
        lon = self.lon_origin + delta_lon
        return round(lat, 7), round(lon, 7)

    def get_state(self):
        lat, lon = self.get_latlon()
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "z": round(self.z, 2),
            "yaw": round(self.yaw, 2),
            "lat": lat,
            "lon": lon
        }

    def set_origin(self, lat, lon):
        self.lat_origin = lat
        self.lon_origin = lon
