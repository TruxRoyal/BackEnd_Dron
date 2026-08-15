from enum import Enum


class MissionStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class MissionStateService:
    def __init__(self):
        self.status = MissionStatus.IDLE
        self.current_waypoint_index = 0
        self.total_waypoints = 0
        self.photos_taken = 0

    def start(self):
        self.status = MissionStatus.RUNNING

    def pause(self):
        self.status = MissionStatus.PAUSED

    def stop(self):
        self.status = MissionStatus.IDLE
        self.current_waypoint_index = 0

    def complete(self):
        self.status = MissionStatus.COMPLETED

    def advance_waypoint(self):
        self.current_waypoint_index += 1

    def add_photo(self):
        self.photos_taken += 1

    def reset(self):
        self.__init__()

    def is_running(self):
        return self.status == MissionStatus.RUNNING

    def get_state(self):
        return {
            "status": self.status.value,
            "currentWaypoint": self.current_waypoint_index,
            "totalWaypoints": self.total_waypoints,
            "photosTaken": self.photos_taken,
        }
