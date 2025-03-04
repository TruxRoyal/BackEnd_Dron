from djitellopy import Tello
import threading
import cv2

class DroneService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Implementación Singleton para evitar múltiples instancias del dron."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DroneService, cls).__new__(cls)
                cls._instance.tello = None
                cls._instance.connected = False
                #cls._instance.video_streaming == False
        return cls._instance

    def connect(self):
        """Conectar al dron. solo si no esta conectado"""
        if not self.connected:
            try:
                if self.tello is None:
                    self.tello = Tello()
                self.tello.connect()
                self.tello.streamoff() #Apagar el stream de video por defecto
                self.connected = True
                print("Conexión exitosa con el dron")
            except Exception as e:
                print(f"Error al conectar con el dron: {e}")
                self.connected = False
        return self.connected

    def disconnect(self):
        """Desconectar el dron correctamente."""
        if self.connected:
            self.tello.end()
            self.connected = False
            print("🔌 Dron desconectado")

    def stop(self):
        """Detener el dron (simula soltar el joystick en la app oficial)."""
        if self.connect():
            with self.command_lock:
                try:
                    self.tello.send_rc_control(0, 0, 0, 0)  # 🔥 Detiene todos los movimientos
                    print("🛑 Dron detenido")
                    return True
                except Exception as e:
                    print(f"❌ Error al detener el dron: {e}")
                    return False

    def get_battery(self):
        """Obtener el nivel de batería del dron."""
        if self.connect():  # Conectar antes de obtener la batería
            return self.tello.get_battery()
        return None

    def takeoff(self):
        """Hacer despegar el dron."""
        if self.connect():  # Conectar antes de despegar
            self.tello.takeoff()
            return True
        return False

    def land(self):
        """Hacer aterrizar el dron."""
        if self.connect():  # Conectar antes de aterrizar
            self.tello.land()
            return True
        return False
    
    def move(self, direction, distance):
        """Mover el dron en una dirección específica."""
        if self.connect():  # Conectar antes de mover
            if direction == "forward":
                self.tello.move_forward(distance)
            elif direction == "back":
                self.tello.move_back(distance)
            elif direction == "left":
                self.tello.move_left(distance)
            elif direction == "right":
                self.tello.move_right(distance)
            elif direction == "up":
                self.tello.move_up(distance)
            elif direction == "down":
                self.tello.move_down(distance)
            else:
                return False
            return True
        return False

    def rotate(self, direction, degrees):
        """Rotar el dron en una dirección específica."""
        if self.connect():  # Conectar antes de rotar
            if direction == "clockwise":
                self.tello.rotate_clockwise(degrees)
            elif direction == "counter_clockwise":
                self.tello.rotate_counter_clockwise(degrees)
            else:
                return False
            return True
        return False

    def start_video_stream(self):
        """Iniciar la transmisión de video."""
        if self.connect():
            self.tello.streamon()
            return True
        return False

    def get_frame(self):
        """Obtener un frame de la cámara."""
        if self.connect():
            try:
                self.tello.streamon()  # Asegurar que el stream está activo
                frame_read = self.tello.get_frame_read()
                return frame_read.frame
            except Exception as e:
                print(f"Error al obtener el frame del dron: {e}")
        return None

    def take_photo(self, filename="photo.jpg"):
        """Capturar una foto y guardarla en un archivo."""
        if self.connect():
            self.tello.streamon()  # Activar el stream antes de capturar

            frame = self.get_frame()
            if frame is not None:
                cv2.imwrite(filename, frame)
            return True
        else:
            print("Error: No se pudo capturar el frame.")
        return False

# Instancia global del servicio del dron
drone_service = DroneService()