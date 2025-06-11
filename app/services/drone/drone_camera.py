from app.utils.media_utils import get_media_directory

from djitellopy import Tello
from datetime import datetime

import cv2

class DroneCamera:
    def __init__(self, base):
        self.base = base
        self.streaming = False
        self.frame_read = None
        self.recording = False
        self.video_writer = None

    def configure_video_settings(self):
        try:
            self.base.tello.set_video_fps(Tello.FPS_30)
        except Exception as e:
            print(f"⚠️ No se pudo establecer FPS: {e}")

    for cmd_name, cmd in [
        ("bitrate", lambda: self.base.tello.set_video_bitrate(Tello.BITRATE_2MBPS)),
        ("resolución", lambda: self.base.tello.set_video_resolution(Tello.RESOLUTION_720P)),
        ("cámara", lambda: self.base.tello.set_video_direction(Tello.CAMERA_FORWARD)),
    ]:
        try:
            cmd()
        except Exception as e:
            print(f"⚠️ No se pudo establecer {cmd_name}: {e}")


    def start_video_stream(self):
        if self.base.connect():
            self.configure_video_settings()
            self.base.tello.streamon()
            self.frame_read = self.base.tello.get_frame_read()
            self.streaming = True
            print("📹 Transmisión de video iniciada")
            return True
        return False
    
    def stop_video_stream(self):
        if self.base.connect():
            self.base.tello.streamoff()
            self.frame_read = None
            self.streaming = False
            print("📹 Transmisión de video detenida")
            return True
        return False

    def get_frame(self):
        if self.frame_read:
            return self.frame_read.frame
        return None

    def take_photo(self):
        frame = self.get_frame()
        if frame is not None:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"mision_{now}.jpg"
            save_path = get_media_directory() / filename
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cv2.imwrite(str(save_path), rgb_frame)
            print(f"📸 Foto guardada en {save_path}")
            return True, str(save_path)
        return False, None

    def start_recording(self):
        if self.recording:
            print("⚠️ Ya está grabando")
            return False

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"video_{now}.mp4"
        save_path = get_media_directory() / filename

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(str(save_path), fourcc, 30.0, (960, 720))
        self.recording = True

        print(f"🔴 Grabación iniciada: {save_path}")
        return True

    def stop_recording(self):
        if self.recording and self.video_writer:
            self.recording = False
            self.video_writer.release()
            self.video_writer = None
            print("⏹️ Grabación detenida")
            return True
        return False
