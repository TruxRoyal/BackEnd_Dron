# app/tools/mongo_check.py
from app.services.mongo.mongo_service import frames

test = {"_id": "test__123", "fruit_count": 42, "leaf_coverage_pct": 87.1}
frames.replace_one({"_id": test["_id"]}, test, upsert=True)
print("Documento de prueba insertado.")
