# app/analysis/detectors/stains_detector.py
import cv2
import numpy as np

def detect_stains(img_bgr, leaves_mask, cfg):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L, a, b = cv2.split(lab)
    # buscar regiones “no verdes” dentro de hojas (a* alto o bajo)
    a_norm = cv2.normalize(a, None, 0, 255, cv2.NORM_MINMAX)
    thr = cv2.adaptiveThreshold(a_norm, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY, 35, -5)
    thr = cv2.bitwise_and(thr, leaves_mask)
    k = np.ones((3,3), np.uint8)
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, k, iterations=1)

    area_pct = 100.0 * (thr>0).sum() / max(1, leaves_mask.size)
    contours,_ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return {"area_pct": float(area_pct), "clusters": int(len(contours)), "method": "lab_threshold_v0.1"}
