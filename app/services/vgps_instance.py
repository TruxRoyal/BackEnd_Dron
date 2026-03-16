from app.services.virtual_gps_service import VirtualGPS
import requests

def get_initial_coordinates():
    try:
        res = requests.get("https://ipinfo.io/json")
        data = res.json()
        if "loc" in data:
            lat_str, lon_str = data["loc"].split(",")
            return float(lat_str), float(lon_str)
    except Exception as e:
        print(f"[vGPS] ⚠️ No se pudo obtener ubicación por IP: {e}")
    
    # Fallback a Bogotá
    return 4.6097, -74.0818

lat, lon = get_initial_coordinates()
vgps = VirtualGPS(lat_origin=lat, lon_origin=lon)

def get_latlon(self):
    return float(self.lat), float(self.lon)

print(f"[vGPS] 🌍 Origen virtual GPS inicializado en lat={lat}, lon={lon}")
