import json
from pathlib import Path

CONFIG_PATH = Path("app/config/camera_config.json")

def load_camera_config(profile_id="default_video_config"):
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as file:
                all_configs = json.load(file)
                if isinstance(all_configs, list):
                    for cfg in all_configs:
                        if cfg.get("_id") == profile_id:
                            return cfg
                elif isinstance(all_configs, dict):
                    return all_configs  # soporte para formato plano
                print(f"⚠️ No se encontró el perfil '{profile_id}' en configuración")
        except Exception as e:
            print(f"⚠️ Error al leer configuración: {e}")
    else:
        print("⚠️ No se encontró el archivo de configuración.")
    return None

def save_camera_config(new_config: dict):
    try:
        with open(CONFIG_PATH, "w") as file:
            json.dump(new_config, file, indent=2)
        print("✅ Configuración de cámara actualizada")
    except Exception as e:
        print(f"❌ Error al guardar configuración: {e}")
