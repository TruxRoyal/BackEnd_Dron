from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio

@socketio.on('start_video')
def handle_start_video():
    success = drone_service.camera.start_video_stream()
    emit('drone_response', {"action": "start_video", "status": success})

@socketio.on('capture_photo')
def handle_capture_photo(data):
    filename = data.get("filename", "photo.jpg")
    success = drone_service.camera.take_photo(filename)
    emit('drone_response', {"action": "capture_photo", "filename": filename, "status": success})
