from flask_socketio import emit
from app.services.drone.drone_service import drone_service
from app.services.websocket_service import socketio
from app.services.camera_config_service import save_camera_config

import threading
import cv2
import base64
import time

camera = drone_service.camera

# ─────────────────────────────────────────────
#  Configuración de calidad del stream en vivo
# ─────────────────────────────────────────────
LIVE_FPS          = 25          # FPS objetivo para el WebSocket
LIVE_JPEG_QUALITY = 85          # Subido a 85 — reduce pixelación en movimiento
RECORD_FPS        = 30.0        # FPS para la grabación (siempre 30, independiente del live)
LIVE_MAX_ENCODE_MS = 1000 / LIVE_FPS  # tiempo máximo permitido por frame (ms)

# ─────────────────────────────────────────────
#  djitellopy entrega frames en RGB (no BGR).
#  cv2.imencode espera BGR, por eso los colores
#  salían azul/amarillo. Hay que convertir RGB→BGR
#  antes de encodear para live, y también para grabar.
# ─────────────────────────────────────────────

def _encode_frame_for_live(frame) -> str | None:
    """Convierte RGB→BGR y encodea a JPEG base64 para WebSocket."""
    try:
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok, buffer = cv2.imencode(
            '.jpg', bgr,
            [cv2.IMWRITE_JPEG_QUALITY, LIVE_JPEG_QUALITY]
        )
        if not ok:
            return None
        return base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return None


# ─────────────────────────────────────────────
#  Hilo 1: Stream en vivo por WebSocket
#  Solo encodea y emite — NO graba
# ─────────────────────────────────────────────
def _live_stream_loop(socketio, camera):
    interval = 1.0 / LIVE_FPS
    debt = 0.0
    consecutive_none = 0

    while camera.streaming:
        t0 = time.monotonic()

        if debt >= interval:
            debt -= interval
            time.sleep(0.001)
            continue

        frame = camera.get_frame()
        if frame is not None:
            consecutive_none = 0
            png_b64 = _encode_frame_for_live(frame)
            if png_b64:
                socketio.emit('video_frame', {'image': png_b64})
        else:
            consecutive_none += 1
            # ~2 segundos sin frame = dron apagado — salir del hilo
            if consecutive_none >= LIVE_FPS * 2:
                print("⚠️  Stream sin frames — dron desconectado, deteniendo hilo de video")
                camera.emergency_stop()
                socketio.emit('video_stopped')
                break

        elapsed = time.monotonic() - t0
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
            debt = 0.0
        else:
            debt += abs(sleep_time)
# ─────────────────────────────────────────────
#  Hilo 2: Grabación a 30 fps constantes
#  Bug #3 corregido: hilo propio, sin bloquear el WebSocket
#  Bug #4 corregido: lock para acceso seguro al video_writer
# ─────────────────────────────────────────────
_record_lock = threading.Lock()

def _recording_loop(camera):
    interval = 1.0 / RECORD_FPS
    while camera.recording:
        t0 = time.monotonic()

        frame = camera.get_frame()
        if frame is not None:
            # djitellopy entrega RGB — convertir a BGR para VideoWriter
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            with _record_lock:
                if camera.recording and camera.video_writer:
                    camera.video_writer.write(bgr)

        elapsed = time.monotonic() - t0
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


# ─────────────────────────────────────────────
#  Eventos WebSocket
# ─────────────────────────────────────────────

@socketio.on('start_video')
def handle_start_video():
    # Si el stream ya está activo y el dron sigue conectado, no reiniciar.
    # El hilo _live_stream_loop ya está emitiendo — el cliente solo necesita
    # escuchar los eventos video_frame que siguen llegando.
    if camera.streaming and camera.base.connected:
        emit('drone_response', {'action': 'start_video', 'status': True})
        return

    # Si el stream estaba activo pero el dron murió entretanto, limpiar antes de reiniciar.
    if camera.streaming and not camera.base.connected:
        camera.emergency_stop()
        time.sleep(0.3)

    if camera.start_video_stream():
        t = threading.Thread(target=_live_stream_loop, args=(socketio, camera), daemon=True)
        t.start()
        emit('drone_response', {'action': 'start_video', 'status': True})
    else:
        emit('drone_response', {'action': 'start_video', 'status': False})


@socketio.on('stop_video')
def handle_stop_video():
    camera.stop_video_stream()
    socketio.emit('video_stopped')


@socketio.on('capture_photo')
def handle_capture_photo(data=None):
    success, path = camera.take_photo()
    emit('drone_response', {
        'action': 'capture_photo',
        'status': success,
        'filename': path if success else None
    })


@socketio.on('start_recording')
def handle_start_recording(data=None):
    success = camera.start_recording()
    if success:
        # Hilo dedicado solo a la grabación — independiente del WebSocket
        t = threading.Thread(target=_recording_loop, args=(camera,), daemon=True)
        t.start()
    emit('drone_response', {'action': 'start_recording', 'status': success})


@socketio.on('stop_recording')
def handle_stop_recording(data=None):
    with _record_lock:
        success = camera.stop_recording()
    emit('drone_response', {'action': 'stop_recording', 'status': success})


@socketio.on('update_camera_settings')
def handle_update_camera_settings(data):
    success, msg = camera.update_video_settings(data)
    if success:
        save_camera_config(data)
    emit('camera_settings_result', {'success': success, 'message': msg})