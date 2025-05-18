class DroneStats:
    def __init__(self, base):
        self.base = base

    def get_battery(self):
        return self.base.tello.get_battery() if self.base.connect() else None

    def get_height(self):
        try:
            return self.base.tello.get_height()
        except Exception as e:
            print(f"❌ Error al obtener altura: {e}")
            return None
        
    def get_barometer(self):
        try:
            return self.base.tello.get_barometer()
        except Exception as e:
            print(f"❌ Error al obtener barómetro: {e}")
            return None

    def get_acceleration_x(self):
        try:
            return self.base.tello.get_acceleration_x()
        except Exception as e:
            print(f"❌ Error al obtener velocidad: {e}")
            return None

    def get_time(self):
        try:
            return self.base.tello.get_flight_time()
        except Exception as e:
            print(f"❌ Error al obtener tiempo de vuelo: {e}")
            return None

    def get_full_status(self):
        return {
            "battery": self.get_battery(),
            "height": self.get_height(),
            "barometer": self.get_barometer(),
            "acceleration_x": self.get_acceleration_x(),
            "time": self.get_time()
        }
