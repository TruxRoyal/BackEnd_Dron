from flask import Flask
from flask_cors import CORS
from app.services.websocket_service import socketio
from app.services.drone.drone_service import drone_service

app = Flask(__name__)
CORS(app)

socketio.init_app(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return "Servidor Flask con WebSockets activo 🚀"

if __name__ == "__main__":
    try:
        print("✅ Iniciando servidor Flask con WebSockets...")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor... Liberando recursos del dron.")
        drone_service.disconnect()