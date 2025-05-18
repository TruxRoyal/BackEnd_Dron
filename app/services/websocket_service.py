from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")

# Importación para registrar automáticamente los eventos
from .websocket import base_ws, flight_ws, camera_ws, stats_ws
