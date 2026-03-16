from pathlib import Path

class AnalysisConfig:
    # Raíz de misiones
    PICTURES_ROOT = Path.home() / "Pictures" / "Misiones de Vuelo"
    # IO
    RAW_DIR_NAME = "raw"
    ANALYSIS_DIR_NAME = "analysis"
    FRAMES_DIR_NAME = "frames"

    # Calidad
    FAIL_ON_POOR_QUALITY = False
    LAPLACIAN_MIN = 80.0    # foco mínimo aceptable
    BRIGHTNESS_MIN = 25.0
    BRIGHTNESS_MAX = 230.0

    # Segmentación
    EXG_THRESH = 0.55
    MIN_FRUIT_AREA = 20

    # Modelos (ML opcional)
    USE_YOLO = False
    YOLO_WEIGHTS = Path("app/services/models/yolo/v0.1/weights.pt")
