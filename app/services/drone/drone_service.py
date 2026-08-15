from .drone_base import DroneBase
from .drone_flight import DroneFlight
from .drone_camera import DroneCamera
from .drone_stats import DroneStats

class DroneService:
    def __init__(self):
        self.base = DroneBase()
        self.flight = DroneFlight(self.base)
        self.camera = DroneCamera(self.base)
        self.stats = DroneStats(self.base)

    def reset(self):
        """Reset completo: emergency_stop ya hace _full_reset interno en base."""
        self.camera.emergency_stop()

    def get_status(self):
        return {
            "connected": self.base.connected,
            "is_flying": self.base._is_flying,
            "is_landing": self.base._is_landing,
            **self.stats.get_full_status()
        }

drone_service = DroneService()
