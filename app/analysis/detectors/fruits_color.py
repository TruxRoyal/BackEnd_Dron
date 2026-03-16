# app/analysis/detectors/fruits_color.py
import cv2
import numpy as np

def detect_fruits_by_color(img_bgr, leaves_mask, cfg):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    red1 = cv2.inRange(hsv, (0, 80, 60), (10, 255, 255))
    red2 = cv2.inRange(hsv, (170, 80, 60), (179,255,255))
    red  = cv2.bitwise_or(red1, red2)

    green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))

    red   = cv2.bitwise_and(red,   leaves_mask)
    green = cv2.bitwise_and(green, leaves_mask)

    fruits = _contour_to_bboxes(red,   label="ripe",
                                min_area=getattr(cfg, "MIN_FRUIT_AREA", 20))
    fruits+= _contour_to_bboxes(green, label="unripe",
                                min_area=getattr(cfg, "MIN_FRUIT_AREA", 20))

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
