from djitellopy import Tello

class DroneBase:
    def __init__(self):
        self.tello = None
        self.connected = False
        self.command_lock = None
        self._is_flying = False
        self._is_landing = False
        
    def connect(self):
        if not self.connected:
            try:
                self.tello = Tello()
                self.tello.connect()
                self.tello.streamoff()
                self.connected = True
                print("✅ Dron conectado")
            except Exception as e:
                print(f"❌ Error al conectar: {e}")
                self.reset()
        return self.connected

    def disconnect(self):
        if self.connected:
            self.tello.end()
            self.connected = False
            print("🔌 Dron desconectado")

    def reset(self):
        try:
            if self.tello:
                self.tello.end()
                print("🧹 Conexión terminada con Tello.")
        except Exception as e:
            print(f"❌ Error al cerrar conexión: {e}")
        self.tello = None
        self.connected = False
        self._is_flying = False
        self._is_landing = False
        print("♻️ Estado del dron reiniciado")
