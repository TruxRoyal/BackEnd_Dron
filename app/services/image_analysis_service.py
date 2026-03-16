# app/services/image_analysis_service.py
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from pathlib import Path
from typing import Iterable, Optional

from app.analysis.pipeline import run_pipeline
from app.config.analysis_config import AnalysisConfig as Cfg
from app.services.mongo.mongo_service import frames, missions

# === Configuración básica de workers ===
MAX_WORKERS = 2  # si quieres, toma de env/config
_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Cola: (mission, image_path, force)
_q: Queue[tuple[str, str, bool]] = Queue()

# Extensiones que procesamos por defecto
EXTS = (".jpg", ".jpeg", ".png")

# ---------- util Mongo/idempotencia ----------
def _frame_id(mission: str, image_path: str) -> str:
    return f"{mission}__{Path(image_path).stem}"

def _exists_in_db(mission: str, image_path: str) -> bool:
    _id = _frame_id(mission, image_path)
    return frames.count_documents({"_id": _id}, limit=1) > 0

# ---------- persistencia principal ----------
def save_to_mongo(rec: dict):
    rec_id = f"{rec['mission']['name']}__{Path(rec['image']['path']).stem}"
    rec["_id"] = rec_id
    rec["filename"] = Path(rec["image"]["path"]).stem
    rec["leaf_coverage_pct"] = rec["vegetation_indices"]["leaf_coverage_pct"]
    # Aseguramos llaves aunque el detector cambie
    fruits = (rec.get("detections", {}) or {}).get("fruits", {}) or {}
    rec["fruit_count"] = int(fruits.get("count_est", 0))
    rec["ripe"] = int(fruits.get("ripe_est", 0))
    rec["unripe"] = int(fruits.get("unripe_est", 0))
    rec["quality_score"] = rec["quality"]["sharpness_laplacian"]
    rec["usable"] = rec["quality"]["is_usable"]

    frames.replace_one({"_id": rec_id}, rec, upsert=True)

# ---------- API: procesamiento individual ----------
def process_one_image(mission: str, image_path: str, force: bool = False) -> dict | None:
    """
    Procesa una imagen de forma síncrona.
    Retorna el record insertado/actualizado o None si se omitió por idempotencia.
    """
    if not force and _exists_in_db(mission, image_path):
        return None
    rec = run_pipeline(image_path, mission, Cfg)
    save_to_mongo(rec)
    return rec

# ---------- API: encolar (asincrónico con threads del proceso) ----------
def enqueue_image(mission: str, image_path: str, force: bool = False):
    _q.put((mission, image_path, force))
    _executor.submit(_worker_once)

def _worker_once():
    try:
        mission, image_path, force = _q.get_nowait()
    except Empty:
        return
    try:
        if force or not _exists_in_db(mission, image_path):
            rec = run_pipeline(image_path, mission, Cfg)
            save_to_mongo(rec)
        # si ya existe y no hay force, lo omitimos en silencio
    finally:
        _q.task_done()

# ---------- API: lote ----------
def _iter_raw_images(mission: str,
                     exts: tuple[str, ...] = EXTS,
                     patterns: Optional[Iterable[str]] = None) -> list[Path]:
    raw_dir = (Cfg.PICTURES_ROOT / mission / Cfg.RAW_DIR_NAME)
    if not raw_dir.exists():
        return []
    out: list[Path] = []
    if patterns:
        for pat in patterns:
            out.extend(sorted(raw_dir.glob(pat)))
    else:
        for e in exts:
            out.extend(sorted(raw_dir.glob(f"*{e}")))
    return out

def scan_mission(mission: str,
                 patterns: Optional[Iterable[str]] = None,
                 force: bool = False) -> dict:
    """
    Encola por lote todas las imágenes de la misión (o por patrón).
    Ya no revisa .json en disco; usa Mongo para idempotencia.
    """
    imgs = _iter_raw_images(mission, patterns=patterns)
    enqueued = skipped = 0
    for img in imgs:
        if force or not _exists_in_db(mission, str(img)):
            enqueue_image(mission, str(img), force=force)
            enqueued += 1
        else:
            skipped += 1
    return {"mission": mission, "enqueued": enqueued, "skipped": skipped, "force": force}

# ---------- API: consulta ----------
def get_frame_result(mission: str, filename_stem: str) -> dict | None:
    """
    Devuelve el documento desde Mongo (antes devolvía la ruta .json).
    """
    return frames.find_one({"_id": f"{mission}__{filename_stem}"})
