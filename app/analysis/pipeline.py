# app/analysis/pipeline.py
import time
from pathlib import Path

from .preprocess import preprocess_image
from .quality import assess_quality
from .indices import compute_indices, leaf_coverage
from .detectors.leaves_mask import segment_leaves
from .detectors.fruits_color import detect_fruits_by_color  # v0.2 con filtros
from .detectors.stains_detector import detect_stains
from .fruit_detection import detect_fruits                   # {ripe, unripe, malformed}
from .storage import build_record, save_record

# (opcional) para visualizar cajas de depuración
try:
    from .debug_vis import draw_boxes  # devuelve imagen con bboxes pintados
except Exception:
    draw_boxes = None


def run_pipeline(image_path: str, mission: str, cfg) -> dict:
    t0 = time.time()

    # 1) Preprocesamiento
    img_bgr = preprocess_image(image_path, cfg)

    # 2) Métricas de calidad
    q = assess_quality(img_bgr, cfg)

    # 3) Índices de vegetación y máscara de hojas
    idx = compute_indices(img_bgr)
    leaves_mask = segment_leaves(img_bgr, idx, exg_thresh=getattr(cfg, "EXG_THRESH", 0.55))
    leaf_pct = leaf_coverage(leaves_mask)

    # 4) Detectores
    fruits_color = detect_fruits_by_color(img_bgr, leaves_mask, cfg)  # bboxes + ripe/unripe estimado por color
    fruits_stats = detect_fruits(img_bgr, leaves_mask, cfg)                         # conteos robustos (ripe/unripe/malformed)
    stains = detect_stains(img_bgr, leaves_mask, cfg)

    # 5) Construcción del registro (build_record ya normaliza detections y genera fruit_summary)
    rec = build_record(
        image_path, mission,
        quality=q,
        indices={**idx, "leaf_coverage_pct": leaf_pct},
        detections={
            "fruits": fruits_color,
            "leaf_stains": stains,
            "fruit_detection": fruits_stats
        },
        leaves_mask=leaves_mask
    )

    # 6) Guardar artefactos (thumb + máscaras). No guardamos JSON en disco.
    rec = save_record(rec, cfg, leaves_mask=leaves_mask)

    # 7) (Opcional) Overlay de depuración con cajas
    if getattr(cfg, "DEBUG_SAVE_OVERLAY", False) and draw_boxes is not None:
        vis = draw_boxes(img_bgr, rec["detections"].get("fruits", {}))
        out_dir = Path(cfg.PICTURES_ROOT) / mission / cfg.ANALYSIS_DIR_NAME / cfg.FRAMES_DIR_NAME
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{Path(image_path).stem}_vis.jpg"
        import cv2
        cv2.imwrite(str(out_path), vis)
        # Puedes referenciarlo en artifacts si quieres verlo desde el dashboard:
        rec["artifacts"]["overlay"] = str(out_path)

    rec["runtime_ms"] = int((time.time() - t0) * 1000)
    return rec
