import re
import json
from pathlib import Path
from datetime import datetime


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r'[^\w\s-]', '', name, flags=re.UNICODE)
    name = re.sub(r'[\s_]+', '-', name)
    return name[:50]


def get_media_directory() -> Path:
    """Carpeta de fecha simple — para fotos manuales fuera de misión."""
    pictures_dir = Path.home() / "Pictures"
    base_dir = pictures_dir / "Misiones de Vuelo"
    date_folder = datetime.now().strftime("%Y-%m-%d")
    mission_dir = base_dir / date_folder
    mission_dir.mkdir(parents=True, exist_ok=True)
    return mission_dir


def get_mission_directory(mission_name: str) -> Path:
    """Carpeta dedicada por misión: YYYY-MM-DD_nombre-mision/"""
    pictures_dir = Path.home() / "Pictures"
    base_dir = pictures_dir / "Misiones de Vuelo"
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{_slugify(mission_name)}" if mission_name else date_str
    mission_dir = base_dir / folder_name
    mission_dir.mkdir(parents=True, exist_ok=True)
    return mission_dir


def init_manifest(mission_dir: Path, mission_name: str) -> None:
    """Crea el manifest.json al inicio de una misión."""
    manifest = {
        "missionName": mission_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "startTime": datetime.now().strftime("%H:%M:%S"),
        "endTime": None,
        "status": "running",
        "photosTaken": 0,
        "files": [],
    }
    _write_manifest(mission_dir, manifest)


def append_photo_to_manifest(
    mission_dir: Path,
    filename: str,
    waypoint: int,
    lat: float,
    lng: float,
    altitude: float,
    battery: int,
) -> None:
    manifest = _read_manifest(mission_dir)
    manifest["files"].append({
        "filename": filename,
        "type": "image",
        "waypoint": waypoint,
        "timestamp": datetime.now().isoformat(),
        "lat": lat,
        "lng": lng,
        "altitude": altitude,
        "battery": battery,
    })
    manifest["photosTaken"] = len(manifest["files"])
    _write_manifest(mission_dir, manifest)


def close_manifest(mission_dir: Path, status: str = "completed") -> None:
    manifest = _read_manifest(mission_dir)
    manifest["endTime"] = datetime.now().strftime("%H:%M:%S")
    manifest["status"] = status
    _write_manifest(mission_dir, manifest)


def _read_manifest(mission_dir: Path) -> dict:
    path = mission_dir / "manifest.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_manifest(mission_dir: Path, data: dict) -> None:
    path = mission_dir / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
