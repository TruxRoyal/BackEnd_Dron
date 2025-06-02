from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio
import threading
import cv2
import base64
import time

camera = drone_service.camera

def video_stream_loop(socketio, camera):
    while camera.streaming:
        frame = camera.get_frame()
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            _, buffer = cv2.imencode('.jpg', rgb_frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('video_frame', {'image': jpg_as_text})

            if camera.recording and camera.video_writer:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                camera.video_writer.write(frame_rgb)

        time.sleep(0.01)  # Puedes usar 0.05 (~20 FPS) o incluso 0.1 (10 FPS)

@socketio.on('start_video')
def handle_start_video():
    if camera.start_video_stream():
        thread = threading.Thread(target=video_stream_loop, args=(socketio, camera))
        thread.daemon = True
        thread.start()

@socketio.on('stop_video')
def handle_stop_video():
    camera.stop_video_stream()
    socketio.emit('video_stopped')

@socketio.on('capture_photo')
def handle_capture_photo(data=None):
    success, path = camera.take_photo()
    emit('drone_response', {
        "action": "capture_photo",
        "status": success,
        "filename": path if success else None
    })

@socketio.on('start_recording')
def handle_start_recording(data=None):
    success = camera.start_recording()
    emit('drone_response', {
        "action": "start_recording",
        "status": success
    })

@socketio.on('stop_recording')
def handle_stop_recording(data=None):
    success = camera.stop_recording()
    emit('drone_response', {
        "action": "stop_recording",
        "status": success
    })
