# app/analysis/preprocess.py
from pathlib import Path
import cv2
import numpy as np

def _read_bgr(image_path: str):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {image_path}")
    return img

def _clahe_lab(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l2 = clahe.apply(l)
    lab2 = cv2.merge([l2, a, b])
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

def preprocess_image(image_path: str, cfg) -> np.ndarray:
    """
    Lee la imagen y aplica un preprocesamiento ligero (CLAHE).
    Devuelve BGR uint8.
    """
    img = _read_bgr(image_path)
    img = _clahe_lab(img)  # balance básico de iluminación/contraste
    return img
