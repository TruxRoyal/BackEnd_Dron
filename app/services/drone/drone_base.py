from djitellopy import Tello
import time

CONNECT_TIMEOUT = 5
MAX_RETRIES     = 3
RETRY_DELAY     = 2.0


class DroneBase:
    def __init__(self):
        self.tello        = None
        self.connected    = False
        self.command_lock = None
        self._is_flying   = False
        self._is_landing  = False

    # ─────────────────────────────────────────
    #  Conexión
    # ─────────────────────────────────────────
    def connect(self) -> bool:
        # Si está marcado como conectado, verificar que sigue vivo.
        # Cuando el dron se apaga, self.connected queda en True pero
        # el socket es inválido — is_alive() lo detecta y hace reset.
        if self.connected and self.tello is not None:
            if self.is_alive():
                return True
            else:
                print("⚠️  Dron no responde — limpiando estado anterior…")
                self._full_reset()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"🔄 Intento de conexión {attempt}/{MAX_RETRIES}…")

                # Siempre crear Tello nuevo — si el dron se reinició
                # el socket anterior es inválido aunque parezca abierto
                self._cleanup_tello()
                self.tello = Tello()
                self.tello.RESPONSE_TIMEOUT = CONNECT_TIMEOUT
                self.tello.TAKEOFF_TIMEOUT  = CONNECT_TIMEOUT

                self.tello.connect()
                battery = self.tello.get_battery()
                print(f"✅ Dron conectado — batería: {battery}%")
                self.connected = True
                return True

            except Exception as e:
                print(f"⚠️  Intento {attempt} fallido: {e}")
                self._cleanup_tello()
                if attempt < MAX_RETRIES:
                    print(f"⏳ Reintentando en {RETRY_DELAY}s…")
                    time.sleep(RETRY_DELAY)

        print("❌ No se pudo conectar — verifica que el dron esté encendido y conectado al WiFi")
        return False

    def disconnect(self):
        if self.connected:
            try:
                if self.tello:
                    try:
                        self.tello.streamoff()
                    except Exception:
                        pass
                    self.tello.end()
            except Exception as e:
                print(f"⚠️  Error al desconectar: {e}")
            finally:
                self._full_reset()
                print("🔌 Dron desconectado")

    def reset(self):
        print("♻️ Reiniciando estado del dron…")
        self._full_reset()
        print("♻️ Estado reiniciado")

    # ─────────────────────────────────────────
    #  Verificación de conectividad
    # ─────────────────────────────────────────
    def is_alive(self) -> bool:
        """Verifica rápido si el dron responde. Si no, marca como desconectado."""
        if not self.connected or self.tello is None:
            return False
        try:
            self.tello.get_battery()
            return True
        except Exception:
            print("⚠️  El dron dejó de responder")
            self.connected = False
            return False

    # ─────────────────────────────────────────
    #  Internos
    # ─────────────────────────────────────────
    def _cleanup_tello(self):
        """Cierra el socket UDP y destruye el objeto Tello.
        El sleep(0.5) es necesario en Windows para que el SO libere
        el puerto antes de que el próximo Tello() intente abrirlo."""
        if self.tello:
            try:
                self.tello.end()
            except Exception:
                pass
            self.tello = None
            time.sleep(0.5)     # esperar liberación del puerto UDP

    def _full_reset(self):
        """Reset completo de estado — sin lanzar excepciones."""
        self._cleanup_tello()
        self.connected   = False
        self._is_flying  = False
        self._is_landing = False