# app/analysis/detectors/fruits_color.py
import cv2
import numpy as np

def detect_fruits_by_color(img_bgr, leaves_mask, cfg):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Broader red ranges: ripe strawberries span H 0-20 and 155-180
    red1 = cv2.inRange(hsv, np.array([0,   50, 40], dtype=np.uint8), np.array([20,  255, 255], dtype=np.uint8))
    red2 = cv2.inRange(hsv, np.array([155, 50, 40], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8))
    red  = cv2.bitwise_or(red1, red2)

    green = cv2.inRange(hsv, np.array([35, 45, 40], dtype=np.uint8), np.array([85, 255, 255], dtype=np.uint8))

    # Dilate leaves_mask so nearby ripe fruits (red pixels) are included in ROI
    if leaves_mask is not None and leaves_mask.size:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
        roi = cv2.dilate(leaves_mask, k, iterations=1)
        red   = cv2.bitwise_and(red,   roi)
        green = cv2.bitwise_and(green, leaves_mask)
    # else: no mask → keep full-image detections

    fruits = _contour_to_bboxes(red,   label="ripe",
                                min_area=getattr(cfg, "MIN_FRUIT_AREA", 150))
    fruits+= _contour_to_bboxes(green, label="unripe",
                                min_area=getattr(cfg, "MIN_FRUIT_AREA_UNRIPE", 300))

    ripe = sum(1 for f in fruits if f["label"]=="ripe")
    unripe = len(fruits)-ripe
    return {
      "count_est": len(fruits), "ripe_est": ripe, "unripe_est": unripe,
      "bboxes": fruits, "method": "color_threshold_v0.1"
    }

def _contour_to_bboxes(mask, label, min_area=20):
    contours,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out=[]
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x,y,w,h = cv2.boundingRect(c)
        out.append({"x":int(x), "y":int(y), "w":int(w), "h":int(h),
                    "label":label, "ripeness": 1.0 if label=="ripe" else 0.0})
    return out
