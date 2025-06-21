from flask_socketio import SocketIO
from .websocket.virtual_gps_ws import VirtualGPSNamespace

socketio = SocketIO(cors_allowed_origins="*")

socketio.on_namespace(VirtualGPSNamespace())

# Importación para registrar automáticamente los eventos
from .websocket import base_ws, flight_ws, camera_ws, stats_ws
