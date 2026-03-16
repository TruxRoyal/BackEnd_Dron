# app/tools/smoke_batch_analysis.py
from __future__ import annotations
import argparse, sys, time
from pathlib import Path

from app.config.analysis_config import AnalysisConfig as Cfg
from app.services.image_analysis_service import (
    process_one_image,   # síncrono
    scan_mission,        # asincrónico (encola)
)
from app.services.mongo.mongo_service import frames


def _gather_images(mission: str, patterns: list[str] | None) -> list[Path]:
    raw_dir = Path(Cfg.PICTURES_ROOT) / mission / Cfg.RAW_DIR_NAME
    if not raw_dir.exists():
        print(f"[ERR] No existe el directorio RAW: {raw_dir}")
        return []

    # Recolecta recursivo (rglob) y normaliza por sufijo, no por patrón textual.
    EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
    MIN_BYTES = 8 * 1024  # ignora miniaturas/archivos vacíos (<8KB)
    files: list[Path] = []

    for p in raw_dir.rglob("*"):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf in EXTS:
            try:
                if p.stat().st_size >= MIN_BYTES:
                    files.append(p)
            except Exception:
                # si falla el stat (archivo bloqueado), lo ignoramos
                continue

    files.sort()
    return files

def _count_in_mongo(mission: str) -> int:
    return frames.count_documents({"mission.name": mission})


def run_sync(mission: str, patterns: list[str] | None, force: bool) -> int:
    files = _gather_images(mission, patterns)
    if not files:
        print("[WARN] No se encontraron imágenes para procesar.")
        return 0

    ok = 0
    for i, img in enumerate(files, 1):
        rec = process_one_image(mission, str(img), force=force)
        status = "OK" if rec else "SKIP"
        print(f"[{i:04d}/{len(files)}] {img.name} -> {status}")
        if rec:
            ok += 1
    print(f"\n[SYNC] Procesadas: {ok} / {len(files)} (force={force})")
    print(f"[SYNC] Documentos en Mongo (mission={mission}): {_count_in_mongo(mission)}")
    return ok


def run_async(mission: str, patterns: list[str] | None, force: bool,
              timeout_s: int, poll_s: float) -> int:
    files = _gather_images(mission, patterns)
    total_expected = len(files)
    if total_expected == 0:
        print("[WARN] No hay imágenes para encolar.")
        return 0

    res = scan_mission(mission, patterns=patterns, force=force)
    enq = res.get("enqueued", 0)
    print(f"[ASYNC] Enqueued={enq} / total_encontradas={total_expected} (force={force})")

    # Espera pasiva hasta que Mongo tenga al menos 'enq' nuevas (o alcance total_expected)
    start = time.time()
    last = -1
    while True:
        done = _count_in_mongo(mission)
        if done != last:
            print(f"[ASYNC] Procesadas en Mongo: {done}")
            last = done
        if done >= total_expected or (time.time() - start) > timeout_s:
            break
        time.sleep(poll_s)

    print(f"\n[ASYNC] Finalizado. Mongo={_count_in_mongo(mission)} | timeout={timeout_s}s")
    return enq


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Smoke test de análisis masivo de imágenes")
    p.add_argument("--mission", required=True, help="Nombre de la misión (carpeta bajo Pictures/Misiones de Vuelo)")
    p.add_argument("--mode", choices=["sync", "async"], default="sync", help="sync: procesa en bloque | async: encola y espera")
    p.add_argument("--patterns", default="*.jpg,*.jpeg,*.png", help="Globs separados por coma")
    p.add_argument("--force", action="store_true", help="Reprocesar aunque exista en Mongo")
    p.add_argument("--timeout", type=int, default=120, help="(async) segundos máximos de espera")
    p.add_argument("--poll", type=float, default=1.0, help="(async) intervalo de sondeo en segundos")
    args = p.parse_args(argv)

    patterns = [s.strip() for s in args.patterns.split(",") if s.strip()]

    print(f"[INFO] Pictures root: {Path(Cfg.PICTURES_ROOT)}")
    print(f"[INFO] Mission: {args.mission}")
    print(f"[INFO] Mode: {args.mode} | Force: {args.force} | Patterns: {patterns}")

    if args.mode == "sync":
        run_sync(args.mission, patterns, args.force)
    else:
        run_async(args.mission, patterns, args.force, args.timeout, args.poll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
