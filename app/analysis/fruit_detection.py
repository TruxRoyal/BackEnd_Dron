import cv2
import numpy as np
from dataclasses import dataclass

@dataclass
class Box:
    x:int; y:int; w:int; h:int; label:str; ripeness:float

def _in_range_mask(hsv, lower, upper):
    return cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))

def detect_fruits(img_bgr, leaves_mask, cfg):
    """
    Retorna dict:
      { count_est, ripe_est, unripe_est, bboxes:[{x,y,w,h,label,ripeness}], method }
    Mejora:
      - Busca solo cerca de hojas (dilatación de leaves_mask)
      - Filtra áreas mínima/máxima
      - Valida color medio dentro del contorno
      - Evita contornos gigantes por reflejos o fondo
    """
    h, w = img_bgr.shape[:2]
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # --- ROI: sólo cerca de hojas ---
    roi = None
    if leaves_mask is not None and leaves_mask.size:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41,41))
        roi = cv2.dilate((leaves_mask>0).astype(np.uint8)*255, k, iterations=1)
    else:
        roi = np.ones((h,w), np.uint8)*255

    # --- rangos HSV básicos ---
    # rojo/naranja-rojo: fresas maduras pueden tener H 0-20 o 155-180
    red1 = _in_range_mask(img_hsv, (0,  50,  40), (20, 255, 255))
    red2 = _in_range_mask(img_hsv, (155, 50, 40), (180,255, 255))
    red  = cv2.bitwise_or(red1, red2)

    # verde inmaduro
    green = _in_range_mask(img_hsv, (35, 50, 40), (85, 255, 255))

    # eliminar zonas muy oscuras (plástico negro) o muy desaturadas (gris)
    v = img_hsv[:,:,2]
    s = img_hsv[:,:,1]
    not_dark = (v > 40).astype(np.uint8)*255
    not_gray = (s > 40).astype(np.uint8)*255

    red   = cv2.bitwise_and(red,   roi); red   = cv2.bitwise_and(red,   not_dark); red   = cv2.bitwise_and(red,   not_gray)
    green = cv2.bitwise_and(green, roi); green = cv2.bitwise_and(green, not_dark); green = cv2.bitwise_and(green, not_gray)

    # limpieza morfológica
    ksmall = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    red = cv2.morphologyEx(red, cv2.MORPH_OPEN, ksmall, iterations=1)
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, ksmall, iterations=1)

    # contornos
    cnts_r,_ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts_g,_ = cv2.findContours(green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_min = max(80, int(0.0002 * w * h))   # evita ruido
    area_max = int(0.06 * w * h)              # evita “pantallazos” gigantes

    bboxes = []
    ripe_est = 0
    unripe_est = 0

    def accept_contour(c, label):
        nonlocal ripe_est, unripe_est, bboxes
        a = cv2.contourArea(c)
        if a < area_min or a > area_max:
            return
        x,y,ww,hh = cv2.boundingRect(c)
        # proporción razonable (evita franjas raras)
        ratio = max(ww/hh, hh/ww)
        if ratio > 3.0:  # demasiado alargado -> suele ser borde/reflejo
            return

        # validación de color medio dentro del bbox
        sub = img_hsv[y:y+hh, x:x+ww]
        mask_c = np.zeros((hh, ww), np.uint8)
        cv2.drawContours(mask_c, [c - [x,y]], -1, 255, -1)
        h_mean = int(cv2.mean(sub[:,:,0], mask=mask_c)[0])
        s_mean = float(cv2.mean(sub[:,:,1], mask=mask_c)[0])
        v_mean = float(cv2.mean(sub[:,:,2], mask=mask_c)[0])

        # Heurística de madurez (ajustable):
        # rojo si H ~ [0..10] U [160..180] y S,V razonables
        if label == "ripe":
            is_red_like = (s_mean > 45 and v_mean > 45 and (h_mean <= 20 or h_mean >= 155))
            if not is_red_like:
                return
            ripe_est += 1
            ripeness = 1.0
        else:
            # verde si H ~ [35..85]
            is_green_like = (s_mean > 45 and v_mean > 45 and 35 <= h_mean <= 85)
            if not is_green_like:
                return
            # Hojas tienen baja circularidad; frutas son más redondas
            perimeter = cv2.arcLength(c, True)
            circularity = (4 * np.pi * a / (perimeter * perimeter)) if perimeter > 0 else 0
            if circularity < 0.30:  # muy irregular → probablemente hoja, no fruta
                return
            unripe_est += 1
            ripeness = 0.0

        bboxes.append(Box(x,y,ww,hh,label,ripeness).__dict__)

    for c in cnts_r: accept_contour(c, "ripe")
    for c in cnts_g: accept_contour(c, "unripe")

    def is_malformed(contour):
        area = cv2.contourArea(contour)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull) + 1e-6
        solidity = area / hull_area           # < 0.8 sugiere huecos/hendiduras
        x,y,w,h = cv2.boundingRect(contour)
        ratio = max(w/h, h/w)                 # muy alargado → atípico
        return (solidity < 0.80) or (ratio > 2.2)


    return {
        "count_est": ripe_est + unripe_est,
        "ripe_est": ripe_est,
        "unripe_est": unripe_est,
        "bboxes": bboxes,
        "malformed": [c for c in cnts_r if is_malformed(c)] + [c for c in cnts_g if is_malformed(c)],
        "method": "color_threshold_v0.2"
    }
