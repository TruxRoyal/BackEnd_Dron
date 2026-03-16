from app.utils.media_utils import get_media_directory
from app.services.camera_config_service import load_camera_config

from djitellopy import Tello
from datetime import datetime

import cv2
import time

# ─────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────
WARMUP_FRAMES   = 60
RECORD_FPS      = 30.0
DEFAULT_BITRATE   = Tello.BITRATE_5MBPS
DEFAULT_FPS       = Tello.FPS_30
DEFAULT_RES       = Tello.RESOLUTION_720P
DEFAULT_DIRECTION = Tello.CAMERA_FORWARD


class DroneCamera:
    def __init__(self, base):
        self.base         = base
        self.streaming    = False
        self.frame_read   = None
        self.recording    = False
        self.video_writer = None
        self._frame_size: tuple[int, int] | None = None

    # ─────────────────────────────────────────
    #  Configuración de video
    # ─────────────────────────────────────────
    def configure_video_settings(self):
        steps = [
            ("FPS",        lambda: self.base.tello.set_video_fps(DEFAULT_FPS)),
            ("bitrate",    lambda: self.base.tello.set_video_bitrate(DEFAULT_BITRATE)),
            ("resolución", lambda: self.base.tello.set_video_resolution(DEFAULT_RES)),
            ("cámara",     lambda: self.base.tello.set_video_direction(DEFAULT_DIRECTION)),
        ]
        for name, cmd in steps:
            try:
                cmd()
                print(f"✅ {name} configurado correctamente")
            except Exception as e:
                print(f"⚠️  No se pudo establecer {name}: {e}")

    # ─────────────────────────────────────────
    #  Stream
    # ─────────────────────────────────────────
    def start_video_stream(self):
        if not self.base.connect():
            return False

        # NOTA: Este Tello responde "unknown command" a set_video_fps/bitrate/resolution/direction.
        # Mandar esos comandos desincroniza el buffer UDP — streamon() recibe "unknown command"
        # en lugar de "ok" y el dron entra en error (LED rojo). Se omiten intencionalmente.

        try:
            try:
                self.base.tello.streamoff()
            except Exception:
                pass
            self.base.tello.streamon()
            self.frame_read = self.base.tello.get_frame_read()

            # Warmup: esperar frames estables usando get_frame() con .copy() seguro
            print(f"⏳ Calentando stream ({WARMUP_FRAMES} frames)…")
            for _ in range(WARMUP_FRAMES):
                self.get_frame()
                time.sleep(1 / RECORD_FPS)

            # Detectar tamaño real del frame
            sample = self.get_frame()
            if sample is not None:
                h, w = sample.shape[:2]
                self._frame_size = (w, h)
                print(f"📐 Frame detectado: {w}×{h}")

            self.streaming = True
            print("📹 Transmisión iniciada")
            return True

        except Exception as e:
            print(f"❌ Error en streamon: {e}")
            return False

    def stop_video_stream(self):
        if self.recording:
            self.stop_recording()

        if not self.base.connect():
            return False

        self.base.tello.streamoff()
        self.frame_read  = None
        self.streaming   = False
        self._frame_size = None
        print("📹 Transmisión detenida")
        return True

    # ─────────────────────────────────────────
    #  Frame
    # ─────────────────────────────────────────
    def get_frame(self):
        """
        Devuelve una copia del frame actual en RGB (formato nativo de djitellopy).

        El .copy() es crítico: frame_read.frame es un buffer compartido que
        djitellopy sobreescribe en su propio hilo continuamente. Sin .copy(),
        leer el buffer mientras se actualiza produce tearing — franjas
        horizontales pixeladas a mitad del frame, incluso con el dron quieto.

        Quien reciba este frame debe hacer RGB→BGR antes de usar OpenCV
        (imencode, imwrite, VideoWriter).
        """
        if self.frame_read and self.frame_read.frame is not None:
            return self.frame_read.frame.copy()
        return None

    # ─────────────────────────────────────────
    #  Foto
    # ─────────────────────────────────────────
    def take_photo(self):
        frame = self.get_frame()        # RGB
        if frame is None:
            print("❌ No hay frame disponible")
            return False, None

        now       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"mision_{now}.jpg"
        save_path = get_media_directory() / filename

        # djitellopy entrega RGB — convertir a BGR antes de imwrite
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(save_path), bgr)
        print(f"📸 Foto guardada en {save_path}")
        return True, str(save_path)

    # ─────────────────────────────────────────
    #  Grabación
    # ─────────────────────────────────────────
    def start_recording(self):
        if self.recording:
            print("⚠️  Ya está grabando")
            return False

        if not self.streaming:
            print("❌ El stream debe estar activo antes de grabar")
            return False

        w, h = self._frame_size if self._frame_size else (960, 720)

        now       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"video_{now}.mp4"
        save_path = get_media_directory() / filename

        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        writer = cv2.VideoWriter(str(save_path), fourcc, RECORD_FPS, (w, h))

        if not writer.isOpened():
            print("⚠️  avc1 no disponible, usando mp4v")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(save_path), fourcc, RECORD_FPS, (w, h))

        if not writer.isOpened():
            print("❌ No se pudo inicializar el VideoWriter")
            return False

        self.video_writer = writer
        self.recording    = True
        print(f"🔴 Grabación iniciada: {save_path}  [{w}×{h} @ {RECORD_FPS}fps]")
        return True

    def stop_recording(self):
        if not self.recording or self.video_writer is None:
            return False

        self.recording = False
        self.video_writer.release()
        self.video_writer = None
        print("⏹️  Grabación detenida")
        return True

    def emergency_stop(self):
        """Detiene el stream/grabación y resetea todo el estado del dron.
        Llamado cuando el dron se apaga inesperadamente — no llama al dron."""
        self.streaming = False
        self.frame_read = None
        self._frame_size = None
        if self.recording:
            self.recording = False
            if self.video_writer:
                try:
                    self.video_writer.release()
                except Exception:
                    pass
                self.video_writer = None
        # Reset completo del estado base: connected=False, _is_flying=False,
        # _is_landing=False, cierra socket UDP viejo
        self.base._full_reset()
        print("🛑 Emergency stop: cámara y estado base limpiados")

    # ─────────────────────────────────────────
    #  Actualización de settings
    # ─────────────────────────────────────────
    def update_video_settings(self, settings: dict):
        mapping = {
            "fps": {
                "5":  Tello.FPS_5,
                "15": Tello.FPS_15,
                "30": Tello.FPS_30,
            },
            "bitrate": {
                "auto": Tello.BITRATE_AUTO,
                "1":    Tello.BITRATE_1MBPS,
                "2":    Tello.BITRATE_2MBPS,
                "3":    Tello.BITRATE_3MBPS,
                "4":    Tello.BITRATE_4MBPS,
                "5":    Tello.BITRATE_5MBPS,
            },
            "resolution": {
                "480p": Tello.RESOLUTION_480P,
                "720p": Tello.RESOLUTION_720P,
            },
            "camera": {
                "forward":  Tello.CAMERA_FORWARD,
                "downward": Tello.CAMERA_DOWNWARD,
            },
        }

        try:
            if "fps" in settings:
                self.base.tello.set_video_fps(mapping["fps"][str(settings["fps"])])
            if "bitrate" in settings:
                self.base.tello.set_video_bitrate(mapping["bitrate"][str(settings["bitrate"])])
            if "resolution" in settings:
                self.base.tello.set_video_resolution(mapping["resolution"][settings["resolution"].lower()])
            if "camera" in settings:
                self.base.tello.set_video_direction(mapping["camera"][settings["camera"].lower()])

            print("✅ Configuración aplicada:", settings)
            return True, "Configuración aplicada"

        except KeyError as e:
            msg = f"Valor desconocido: {e}"
            print(f"❌ {msg}")
            return False, msg
        except Exception as e:
            print(f"❌ Error al aplicar configuración: {e}")
            return False, str(e)