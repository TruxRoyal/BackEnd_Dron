# app/analysis/storage.py
from pathlib import Path
import hashlib, time
import cv2

def _paths(image_path: str, mission: str, cfg):
    img_path = Path(image_path)
    mission_root = Path(cfg.PICTURES_ROOT) / mission
    analysis_dir = mission_root / cfg.ANALYSIS_DIR_NAME
    frames_dir = analysis_dir / cfg.FRAMES_DIR_NAME
    frames_dir.mkdir(parents=True, exist_ok=True)

    stem = img_path.stem
    return {
        "mission_root": mission_root,
        "analysis_dir": analysis_dir,
        "frames_dir": frames_dir,
        "mask_leaves": frames_dir / f"{stem}_mask_leaves.png",
        "mask_fruits": frames_dir / f"{stem}_mask_fruits.png",
        "thumb": frames_dir / f"{stem}_thumb.jpg",
        "stem": stem
    }

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def build_record(image_path: str, mission: str, quality: dict,
                 indices: dict | None = None,
                 detections: dict | None = None,
                 leaves_mask=None):
    p = Path(image_path)
    img = cv2.imread(str(p), cv2.IMREAD_COLOR)
    h, w = (img.shape[:2] if img is not None else (0, 0))
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(p.stat().st_mtime))

    # --- normalización de detecciones ---
    det = detections or {}
    fruit_det = det.get("fruit_detection") or {}
    fruit_color = det.get("fruits") or {}

    def _as_count(v):
        # Acepta int/float/str numérica o lista/tupla (usa len)
        if v is None:
            return 0
        if isinstance(v, (list, tuple)):
            return len(v)
        try:
            return int(round(float(v)))
        except Exception:
            return 0

    ripe_fd = _as_count(fruit_det.get("ripe", 0))
    unripe_fd = _as_count(fruit_det.get("unripe", 0))
    malformed_fd = _as_count(fruit_det.get("malformed", 0))

    # Normaliza "fruits" (color threshold)
    count_fc   = _as_count(fruit_color.get("count_est", 0))
    ripe_fc    = _as_count(fruit_color.get("ripe_est", 0))
    unripe_fc  = _as_count(fruit_color.get("unripe_est", 0))
    bboxes_fc  = fruit_color.get("bboxes", [])

    if not isinstance(bboxes_fc, (list, tuple)):
        bboxes_fc = []

    fruit_det_norm = {
        "ripe": ripe_fd,
        "unripe": unripe_fd,
        "malformed": malformed_fd
    }
    
    if count_fc == 0 and (ripe_fd + unripe_fd) > 0:
        count_fc  = ripe_fd + unripe_fd
        ripe_fc   = ripe_fd
        unripe_fc = unripe_fd

    fruit_color_norm = {
        "count_est": count_fc,
        "ripe_est": ripe_fc,
        "unripe_est": unripe_fc,
        "bboxes": bboxes_fc,
        "method": fruit_color.get("method", "color_threshold_v0.1")
    }

    det["fruit_detection"] = fruit_det_norm
    det["fruits"] = fruit_color_norm

    # --- resumen robusto (prefiere el detector estadístico si tiene señal) ---
    use_fd = (ripe_fd + unripe_fd) > 0
    ripe_src   = ripe_fd   if use_fd else ripe_fc
    unripe_src = unripe_fd if use_fd else unripe_fc

    fruit_summary = {
        "total": int(ripe_src + unripe_src),
        "ripe": int(ripe_src),
        "unripe": int(unripe_src),
        "malformed": int(malformed_fd)
    }
    # -------------------------------------

    rec = {
        "image": {
            "path": str(p),
            "hash": _sha256_file(p),
            "width": int(w),
            "height": int(h),
            "timestamp": ts
        },
        "mission": {
            "name": mission,
            "capture_order": None,
            "vgps": None
        },
        "quality": quality,
        "preprocess": {
            "denoise": None,
            "color_balance": "clahe_lab",
            "clahe": True,
            "scale": 1.0
        },
        "vegetation_indices": indices or {
            "exg_mean": 0.0,
            "vari_mean": 0.0,
            "cive_mean": 0.0,
            "leaf_coverage_pct": 0.0
        },
        "detections": det,
        "fruit_summary": fruit_summary,   # 👈 agregado para consultas
        "artifacts": {
            "mask_leaves": None,
            "mask_fruits": None,
            "thumb": None
        },
        "model": {
            "fruit_detector": {"name": "color_threshold", "version": "v0.1", "used": True},
            "leaf_classifier": {"name": None, "version": None, "used": False}
        },
        "runtime_ms": 0,
        "version": "analysis_schema_v1"
    }

    return rec

def save_record(rec: dict, cfg, leaves_mask=None, fruits_mask=None):
    pth = _paths(rec["image"]["path"], rec["mission"]["name"], cfg)

    img = cv2.imread(rec["image"]["path"], cv2.IMREAD_COLOR)
    if img is not None:
        scale = 640.0 / max(1, max(img.shape[0], img.shape[1]))
        img_thumb = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1.0 else img
        cv2.imwrite(str(pth["thumb"]), img_thumb)
        rec["artifacts"]["thumb"] = str(pth["thumb"])

    if leaves_mask is not None:
        cv2.imwrite(str(pth["mask_leaves"]), leaves_mask)
        rec["artifacts"]["mask_leaves"] = str(pth["mask_leaves"])

    if fruits_mask is not None:
        cv2.imwrite(str(pth["mask_fruits"]), fruits_mask)
        rec["artifacts"]["mask_fruits"] = str(pth["mask_fruits"])

    return rec
