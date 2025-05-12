import cv2

class DroneCamera:
    def __init__(self, base):
        self.base = base

    def start_video_stream(self):
        if self.base.connect():
            self.base.tello.streamon()
            return True
        return False

    def get_frame(self):
        if self.base.connect():
            try:
                self.base.tello.streamon()
                return self.base.tello.get_frame_read().frame
            except Exception as e:
                print(f"❌ Error al obtener frame: {e}")
        return None

    def take_photo(self, filename="photo.jpg"):
        frame = self.get_frame()
        if frame is not None:
            cv2.imwrite(filename, frame)
            print(f"📸 Foto guardada en {filename}")
            return True
        return False
