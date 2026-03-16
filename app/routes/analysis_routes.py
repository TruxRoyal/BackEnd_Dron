# app/routes/analysis_routes.py

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
from pathlib import Path

from app.services.image_analysis_service import (
    enqueue_image,
    scan_mission,
    get_frame_result,      # ahora trae el doc desde Mongo
    process_one_image,     # síncrono/individual
)
from app.services.llama.llm_service import LLMService
from app.services.mongo.mongo_service import get_frame_by_id, update_frame_explanation

bp_analysis = Blueprint("analysis", __name__, url_prefix="/api/analysis")
llm = LLMService(model="llama3")


# ---------- Encolar una sola imagen (asincrónico) ----------
@bp_analysis.post("/enqueue")
def analysis_enqueue():
    data = request.get_json(force=True)
    mission = data["mission"]
    image_path = data["image_path"]
    force = bool(data.get("force", False))

    enqueue_image(mission, image_path, force=force)
    return jsonify({"status": "accepted", "mission": mission, "image": image_path, "force": force})


# ---------- Procesar una sola imagen (síncrono) ----------
@bp_analysis.post("/process-one")
def analysis_process_one():
    data = request.get_json(force=True)
    mission = data["mission"]
    image_path = data["image_path"]
    force = bool(data.get("force", False))

    rec = process_one_image(mission, image_path, force=force)
    if rec is None:
        return jsonify({"status": "skipped", "reason": "already_exists", "mission": mission, "image": image_path}), 200
    return jsonify({"status": "ok", "record_id": f"{mission}__{Path(image_path).stem}", "mission": mission}), 200


# ---------- Escanear misión por lote (asincrónico con cola) ----------
@bp_analysis.post("/scan-mission")
def analysis_scan():
    data = request.get_json(force=True)
    mission = data["mission"]
    patterns = data.get("patterns")  # e.g. ["2025*.jpg", "*.png"]
    force = bool(data.get("force", False))

    res = scan_mission(mission, patterns=patterns, force=force)
    return jsonify({"status": "accepted", **res})


# ---------- Obtener resultado desde Mongo ----------
@bp_analysis.get("/result")
def analysis_result():
    mission = request.args.get("mission")
    stem = request.args.get("stem")  # nombre sin extensión
    if not mission or not stem:
        return jsonify({"error": "missing_params", "detail": "mission & stem are required"}), 400

    doc = get_frame_result(mission, stem)  # dict o None
    if not doc:
        return jsonify({"error": "not_found"}), 404
    return jsonify(doc), 200


# (Opcional) Descargar el thumbnail si existe (sigue leyendo del path de artefactos)
@bp_analysis.get("/result/thumb")
def analysis_result_thumb():
    mission = request.args.get("mission")
    stem = request.args.get("stem")
    if not mission or not stem:
        return jsonify({"error": "missing_params"}), 400
    doc = get_frame_result(mission, stem)
    if not doc:
        return jsonify({"error": "not_found"}), 404

    thumb = (doc.get("artifacts") or {}).get("thumb")
    if not thumb or not Path(thumb).exists():
        return jsonify({"error": "thumb_not_available"}), 404
    return send_file(thumb, mimetype="image/jpeg")


# ---------- LLM: explicación a partir de métricas crudas ----------
@bp_analysis.post("/explain")
def explain_analysis():
    data = request.get_json(silent=True) or {}
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        return jsonify({
            "success": False,
            "error": "El campo 'metrics' es obligatorio y debe ser un objeto JSON."
        }), 400

    result = llm.explain_analysis(metrics)
    return jsonify(result), 200


# ---------- LLM: explicación a partir del frame en Mongo ----------
@bp_analysis.get("/explain-frame")
def explain_from_frame():
    frame_id = request.args.get("id")
    if not frame_id:
        return jsonify({"success": False, "error": "El parámetro 'id' es obligatorio"}), 400

    frame = get_frame_by_id(frame_id)
    if not frame:
        return jsonify({"success": False, "error": f"No se encontró frame con id '{frame_id}'"}), 404

    def safe_get(d, path, default=None):
        cur = d
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def safe_human_ts(ts: str | None) -> str | None:
        if not ts:
            return None
        try:
            ts_norm = ts
            if len(ts) >= 5 and ts[-5] in ['+', '-'] and ts[-3] != ':':
                ts_norm = ts[:-2] + ':' + ts[-2:]
            return datetime.fromisoformat(ts_norm).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return None

    def deep_clean(x):
        if isinstance(x, dict):
            return {k: deep_clean(v) for k, v in x.items() if v is not None and v != {} and v != []}
        if isinstance(x, list):
            return [deep_clean(v) for v in x if v is not None]
        return x

    vi         = frame.get("vegetation_indices", {}) or {}
    quality    = frame.get("quality", {}) or {}
    image      = frame.get("image", {}) or {}
    mission    = frame.get("mission", {}) or {}
    preprocess = frame.get("preprocess", {}) or {}
    artifacts  = frame.get("artifacts", {}) or {}
    model      = frame.get("model", {}) or {}
    det_fruits = safe_get(frame, ["detections", "fruits"], {}) or {}
    leaf_stains = safe_get(frame, ["detections", "leaf_stains"], {}) or {}
    summary    = frame.get("fruit_summary", {}) or {}

    total    = summary.get("total")       or det_fruits.get("count_est")  or frame.get("fruit_count")
    ripe     = summary.get("ripe")        or det_fruits.get("ripe_est")   or frame.get("ripe")
    unripe   = summary.get("unripe")      or det_fruits.get("unripe_est") or frame.get("unripe")
    malformed = summary.get("malformed")  or safe_get(frame, ["detections", "fruit_detection", "malformed"])

    ripe_pct = (round(ripe * 100.0 / total, 2) if total and isinstance(ripe, (int, float)) else None)
    only_unripe = bool((ripe == 0) and (unripe and unripe > 0))

    stains_pct = leaf_stains.get("area_pct")
    if stains_pct is None:
        stain_severity = None
    else:
        if stains_pct >= 10:
            stain_severity = "alta"
        elif stains_pct >= 5:
            stain_severity = "media"
        else:
            stain_severity = "baja"

    metrics = {
        "vegetation_indices": {
            "leaf_coverage_pct": vi.get("leaf_coverage_pct"),
            "exg_mean": vi.get("exg_mean"),
            "vari_mean": vi.get("vari_mean"),
            "cive_mean": vi.get("cive_mean"),
        },
        "leaf_health": {
            "stains_area_pct": stains_pct,
            "stains_clusters": leaf_stains.get("clusters"),
            "stain_severity": stain_severity,
            "method": leaf_stains.get("method"),
        },
        "image_quality": {
            "sharpness_laplacian": quality.get("sharpness_laplacian"),
            "brightness_mean": quality.get("brightness_mean"),
            "snr_est": quality.get("snr_est"),
            "is_usable": quality.get("is_usable"),
            "warnings_count": len(quality.get("warnings", [])) if isinstance(quality.get("warnings"), list) else None,
        },
        "fruit_detection": {
            "total": total,
            "ripe": ripe,
            "unripe": unripe,
            "malformed": malformed,
            "ripe_pct": ripe_pct,
            "only_unripe": only_unripe,
            "source_method": det_fruits.get("method") or (model.get("fruit_detector") or {}).get("name"),
        },
        "preprocess": {
            "clahe": preprocess.get("clahe"),
            "color_balance": preprocess.get("color_balance"),
            "scale": preprocess.get("scale"),
        },
        "model_info": {
            "fruit_detector": (model.get("fruit_detector") or {}).get("name"),
            "fruit_detector_version": (model.get("fruit_detector") or {}).get("version"),
            "leaf_classifier": (model.get("leaf_classifier") or {}).get("name"),
            "leaf_classifier_version": (model.get("leaf_classifier") or {}).get("version"),
        },
        "artifacts": {
            "mask_leaves": artifacts.get("mask_leaves"),
            "mask_fruits": artifacts.get("mask_fruits"),
            "thumb": artifacts.get("thumb"),
        },
        "metadata": {
            "frame_id": frame.get("_id"),
            "filename": frame.get("filename"),
            "mission_name": mission.get("name"),
            "timestamp": image.get("timestamp"),
            "human_readable_date": safe_human_ts(image.get("timestamp")),
            "image_width": image.get("width"),
            "image_height": image.get("height"),
            "notes": frame.get("observaciones", ""),
            "schema_version": frame.get("version"),
            "runtime_ms": frame.get("runtime_ms"),
        },
    }

    metrics = deep_clean(metrics)

    llm_result = llm.explain_analysis(metrics)
    success = llm_result.get("success", False)
    explanation_text = llm_result.get("response") or llm_result.get("error")

    saved_doc = None
    if success and explanation_text:
        saved_doc = update_frame_explanation(frame_id, explanation_text)

    return jsonify({
        "success": success,
        "frame_id": frame_id,
        "metrics": metrics,
        "explanation": explanation_text,
        "saved": bool(saved_doc),
    }), 200
