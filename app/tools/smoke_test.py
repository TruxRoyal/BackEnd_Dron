from app.analysis.pipeline import run_pipeline
from app.config.analysis_config import AnalysisConfig as Cfg
from app.services.image_analysis_service import save_to_mongo
from pathlib import Path

mission = "Mision_Prueba"
img = Path(Cfg.PICTURES_ROOT) / mission / Cfg.RAW_DIR_NAME / "photo_2025-10-26_17-02-30.jpg"

rec = run_pipeline(str(img), mission, Cfg)
print("OK ✅")
save_to_mongo(rec) 

print("Guardado en Mongo como:", rec["image"]["path"])
print("JSON:", rec["image"]["path"], "→", rec["version"])
print("Leaf %:", rec["vegetation_indices"]["leaf_coverage_pct"], "Fruits:", rec["detections"]["fruits"]["count_est"])
