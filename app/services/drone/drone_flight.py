import threading
import time

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

    def calibrate(self) -> dict:
        """
        Diagnóstico compatible con Tello básico.
        Usa lock y delays entre comandos para evitar mezcla de respuestas UDP.
        """
        if not self.base.connect():
            return {"success": False, "message": "Dron no conectado"}

        report = {}
        warnings = []
        battery = 0

        with self.lock:
            try:
                self.base.tello.send_command_with_return("command")
                time.sleep(0.3)

                battery = self.base.tello.get_battery()
                report["battery"] = battery
                time.sleep(0.3)
                if battery < 15:
                    warnings.append(f"Batería crítica ({battery}%) — carga antes de despegar")
                elif battery < 30:
                    warnings.append(f"Batería baja ({battery}%)")

                try:
                    attitude = self.base.tello.query_attitude()
                    report["attitude"] = attitude
                    time.sleep(0.3)
                    if abs(attitude.get("pitch", 0)) > 5 or abs(attitude.get("roll", 0)) > 5:
                        warnings.append(
                            f"Dron inclinado (pitch={attitude['pitch']}°, roll={attitude['roll']}°) — coloca en superficie plana"
                        )
                except Exception:
                    report["attitude"] = None

                try:
                    snr = self.base.tello.query_wifi_signal_noise_ratio()
                    report["wifi_snr"] = snr
                    time.sleep(0.3)
                except Exception:
                    report["wifi_snr"] = None

            except Exception as e:
                return {"success": False, "message": str(e), "report": report}

        success = battery >= 15
        message = "Calibración OK — listo para despegar" if not warnings else " | ".join(warnings)
        return {"success": success, "message": message, "report": report, "warnings": warnings}

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
