from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from app.config.analysis_config import AnalysisConfig as Cfg
from app.services.image_analysis_service import enqueue_image

class RawHandler(FileSystemEventHandler):
    def __init__(self, mission:str): self.mission = mission
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".jpg"):
            enqueue_image(self.mission, event.src_path)

def watch_mission(mission:str):
    raw_dir = (Cfg.PICTURES_ROOT/mission/Cfg.RAW_DIR_NAME)
    raw_dir.mkdir(parents=True, exist_ok=True)
    obs = Observer(); obs.schedule(RawHandler(mission), str(raw_dir), recursive=False)
    obs.start(); return obs
