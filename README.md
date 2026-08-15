# BackEnd Dron

API backend (Flask + Flask-SocketIO) para el control de un dron DJI Tello, streaming de cámara y análisis de cultivos (detección de frutos, hojas, manchas) a partir de las imágenes capturadas en vuelo.

## Stack

- **Flask** + **Flask-SocketIO** (REST + WebSockets)
- **djitellopy** para el control del dron Tello
- **OpenCV**, **numpy**, **pillow** para procesamiento de imágenes
- **pymongo** (MongoDB) para persistencia
- **pandas** + **matplotlib** para reportes y gráficos de análisis
- YOLO opcional para detección de frutos (`app/analysis/detectors/yolo_detector.py`)

## Estructura principal

```
app/
├── analysis/          # Pipeline de análisis de imágenes (calidad, índices, detección)
│   └── detectors/      # Frutos por color, hojas, manchas, YOLO
├── config/            # Configuración (settings, auth, base de datos, cámara)
├── middleware/        # Auth y logging
├── models/            # Esquemas de datos
├── routes/            # Endpoints REST (dron, imágenes, análisis, posición)
├── services/
│   ├── drone/          # Conexión, vuelo, cámara y stats del dron
│   ├── websocket/       # Canales en tiempo real (vuelo, cámara, stats, GPS virtual, misión)
│   ├── mongo/           # Acceso a MongoDB
│   └── mission/         # Lógica de misiones
├── tools/             # Scripts de utilidad (smoke tests, gráficos, chequeo de mongo)
└── utils/             # Helpers (logger, GPS, validaciones, fechas)
tests/                 # Tests unitarios e integración
reports/               # Reportes generados por el análisis de misiones
```

## Requisitos

- Python 3.13
- MongoDB corriendo localmente (o accesible vía `MONGO_URI`)

## Configuración

1. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copiar `.env.example` a `.env` y completar los valores:
   ```bash
   copy .env.example .env
   ```

   | Variable | Descripción |
   |---|---|
   | `SECRET_KEY` | Clave secreta de la app (usar un valor único y privado, no el de ejemplo) |
   | `MONGO_URI` | URI de conexión a MongoDB |
   | `DEBUG` | Activa el modo debug de Flask (`True`/`False`) |

   > `.env` está en `.gitignore`: nunca se debe commitear con secretos reales. `app/config/settings.py` los lee mediante variables de entorno (`python-dotenv`).

## Ejecución

```bash
python run.py
```

El servidor levanta en `http://localhost:5000` con soporte de WebSockets (`cors_allowed_origins="*"`).

## Tests

```bash
pytest tests/
```

## Frontend

Este backend es consumido por [Frontend-Dron](../../Front%20dron/Frontend-Dron), la aplicación de escritorio (Electron) que controla el dron y visualiza telemetría, video y reportes.
