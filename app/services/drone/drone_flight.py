import threading

class DroneFlight:
    def __init__(self, base):
        self.base = base
        self.lock = threading.Lock()

    def takeoff(self):
        if self.base.connect() and not self.base._is_flying:
            with self.lock:
                try:
                    h = self.base.tello.get_height()
                    b = self.base.tello.get_battery()
                    print(f"🚁 Pre-takeoff — altura: {h}cm  batería: {b}%")
                    self.base.tello.takeoff()
                    self.base._is_flying = True
                    return True
                except Exception as e:
                    print(f"❌ Error en despegue: {e}")
        return False

    def land(self):
        if self.base.connect() and self.base._is_flying and not self.base._is_landing:
            with self.lock:
                try:
                    self.base._is_landing = True
                    self.base.tello.land()
                    self.base._is_flying = False
                    self.base._is_landing = False

                    return True
                except Exception:
                    self.base._is_landing = False
        return False

    def move(self, direction, distance):
        if self.base.connect():
            try:
                getattr(self.base.tello, f"move_{direction}")(distance)
                return True
            except Exception:
                return False

    def rotate(self, direction, degrees):
        if self.base.connect():
            try:
                if direction == "clockwise":
                    self.base.tello.rotate_clockwise(degrees)
                else:
                    self.base.tello.rotate_counter_clockwise(degrees)
                return True
            except Exception:
                return False

    def rc_control(self, x=0, y=0, z=0, yaw=0):
        if not self.base._is_flying:
            #print("[RC_CONTROL] ❌ Ignorado: el dron no está volando.")
            return False

        with self.lock:
            try:
                self.base.tello.send_rc_control(x, y, z, yaw)
               #print(f"[RC_CONTROL] x={x}, y={y}, z={z}, yaw={yaw} | ✅ True")
                return True
            except Exception:
                return False
