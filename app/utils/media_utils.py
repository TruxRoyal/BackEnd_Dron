from pathlib import Path
from datetime import datetime

def get_media_directory():
    pictures_dir = Path.home() / "Pictures"
    base_dir = pictures_dir / "Misiones de Vuelo"
    date_folder = datetime.now().strftime("%Y-%m-%d")
    mission_dir = base_dir / date_folder

    if not mission_dir.exists():
        mission_dir.mkdir(parents=True, exist_ok=True)

    return mission_dir
