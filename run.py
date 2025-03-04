from flask import Flask
from flask_cors import CORS
from app.services.websocket_service import socketio  # ✅ Usamos la misma instancia
from app.services.drone_service import drone_service  # ✅ Importamos el dron correctamente

app = Flask(__name__)
CORS(app)

# Configurar WebSockets correctamente
socketio.init_app(app, cors_allowed_origins="*")  # ✅ Solo se inicializa aquí, no en otro lado

# Ruta de prueba
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
