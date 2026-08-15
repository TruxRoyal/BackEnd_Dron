import math

TELLO_MIN_CM = 20
TELLO_MAX_CM = 500
SEGMENT_M = 0.5          # indoor: pasos de 50 cm (era 3.0 m para exterior)
YAW_TOLERANCE_DEG = 5
ALTITUDE_TOLERANCE_M = 0.15  # indoor: tolerancia 15 cm (era 30 cm)


class DroneNavigationService:
    def __init__(self, drone_flight, vgps):
        self.flight = drone_flight
        self.vgps = vgps

    def distance_to(self, target_x: float, target_y: float) -> float:
        cx, cy, _ = self.vgps.get_position()
        return math.sqrt((target_x - cx) ** 2 + (target_y - cy) ** 2)

    def bearing_to(self, target_x: float, target_y: float) -> float:
        cx, cy, _ = self.vgps.get_position()
        dx = target_x - cx
        dy = target_y - cy
        bearing = math.degrees(math.atan2(dx, dy))
        return bearing % 360

    def rotate_to_bearing(self, target_bearing: float) -> bool:
        delta = (target_bearing - self.vgps.yaw + 180) % 360 - 180
        if abs(delta) <= YAW_TOLERANCE_DEG:
            return True
        degrees = max(1, min(360, abs(int(delta))))
        direction = "clockwise" if delta > 0 else "counter_clockwise"
        success = self.flight.rotate(direction, degrees)
        if success:
            self.vgps.rotate(delta)
        return success

    def adjust_altitude(self, target_altitude_m: float) -> bool:
        _, _, current_z = self.vgps.get_position()
        diff_m = target_altitude_m - current_z
        if abs(diff_m) < ALTITUDE_TOLERANCE_M:
            return True
        diff_cm = max(TELLO_MIN_CM, min(TELLO_MAX_CM, int(abs(diff_m) * 100)))
        direction = "up" if diff_m > 0 else "down"
        success = self.flight.move(direction, diff_cm)
        if success:
            sign = 1 if diff_m > 0 else -1
            self.vgps.update_position(up_cm=sign * diff_cm)
        return success

    def move_step_towards(self, target_x: float, target_y: float) -> bool:
        dist_m = self.distance_to(target_x, target_y)
        move_m = min(dist_m, SEGMENT_M)
        move_cm = max(TELLO_MIN_CM, min(TELLO_MAX_CM, int(move_m * 100)))
        success = self.flight.move("forward", move_cm)
        if success:
            self.vgps.update_position(forward_cm=move_cm)
        return success
