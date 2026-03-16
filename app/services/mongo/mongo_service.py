import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pymongo import MongoClient, ReturnDocument

client = MongoClient('mongodb://localhost:27017/')
db = client['drone_analysis']

frames = db['frames']
missions = db['missions']

def get_frame_by_id(frame_id: str):
    return frames.find_one({"_id": frame_id})

def update_frame_explanation(frame_id: str, text: str) -> Optional[dict]:
    """
    Guarda solo la explicación como texto.
    - last_explanation_text: último texto (rápido de leer).
    - explanations_text: historial (solo strings, máx. 10).
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = f"[{now}] {text}"

    return frames.find_one_and_update(
        {"_id": frame_id},
        {
            "$set": {"last_explanation_text": text},
            "$push": {
                "explanations_text": {
                    "$each": [entry],
                    "$position": 0,
                    "$slice": 10
                }
            }
        },
        return_document=ReturnDocument.AFTER,
    )